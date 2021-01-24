from typing import List

from page import Page, NewsPage, CommentPage, PostPage, extract_page, DEFAULT_PAGE_NUM
from common import get_html, HN_ITEMS_URL, HN_NEWS_URL
from itemdb import ItemDB

items_db = ItemDB(items={})

class Pages(object):
    """Represents a collection of Pages on HN."""
    pages: List[Page] = None
    current_page: int = None

    def __init__(self, pages: List[Page], current_page: int = DEFAULT_PAGE_NUM):
        self.pages = pages
        self.current_page = current_page

    def __str__(self):
        s = ''
        for p in self.pages:
            s += 'Page Number {}:\n\n{}\n'.format(p.pg_number, p)
        return s

    def update_db(self):
        """Update the ItemDB with one or more Items."""
        if self.pages is not None:
            first_pg = self.pages[0]
            if isinstance(first_pg, NewsPage):
                for p in self.pages:
                    for item in p.items.values():
                        items_db.add_item(item)
            else:
                for p in self.pages:
                    items_db.add_item(p.item)

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

def get_news_pages_by_num(page_nums: List[int]) -> Pages:
    """Get News Pages indicated by a list of numbers."""
    pages = []
    for page_num in page_nums:
        url = HN_NEWS_URL + '?p={}'.format(page_num)
        pg = extract_page(get_html(url))
        pages.append(pg)

    return Pages(pages)