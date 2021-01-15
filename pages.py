from typing import List

from page import Page, extract_page, DEFAULT_PAGE_NUM
from common import get_html, HN_ITEMS_URL, HN_NEWS_URL

class Pages(object):
    """Represents a collection of Pages on HN."""
    pages: List[Page] = None
    num_pages: int = None
    current_page: int = None

    def __init__(self, pages: List[Page], num_pages: int, current_page: int = DEFAULT_PAGE_NUM):
        self.pages = pages
        self.num_pages = num_pages
        self.current_page = current_page

    def __str__(self):
        s = '{\n'
        for p in self.pages:
            s += '\t{}. {}\n'.format(p.pg_number, p)
        s += '}'
        return s

def get_post_pages_by_id(item_id: int) -> List[Page]:
    pages = []
    url = HN_ITEMS_URL + '?id={}'.format(item_id)
    pg = extract_page(get_html(url))
    pages.append(pg)
    while(pg.has_next):
        newurl = url + '&p={}'.format(pg.pg_number + 1)
        pg = extract_page(get_html(newurl))
        pages.append(pg)

    return pages

def get_news_pages_by_num(page_nums: List[int]) -> List[Page]:
    """Return the HTML content of a given news page."""
    pages = []
    for page_num in page_nums:
        url = HN_NEWS_URL + '?p={}'.format(page_num)
        pg = extract_page(get_html(url))
        pages.append(pg)

    return pages