import collections
from typing import Dict

from common import get_html, HN_NEWS_URL
from items import Item, extract_item_main_text, extract_item_subtext

import bs4

class Page(object):
    """Represents a page on Hacker News."""
    items = Dict[int, Item]

    def __init__(self, items: Dict[int, Item] = None):
        self.pg_number = pg_number
        self.items = items
    
    def __str__(self):
        return str(items)

class NewsPage(Page):
    """Represents one of the news pages on Hacker News."""
    pg_number = None

    def __init__(self, pg_number: int, items: Dict[int, Item] = None):
        super().__init__(items=items)
        self.pg_number = pg_number

class CommentPage(Page):
    """Represents a page containing a comment and any subcomments."""
    pass

class PostPage(Page):
    """Represents a page containing the frontmatter of a post on HN, as well as any associated comments."""
    pass

def get_page():
    pass

def get_posts_on_page(page_num: int):
    posts = process_page(get_page_html(page_num))
    return posts

def process_page(text: str) -> Dict:
    """Processes text representing HTML for a news page of HN, returning Posts."""
    soup = bs4.BeautifulSoup(text, 'html.parser')
    posts = collections.OrderedDict()

    # Strategy: Extract out the entries, which are in a table
    # with class name 'itemlist'
    items_table = soup.find('table', attrs={'class' : 'itemlist'})
    if items_table is not None:
        for child in items_table.children:
            if child == '\n':
                continue
            # <tr> tags with classes 'spacer', 'athing', or 'morespace'
            if child.has_attr('class'):
                # post title with story URL, rank, and site string
                if child['class'][0] == 'athing':
                    item_id = int(child['id'])
                    content = extract_item_main_text(child)
                    content['rank'] = extract_rank(child)
                    posts[item_id] = Item(item_id, content=content)
                else:
                    continue
            else:
                for descendant in child.children:
                    if descendant.has_attr('class') and descendant['class'][0] == 'subtext':
                        item_id, subtext_info = extract_item_subtext(child)
                        # find the appropriate Post and update its content
                        i = posts[item_id]
                        i.content.update(subtext_info)
    else:
        posts = None

    return posts

def extract_rank(t: bs4.Tag):
    """Extract rank from tag representing title of a post on a page of HN."""
    # get rank, if it exists
    rank_span = t.find('span', attrs={'class': 'rank'})
    rank = int(rank_span.string.split('.')[0]) if rank_span.string else ''
    return rank

def get_page_html(page_num: int) -> str:
    """Returns the HTML content for a given news page of HN."""
    page_url = HN_NEWS + '?p={}'.format(page_num)
    return get_html(page_url)
