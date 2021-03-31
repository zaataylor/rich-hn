from typing import List, Tuple
import math

from page import Page, NewsPage, PostPage, CommentPage, extract_page, extract_ranks, DEFAULT_PAGE_NUM
from common import get_html, HN_ITEMS_URL, HN_NEWS_URL

ITEMS_PER_NEWS_PAGE = 30

class Pages(object):
    """Represents a collection of Pages on HN."""
    pages: List[Page] = None
    current_page: int = None
    page_type: Page = None

    def __init__(self, pages: List[Page], current_page: int = DEFAULT_PAGE_NUM):
        self.pages = pages
        self.current_page = current_page
        self.page_type = type(self.pages[0])

    def __str__(self):
        s = ''
        for p in self.pages:
            s += '(page {}):\n{}\n'.format(p.pg_number, p)
        return s

    def get_current_page(self):
        """Get the current Page."""
        return self.pages[self.current_page - 1]

    def get_current_page_num(self):
        """Get the current page number."""
        return self.current_page

    def next_page(self):
        """Get the next Page, or None if there isn't one."""
        cur_pg = self.get_current_page()
        if cur_pg.has_next:
            self.current_page += 1
            return self.get_current_page()
        else:
            return None
        
    def prev_page(self):
        """Get the previous Page, or None if there isn't one."""
        if self.current_page - 1 >= 1:
            self.current_page -= 1
            return self.get_current_page()
        else:
            return None

def get_post_pages_by_id(item_id: int) -> Pages:
    """Get Post Pages based on an Item ID."""
    pages = []
    url = HN_ITEMS_URL + '?id={}'.format(item_id)
    pg = extract_page(get_html(url))
    pages.append(pg)
    while(pg.has_next):
        newurl = url + '&p={}'.format(pg.pg_number + 1)
        pg = extract_page(get_html(newurl))
        pages.append(pg)

    return Pages(pages)

def get_post_by_rank(rank: int) -> Tuple[int, str]:
    """Get information (title, ID) about a post by rank."""
    # calculate page to visit based on the rank 
    #   (there are 30 results/page)
    page_num = rank / ITEMS_PER_NEWS_PAGE
    page_num = int(math.ceil(page_num))

    url = HN_NEWS_URL + '?p={}'.format(page_num)
    ranks = extract_ranks(get_html(url))
    return ranks[rank]

def get_news_pages_by_num(page_nums: List[int]) -> Pages:
    """Get News Pages indicated by a list of numbers."""
    pages = []
    for page_num in page_nums:
        url = HN_NEWS_URL + '?p={}'.format(page_num)
        pg = extract_page(get_html(url))
        pages.append(pg)

    return Pages(pages)
