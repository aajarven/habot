"""
Test `habot.io.wiki` module.
"""

import pytest

from habot.io.wiki import WikiReader


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
            [h.text for h in reader.page.xpath("//h1")])
    assert (reader.page.xpath("//span")[-1].text ==
            "Take your favorite fandoms with you and never miss a beat.")


@pytest.mark.usefixtures("patch_wiki_page")
def test_find_elements_with_matching_subelement():
    """
    Test that a list of elements with the correct content is returned.

    The method is currently only tested using a query that returns a single
    element, but it is ensured that the element is of the right type and has
    the expected content.
    """
    reader = WikiReader("https://habitica.fandom.com/wiki/test_article")
    quest_list = reader.find_elements_with_matching_subelement("ul",
                                                               "(CURRENT)")
    assert len(quest_list) == 1
    assert quest_list[0].tag == "ul"

    li_elements = quest_list[0].getchildren()
    assert len(li_elements) == 8
    assert li_elements[0].text == "(CURRENT) Robot (collection)"

    for element in li_elements:
        assert element.tag == "li"
