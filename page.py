from collections import OrderedDict
from typing import Dict, Tuple, Any
import textwrap
import math

from common import get_html, HN_NEWS_URL
from items import Item, extract_post_item_main, extract_post_item_subtext, extract_post_item_text, \
    extract_comment_info, extract_comment_tree, extract_comment_tree_ds, ITEM_TYPE
from tree import Tree

import bs4
import colorama
from colorama import Fore, Back
colorama.init(autoreset=True)

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
            s += '{:>3}. {} ({})\n'.format(rank, self.items[item_id].get_title(), item_id)
        return s

class CommentPage(Page):
    """Represents a page containing a comment and any subcomments."""
    item: Item = None
    comments: Dict = None
    # comment pages have a dict member called items, but this dict
    # will only ever have one key that corresponds to the main item
    # on the comment page itself
    def __init__(self, pg_number, has_next, item: Item = None,
        comments = None):
        super().__init__(pg_number, has_next)
        self.item = item
        self.comments = comments

    def __str__(self):
        s = ''
        s += '{}:\n'.format(self.item.get_user())
        main_comment = prettify_string(self.item.get_text(), '')
        s += main_comment + '\n'
        if self.comments is not None:
            for lineage in self.comments.values():
                comment = lineage[-1][1]
                ind = '  ' * len(lineage)
                s += Fore.BLUE + '{}{}'.format(ind, comment.get_user() + ':')
                s += '\n'
                pretty_comment = prettify_string(comment.get_text(), ind)
                s += pretty_comment
        return s

class PostPage(Page):
    """Represents a page containing the frontmatter of a post on HN, as well as any associated comments."""
    item: Item = None
    comments: Dict = None
    # post pages have a dict member called items, but this dict
    # will only ever have one key that corresponds to the main item
    # on the post page itself
    def __init__(self, pg_number, has_next, item: Item = None,
        comments = None):
        super().__init__(pg_number, has_next)
        self.item = item
        self.comments = comments

    def __str__(self):
        s = ''
        s += '{}\n'.format(self.item.get_title())
        main_description = self.item.get_text()
        if main_description is not None:
            pretty_description = prettify_string(main_description, '')
            s += pretty_description
            s += '\n'
        parts = self.item.get_parts()
        if parts is not None:
            for pollitem in parts:
                s += '\t' + pollitem.get_text() + '\n\t' + pollitem.get_score()
                s += '\n\n'
            s += '\t===================================\n\n'
        if self.comments is not None:
            for lineage in self.comments.values():
                comment = lineage[-1][1]
                ind = '  ' * len(lineage)
                s += Fore.BLUE + '{}{}'.format(ind, comment.get_user() + ':')
                s += '\n'
                pretty_comment = prettify_string(comment.get_text(), ind)
                s += pretty_comment
        return s

def prettify_string(text: str, ind: str, width=80) -> str:
    """Prettifies a string into a string justified by ind."""
    text_blobs = text.split('<p>')
    fins = ''
    for text_blob in text_blobs:
        t = textwrap.fill(text_blob, width=width, break_long_words=False, break_on_hyphens=False)

        # handle inline quotes
        if t.startswith('>'):
            # number of newlines tells us number of lines in the wrapped
            # text
            num_newlines = t.count('\n')
            # short comment
            if num_newlines == 0:
                t = '{}{}{}'.format(Back.CYAN, t, Back.RESET)
            else:
                j = ''
                len_t = len(t)
                start_range = 0
                for i in range(0, num_newlines):
                    newline_idx = t.find('\n', start_range)
                    # last section of string (after a newline)
                    if newline_idx == -1:
                        j += '{}{}{}'.format(Back.CYAN, t[start_range:len_t], Back.RESET)
                    else:
                        j += '{}{}{}'.format(Back.CYAN, t[start_range: newline_idx + 1], Back.RESET) 
                        start_range = newline_idx + 1
                t = j

        # make all links red in color
        num_links = t.count('[link=')
        if num_links != 0:
            start_range = 0
            t_len = len(t)
            j = ''
            for i in range(num_links):
                idx_start = t.find('[link=', start_range)
                idx_end = t.find(']', idx_start)
                begin_j = t[start_range: idx_start]
                link_part_j = '{}{}{}'.format(Fore.RED, t[(idx_start + len('[link=')): idx_end], Fore.RESET)

                # last iteration (i.e. getting last link + other text after, if any)
                if i == num_links - 1:
                    end_j = t[idx_end + 1: t_len]   
                else:
                    # There are more links after this one, so don't
                    # get any text after the link ends. 
                    # Instead, set start_range appropriately so it
                    # starts right after the end of the link's closing
                    # ] bracket.
                    end_j = ''
                    start_range = idx_end + 1

                j += begin_j + link_part_j + end_j
            t = j
        fins += textwrap.indent(t, prefix=ind) + '\n\n'
    return fins

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

    # If there is a <td> with class equal to "subtext" on the
    # page, that indicates that we're looking at a post page,
    # rather than a comment page
    subtext_td = soup.find('td', attrs={'class': 'subtext'})
    is_comment_page = True if subtext_td is None else False

    if is_comment_page:
        # construct Comment Page object
        comment_tr = soup.find('tr', attrs={'class' : 'athing'})
        comment_tree_table = soup.find('table', attrs={'class' : 'comment-tree'})
        item, comment_tree = extract_comment_page(comment_tr, comment_tree_table)
        return CommentPage(pg_num, has_next, item=item, comments=comment_tree)
    else:
        # construct Post Page object
        fatitem_table = soup.find('table', attrs={'class': 'fatitem'})
        post_tr = soup.find('tr', attrs={'class' : 'athing'})
        post_td = soup.find('td', attrs={'class' : 'subtext'})
        comment_tree_table = soup.find('table', attrs={'class' : 'comment-tree'})
        item, comment_tree = extract_post_page(fatitem_table, post_tr, post_td, comment_tree_table)
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
    comment_tree = None
    if comment_tree_table is not None:
        comment_tree_ds = extract_comment_tree_ds(comment_tree_table)
        comment_tree = extract_comment_tree(main_item_id, comment_tree_ds)
    item.content.update({'kids': comment_tree})

    return item, comment_tree 

def extract_post_page(fatitem_table: bs4.Tag, post_tr: bs4.Tag, post_td: bs4.Tag,
    comment_tree_table: bs4.Tag) -> Tuple[Item, Dict]:
    """Process HTML for a post page."""
    
    # extract main post info
    main_item_id = int(post_tr['id'])
    content = extract_post_item_main(post_tr)
    item = Item(main_item_id, content=content)

    # extract subtext info
    _, subtext_info = extract_post_item_subtext(post_td)
    item.content.update(subtext_info)

    # extract text content of the post based on the type
    # of the post (Story, Job, Poll)
    text, pollopts = extract_post_item_text(item.content['type'], fatitem_table)
    item.content.update({'text' : text})
    # add polloptions to the 'parts' member of this item
    if pollopts:
        item.content.update({'parts': pollopts})

    # extract comment tree, if applicable
    comment_tree = None
    if item.content['type'] != ITEM_TYPE['JOB'] and comment_tree_table is not None:
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

def extract_ranks(html_or_tag: Any) -> Dict[int, Tuple[int, str]]:
    """Extracts all of the ranks for the Items on a given News Page."""
    # this way, we can pass in pre-bs4'd stuff or raw stuff
    if type(html_or_tag) is str:
        itemlist_table = bs4.BeautifulSoup(html_or_tag, 'html.parser')
    else:
        itemlist_table = html_or_tag

    ranks = {}
    # get all <tr> with class 'id' and class 'athing'
    athing_trs = itemlist_table.find_all('tr', attrs={'class': 'athing'})
    for tr in athing_trs:
        item_id = int(tr['id'])

        # extract text of <span> element with class of "rank"
        rank_span = tr.find('span', attrs={'class': 'rank'})
        rank_text = rank_span.text
        rank = int(rank_text[0:len(rank_text) - 1])

        storylink_a = tr.find('a', attrs={'class': 'storylink'})
        title = storylink_a.text

        ranks[rank] = (item_id, title)
    return ranks

def extract_rank(t: bs4.Tag) -> int:
    """Extract rank from an Item on a news page."""
    # get rank, if it exists
    rank_span = t.find('span', attrs={'class': 'rank'})
    rank = int(rank_span.string.split('.')[0]) if rank_span.string else ''
    return rank


