"""
Read Habitica wiki pages.
"""

from codecs import decode, encode
import copy
from io import StringIO

from lxml import etree
import requests.exceptions


class WikiReader():
    """
    Tool for fetching content of a page from Habitica wiki.
    """

    def __init__(self, url):
        """
        Initialize the object

        :url: String containing url to the page, e.g.
              "https://habitica.fandom.com/wiki/The_Keep:Mental_Health_Warriors_Unite".
        """
        self.url = url
        self._parser = etree.HTMLParser()
        self._page = None

    class Decorators():
        """
        Decorators used by WikiReader
        """
        # pylint: disable=too-few-public-methods

        @classmethod
        def needs_page(cls, method):
            """
            Decorator for functions that need the page to be fetched
            """
            def _decorated(*args, **kwargs):
                # pylint: disable=protected-access
                if not args[0]._page:
                    args[0]._read_page()
                return method(*args, **kwargs)
            return _decorated

    def _read_page(self):
        """
        Fetch the page from the wiki.

        :raise:
            :HTTPError: if the page cannot be fetched
            :WikiParsingError: if the page content cannot be found
        """
        response = requests.get(self.url)
        response.raise_for_status()
        full_page_tree = etree.parse(StringIO(str(response.content)),
                                     self._parser)
        content = full_page_tree.getroot().cssselect(".WikiaPage")
        if len(content) != 1:
            raise WikiParsingError("More than one `WikiaPage` element "
                                   "encountered")
        self._page = content[0]

    @property
    @Decorators.needs_page
    def page(self):
        """
        Return the HTML contents of the page as lxml ElementTree.
        :returns: lxml Element corresponding to the root node of the wiki page
                  content.
        """
        return self._page

    @Decorators.needs_page
    def find_elements_with_matching_subelement(self, element_selector,
                                               child_text):
        """
        Return a list of elements of given type that have a matching children.

        The given `child_text` must only be present in one of the children
        elements: it is not necessary for it to be the full content of the
        element.

        :element_selector: CSS selector for finding the elements. E.g. `div` or
                           `#someid` or `ul.navigation`.
        :child_text: A string that must be found in the content of at least one
                     of the child elements.
        :returns: A list of lxml ElementTrees, each startig from an element
                  that matched the search criteria.
        """
        css_matching_elements = self._page.cssselect(element_selector)
        full_match_elements = []
        for element in css_matching_elements:
            for child in element.iterchildren():
                if child.text and child_text in child.text:
                    full_match_elements.append(element)
        return full_match_elements


class HtmlToMd():
    """
    Produce Habitica markdown from a HTML lxml etree.

    The support is at this point very limited: only the following HTML tags can
    be converted:
    - <i> (italic)
    - <b> (bold)
    - <s> (strikethrough)
    - <code> (inline code)
    - <ol> and the <li> within (ordered list)
    - <ul> and the <li> within (unordered list)
    """
    # pylint: disable=too-few-public-methods

    def __init__(self):
        """
        """
        self._conversion_functions = {
            "i": self._convert_i,
            "b": self._convert_b,
            "s": self._convert_s,
            "code": self._convert_code,
            "li": self._convert_li,
            "ol": self._convert_ol,
            "ul": self._convert_ul,
            }

    def convert(self, html_node):
        """
        Return a string corresponding in which content has been converted to md

        The returned tree has nodes corresponding to the ones in the original
        tree, but their text contents have been converted to markdown.
        """
        new_tree = copy.deepcopy(html_node)
        for node in self._traverse_depth_first(new_tree):
            if node.tag in self._conversion_functions:
                node.text = self._conversion_functions[node.tag](node)
        return new_tree.text

    def _traverse_depth_first(self, node):
        """
        Return nodes in dept-first order, yielding each node.

        The nodes are yielded in post-order (all children before parent).
        """
        for child in node.getchildren():
            yield from self._traverse_depth_first(child)
        yield node

    # Methods here are for internal use only despite not using `self`, so this
    # is the most sensible place for them at the moment.
    # pylint: disable=no-self-use

    def _text(self, node):
        """
        Return the text of the node without escapes.
        """
        return decode(encode(node.text, "latin-1"), "unicode-escape")

    def _tail(self, node):
        """
        Return the "tail" text of the node without escapes.
        """
        return decode(encode(node.tail, "latin-1"), "unicode-escape")

    def _children_texts(self, node):
        """
        Return the text content from all children nodes concatenated together.
        """
        return "".join([self._text(c) for c in node.getchildren() if c.text])

    def _convert_i(self, node):
        """
        Return a markdown string corresponding to `i` html node contents.

        The node must not have any children.
        """
        return "*{}*{}".format(self._text(node.text), self._tail(node))

    def _convert_b(self, node):
        """
        Return a markdown string corresponding to `b` html node contents.

        The node must not have any children.
        """
        return "**{}**{}".format(self._text(node), self._tail(node))

    def _convert_s(self, node):
        """
        Return a markdown string corresponding to `s` html node contents.

        The node must not have any children.
        """
        return "~~{}~~{}".format(self._text(node), self._tail(node))

    def _convert_code(self, node):
        """
        Return a markdown string corresponding to `i` html node contents.

        The node must not have any children.
        """
        return "`{}`{}".format(self._text(node), self._tail(node))

    def _convert_li(self, node):
        """
        Return markdown string corresponding to a `li` in HTML.

        Depending on the parent node (`ol`/`ul`), the children nodes are
        prepended either with "- " or "1. ".
        """
        children_texts = self._children_texts(node)
        if node.getparent().tag == "ol":
            list_indicator = "1. "
        elif node.getparent().tag == "ul":
            list_indicator = "- "
        else:
            raise HtmlParsingError("Unsupported parent tag {} encountered "
                                   "for a list item {}"
                                   "".format(node.getparent().tag,
                                             node.text))
        return "{}{}{}".format(list_indicator, node.text, children_texts)

    def _join_children_with_newline(self, node):
        """
        Return the text contents for all children joined with newlines.
        """
        return "\n".join([self._text(c) for c in node.getchildren()])

    def _convert_ul(self, node):
        """
        Return markdown corresponding to an `ul` in HTML.

        The returned string also contains contents for all child nodes.
        """
        return self._join_children_with_newline(node) + "\n\n"

    def _convert_ol(self, node):
        """
        Return markdown corresponding to an `ol` in HTML.

        The returned string also contains contents for all child nodes.
        """
        return self._join_children_with_newline(node) + "\n\n"


class WikiParsingError(Exception):
    """
    Exception for unexpected content from Habitica Wiki.
    """


class HtmlParsingError(ValueError):
    """
    Exception for HTML content that cannot be parsed.
    """
