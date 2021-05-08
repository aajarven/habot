"""
Read Habitica wiki pages.
"""

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


class WikiParsingError(Exception):
    """
    Exception for unexpected content from Habitica Wiki.
    """
