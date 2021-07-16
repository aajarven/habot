"""
Test `habot.io.wiki` module.
"""

from lxml import etree
import pytest

from habot.io.wiki import WikiReader, HtmlToMd


@pytest.fixture
def patch_wiki_page(requests_mock):
    """
    Make get request to wiki return a constant article from a file.

    The page has a all the versatile content Mental Health Warriors party page
    has.
    """
    with open("tests/data/party-wikipage.html") as htmlfile:
        page = htmlfile.read()
    requests_mock.get("https://habitica.fandom.com/wiki/test_article",
                      text=page)


# pylint doesn't understand fixtures
# pylint: disable=redefined-outer-name


@pytest.mark.usefixtures("patch_wiki_page")
def test_get_wiki_page():
    """
    Test using WikiReader to get a page.

    Ensure that it has real content elements from start and end of the page.
    """
    reader = WikiReader("https://habitica.fandom.com/wiki/test_article")
    assert reader.page
    assert ("The Keep:Mental Health Warriors Unite" in
            reader.page.xpath("//h1")[0].text)
    assert (reader.page.xpath("//span")[-1].text ==
            "Join Fan Lab")


@pytest.mark.usefixtures("patch_wiki_page")
def test_find_elements_with_matching_subelement():
    """
    Test that a list of elements with the correct content is returned.

    The method is currently only tested using a query that returns a single
    element, but it is ensured that the element is of the right type and has
    the expected content.
    """
    reader = WikiReader("https://habitica.fandom.com/wiki/test_article")
    quest_list = reader.find_elements_with_matching_subelement("ol",
                                                               "(CURRENT)")
    assert len(quest_list) == 1
    assert quest_list[0].tag == "ol"

    li_elements = quest_list[0].getchildren()
    assert len(li_elements) == 9
    assert li_elements[0].text == "(CURRENT) Spider (Boss 400)"

    for element in li_elements:
        assert element.tag == "li"


@pytest.fixture
def complex_test_tree():
    """
    Return a lxml etree containing three levels of elements.

    The HTML to which the tree correspondings is the following:
    ```
    <ol>
      <li>There is something in italic <i>here</i>, how cool</li>
      <li>There is something bold <b>here</b>, how cool</li>
      <li>There is something <s>strikethroughed</s> here, how cool</li>
      <li>There is some <code>code</code> here, how cool</li>
    </ol>
    ```
    """
    html_str = (
            "<ol>"
            "<li>There is something in italic <i>here</i>, how cool</li>"
            "<li>There is something bold <b>here</b>, how cool</li>"
            "<li>There is something <s>strikethroughed</s> here, how cool</li>"
            "<li>There is some <code>code</code> here, how cool</li>"
            "</ol>"
            )
    root = etree.fromstring(html_str)
    return root


def test_depth_first_traversal_order(complex_test_tree):
    """
    Ensure that the tree is traversed in post-order.

    The nodes should be yielded so that a formatting nodes (`i`, `b`, `code`
    etc) and `li` nodes alternate, and each formatting node is returned just
    before its parent list item node.
    """
    # We are testing a private method here
    # pylint: disable=protected-access

    html2md = HtmlToMd()
    nodes_in_order = list(html2md._traverse_depth_first(complex_test_tree))

    for i in range(0, len(nodes_in_order)-1, 2):
        assert nodes_in_order[i].getparent() == nodes_in_order[i+1]


def test_convert(complex_test_tree):
    """
    Test that the following elements are converted to markdown correctly:
    - <i> (italic)
    - <b> (bold)
    - <s> (strikethrough)
    - <code> (inline code)
    - <ol> and the <li> within
    """
    html2md = HtmlToMd()
    converted = html2md.convert(complex_test_tree)

    expected_result = ("1. There is something in italic *here*, how cool\n"
                       "1. There is something bold **here**, how cool\n"
                       "1. There is something ~~strikethroughed~~ here, "
                       "how cool\n"
                       "1. There is some `code` here, how cool\n\n")
    assert converted == expected_result
