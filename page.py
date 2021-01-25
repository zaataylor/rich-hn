from collections import OrderedDict
from typing import Dict, Tuple
import textwrap

from common import get_html, HN_NEWS_URL
from items import Item, extract_post_item_main, extract_post_item_subtext, extract_comment_info, \
    extract_comment_tree, extract_comment_tree_ds
from tree import Tree

import bs4

DEFAULT_PAGE_NUM = 1

class Page(object):
    """Represents a page on Hacker News."""
    pg_number = None
    has_next = None

    def __init__(self, pg_number, has_next):
        self.pg_number = pg_number
        self.has_next = has_next

class NewsPage(Page):
    """Represents one of the news pages on Hacker News."""
    # ranks dict maps item IDs to rank
    ranks: Dict[int, int] = None
    items: Dict[int, Item] = None
    def __init__(self, pg_number, has_next, ranks: Dict[int, int] = None,
        items: Dict[int, Item] = None):
        super().__init__(pg_number, has_next)
        self.ranks = ranks
        self.items = items
    
    def __str__(self):
        s = ''
        for item_id, rank in self.ranks.items():
            s += '{:>3}. {}\n'.format(rank, self.items[item_id].get_title())
        return s

class CommentPage(Page):
    """Represents a page containing a comment and any subcomments."""
    item: Item = None
    comments: Tree = None
    # comment pages have a dict member called items, but this dict
    # will only ever have one key that corresponds to the main item
    # on the comment page itself
    def __init__(self, pg_number, has_next, item: Item = None,
        comments: Tree = None):
        super().__init__(pg_number, has_next)
        self.item = item
        self.comments = comments

    def __str__(self):
        s = ''
        s += '{}:\n'.format(self.item.get_user())
        main_comment = prettify_string(self.item.get_text(), '')
        main_comment = main_comment.replace('<p>', '\n\n')
        s += main_comment + '\n\n'
        for lineage in self.comments.values():
            comment = lineage[-1][1]
            ind = '\t' * len(lineage)
            s += '{}:'.format(prettify_string(comment.get_user(), ind))
            s += '\n'
            pretty_comment = prettify_string(comment.get_text(), ind)
            pretty_comment = pretty_comment.replace('<p>', '\n\n' + ind)
            s += pretty_comment
            s += '\n\n'
        return s

class PostPage(Page):
    """Represents a page containing the frontmatter of a post on HN, as well as any associated comments."""
    item: Item = None
    comments: Tree = None
    # post pages have a dict member called items, but this dict
    # will only ever have one key that corresponds to the main item
    # on the post page itself
    def __init__(self, pg_number, has_next, item: Item = None,
        comments: dict = None):
        super().__init__(pg_number, has_next)
        self.item = item
        self.comments = comments

    def __str__(self):
        s = ''
        s += '{}\n'.format(self.item.get_title())
        for lineage in self.comments.values():
            comment = lineage[-1][1]
            ind = '\t' * len(lineage)
            s += '{}:'.format(prettify_string(comment.get_user(), ind))
            s += '\n'
            pretty_comment = prettify_string(comment.get_text(), ind)
            pretty_comment = pretty_comment.replace('<p>', '\n\n' + ind)
            s += pretty_comment
            s += '\n\n'
        return s

def prettify_string(text: str, ind: str) -> str:
    """Prettifies a string into a string justified by ind."""
    t = textwrap.fill(text, width=100, break_long_words=True, break_on_hyphens=False)
    return textwrap.indent(t, prefix=ind)

# The main extraction function: this function takes the
# HTML representing any given page on HN and uses indicators
# in the HTML to determine how to process the page.
def extract_page(html: str) -> Page:
    """Process HTML of a page on HN and return a Page."""
    soup = bs4.BeautifulSoup(html, 'html.parser')
    pg_num = extract_page_number(soup)
    has_next = has_next_page(soup)

    # search for <table> with class='itemlist', characteristic of a News Page
    itemlist_table = soup.find('table', attrs={'class': 'itemlist'})
    is_news_page = True if itemlist_table is not None else False
    if is_news_page:
        # get posts with ranks
        ranks, items = extract_news_page(itemlist_table)
        # construct News object
        return NewsPage(pg_num, has_next, ranks, items)

    # Search for <span> elements with class='storyon', and check whether all
    # of them are empty. This distinguishes Comment Pages from Post Pages.
    # Optimization: only check the first item with class='storyon', as
    # this corresponds to the front matter of a post
    storyon_span = soup.find('span', attrs={'class': 'storyon'})
    # If the first tag in the tree with class='storyon' is empty, that indicates we're
    # on a Post Page. Otherwise, we're on a Comment Page.
    is_comment_page = bool(storyon_span.contents)
    if is_comment_page:
        # construct Comment Page object
        comment_tr = soup.find('tr', attrs={'class' : 'athing'})
        comment_tree_table = soup.find('table', attrs={'class' : 'comment-tree'})
        item, comment_tree = extract_comment_page(comment_tr, comment_tree_table)
        return CommentPage(pg_num, has_next, item=item, comments=comment_tree)
    else:
        # construct Post Page object
        post_tr = soup.find('tr', attrs={'class' : 'athing'})
        post_td = soup.find('td', attrs={'class' : 'subtext'})
        comment_tree_table = soup.find('table', attrs={'class' : 'comment-tree'})
        item, comment_tree = extract_post_page(post_tr, post_td, comment_tree_table)
        return PostPage(pg_num, has_next, item=item, comments=comment_tree)

# Extraction functions: these functions extract Items and information
# related to them, such as page number, ranking, etc. from the HTML
# corresponding to a given page on HN. To extract individual items,
# a lot of these function call other, Item abstraction level functions
# located in items.py
def extract_page_number(s: bs4.BeautifulSoup):
    """Return the page number for a given page."""
    pagetop_span = s.find('span', attrs={'class': 'pagetop'})
    pagenum_font = pagetop_span.find('font')
    if pagenum_font is not None:
        page_num = int(pagenum_font.string.split('page')[1])
        return page_num
    else:
        more_a = s.find('a', attrs={'class': 'morelink'})
        if more_a is not None:
            return int(more_a['href'].split('p=')[1]) - 1
        else:
            return DEFAULT_PAGE_NUM

def has_next_page(s: bs4.BeautifulSoup):
    """Return boolean indicating if there is a next page or not."""
    more_a = s.find('a', attrs={'class': 'morelink'})
    if more_a is None:
        return False
    else:
        # If there's a "More" link at the bottom of the page, then
        # there's a next page
        return True

def extract_comment_page(comment_tr: bs4.Tag, comment_tree_table: bs4.Tag) -> Tuple[Item, Tree]:
    """Process HTML for a comment page."""

    # extract main comment info
    main_item_id = int(comment_tr['id'])
    content = extract_comment_info(comment_tr)
    item = Item(main_item_id, content=content)

    # extract comment tree
    comment_tree_ds = extract_comment_tree_ds(comment_tree_table)
    comment_tree = extract_comment_tree(main_item_id, comment_tree_ds)
    item.content.update({'kids': comment_tree})

    return item, comment_tree 

def extract_post_page(post_tr: bs4.Tag, post_td: bs4.Tag, comment_tree_table: bs4.Tag) -> Tuple[Item, Dict]:
    """Process HTML for a post page."""
    
    # extract main post info
    main_item_id = int(post_tr['id'])
    content = extract_post_item_main(post_tr)
    item = Item(main_item_id, content=content)

    # extract subtext info
    _, subtext_info = extract_post_item_subtext(post_td)
    item.content.update(subtext_info)
    
    # extract comment tree
    comment_tree_ds = extract_comment_tree_ds(comment_tree_table)
    comment_tree = extract_comment_tree(main_item_id, comment_tree_ds)
    item.content.update({'kids': comment_tree})

    return item, comment_tree

def extract_news_page(t: bs4.Tag) -> Tuple[Dict, Dict]:
    """Process HTML for a news page."""
    items = OrderedDict()
    ranks = dict()

    for child in t.children:
        if child == '\n' or bool(child.contents) is False:
            continue
        # <tr> tags with class 'athing' are posts
        if child.has_attr('class') and child['class'][0] == 'athing':
            # post title with story URL, rank, and site string
            item_id = int(child['id'])
            content = extract_post_item_main(child)
            ranks[item_id] = extract_rank(child)
            items[item_id] = Item(item_id, content=content)
        else:
            # most of the other <tr> tags are subtexts under the post
            subtext_td = child.find('td', attrs={'class' : 'subtext'})
            if subtext_td is not None:
                item_id, subtext_info = extract_post_item_subtext(subtext_td)
                # find the appropriate Item and update its content
                i = items[item_id]
                i.content.update(subtext_info)

    return ranks, items

def extract_ranks(itemlist_table: bs4.Tag) -> Dict[int, int]:
    """Extracts all of the ranks for the Items on a given News Page."""
    pass

def extract_rank(t: bs4.Tag) -> int:
    """Extract rank from an Item on a news page."""
    # get rank, if it exists
    rank_span = t.find('span', attrs={'class': 'rank'})
    rank = int(rank_span.string.split('.')[0]) if rank_span.string else ''
    return rank


