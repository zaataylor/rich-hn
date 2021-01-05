import collections
from typing import Dict

from common import get_html, HN_NEWS_URL
from items import Item, extract_item_main_text, extract_item_subtext

import bs4

DEFAULT_PAGE_NUM = 1

class Page(object):
    """Represents a page on Hacker News."""
    pg_number = None
    items = Dict[int, Item]

    def __init__(self, pg_number, items: Dict[int, Item] = None):
        self.pg_number = pg_number
        self.items = items
    
    def __str__(self):
        return str(items)

class NewsPage(Page):
    """Represents one of the news pages on Hacker News."""
    # maps item IDs to rank
    ranks = None
    def __init__(self, pg_number, ranks: Dict[int, int] = None,
        items: Dict[int, Item] = None):
        super().__init__(pg_number, items)
        self.ranks = ranks

class CommentPage(Page):
    """Represents a page containing a comment and any subcomments."""
    pass

class PostPage(Page):
    """Represents a page containing the frontmatter of a post on HN, as well as any associated comments."""
    pass

# def get_page(page_num: int):
#     page = process_page(get_page_html(page_num))
#     return page

def process_page(html: str) -> Page:
    """Processes HTML of a page on HN, returning a Page."""
    page = None

    soup = bs4.BeautifulSoup(html, 'html.parser')
    pg_num = get_page_number(soup)

    # search for <table> with class='itemlist', characteristic of a News Page
    itemlist_table = soup.find('table', attrs={'class': 'itemlist'})
    is_news_page = True if itemlist_table is not None else False
    if is_news_page:
        # get posts with ranks
        ranks, items = get_news_items()
        # construct News object
        page = NewsPage(pg_num, ranks, items)

    # Search for <span> elements with class='storyon', and check whether all
    # of them are empty. This distinguishes Comment Pages from Post Pages.
    # Optimization: only check the first item with class='storyon', as
    # this corresponds to the front matter of a post
    storyon_span = soup.find('span', 'attrs'={'class': 'storyon'})
    # If the first tag in the tree with class='storyon' is empty, that indicates we're
    # on a Post Page. Otherwise, we're on a Comment Page.
    is_comment_page = bool(storyon_span.contents)
    if is_comment_page:
        # construct Comment Page object
        print('comment page!')
    else:
        # construct Post Page object
        print('post page!')
    
    return page

def get_page_number(s: bs4.BeautifulSoup):
    """Returns the page number for a given page on HN."""
    more_a = soup.find('a', attrs={'class': 'morelink'})
    if more_a is None:
        return DEFAULT_PAGE_NUM
    else:
        # If there's a "More" link at the bottom of the page, the
        # current page number is 1 less than the page number listed
        # in the "More" link
        next_page = int(more_a['href'].split('?p=')[1]) 
        return next_page - 1

def get_news_items(t: bs4.Tag) -> Dict:
    """Process HTML for a news page of HN, returning a dict of Items and dict of ranks."""
    items = collections.OrderedDict()
    ranks = dict()

    for child in t.children:
        if child == '\n':
            continue
        # <tr> tags with class 'athing' are posts
        if child.has_attr('class'):
            # post title with story URL, rank, and site string
            if child['class'][0] == 'athing':
                item_id = int(child['id'])
                content = extract_item_main_text(child, context=NewsPage)
                ranks[item_id] = extract_rank(child)
                items[item_id] = Item(item_id, content=content)
            else:
                continue
        else:
            for descendant in child.children:
                if descendant.has_attr('class') and descendant['class'][0] == 'subtext':
                    item_id, subtext_info = extract_item_subtext(child)
                    # find the appropriate Post and update its content
                    i = items[item_id]
                    i.content.update(subtext_info)

    return ranks, items

def extract_rank(t: bs4.Tag):
    """Extract rank from tag representing title of a post on a page of HN."""
    # get rank, if it exists
    rank_span = t.find('span', attrs={'class': 'rank'})
    rank = int(rank_span.string.split('.')[0]) if rank_span.string else ''
    return rank

def get_page_html(page_num: int) -> str:
    """Returns the HTML content for a given news page of HN."""
    page_url = HN_NEWS_URL + '?p={}'.format(page_num)
    return get_html(page_url)
