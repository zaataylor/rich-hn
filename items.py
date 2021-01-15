from typing import Dict, Tuple, List
import re
import html
from collections import OrderedDict

from common import get_html, HN_ITEMS_URL, HN_API_ITEMS_URL
from tree import Tree

import bs4
import requests

class Item(object):
    """Represents an item on Hacker News."""
    item_id = None
    content = None

    def __init__(self, item_id: int, content: dict = None):
        self.item_id = item_id
        self.content = content

    def __str__(self):
        return str(self.item_id) + ' ' + str(self.content)

ITEM_TYPE = {
    'STORY' : 'story',
    'JOB' : 'job',
    'COMMENT' : 'comment',
    'POLL' : 'poll',
    'POLLOPT' : 'pollopt'
}

DUMMY_ITEM = None
DUMMY_ID = -1

# Extraction functions: here, we extract useful information from
# the HTML or JSON obtained from the HN site directly or the HN API.
def extract_comment_info(comment_tr: bs4.Tag) -> Dict:
    """Extract information from a comment on HN."""
    content = dict()
    content['type'] = ITEM_TYPE['COMMENT']

    comhead_span = comment_tr.find('span', attrs={'class' : 'comhead'})

    user = comhead_span.find('a', attrs={'class' : 'hnuser'})
    content['user'] = user.string

    par_span = comhead_span.find('span', attrs={'class' : 'par'})
    if par_span.string is not None:
        par_a = par_span.find('a')
        parent_id = int(par_a['href'].split('id=')[1])
        content['parent'] = parent_id

    storyon_span = comhead_span.find('span', attrs={'class' : 'storyon'})
    if storyon_span.string is not None:
        storyon_a = storyon_span.find('a')
        url = storyon_a['href']
        content['url'] = url

    comment_div = comment_tr.find('div', attrs={'class' : 'comment'})
    commtext_span = comment_div.find('span', attrs={'class': 'commtext'})
    if commtext_span is None:
        text = comment_div.contents[0].string
    else:
        text = extract_comment_text(commtext_span)
    content['text'] = text

    return content

def extract_comment_text(comment_text_span: bs4.Tag) -> str:
    """Extract the text content of a comment."""
    fins = ''
    for tag in comment_text_span.contents:
        if tag.name != 'div':
            # since we're using the raw string representation, which would include
            # named and numeric character references such as &gt; and &lt;, we want
            # to reprsent these as actual Unicode entities (i.e. > and <, respectively)
            fins += html.unescape(tag.__str__())

    # Mark where <i> tags were so Rich can make them italic
    # https://rich.readthedocs.io/en/latest/markup.html?highlight=italic#syntax
    fins = fins.replace('<i>', '[italic]')
    fins = fins.replace('</i>', '[/italic]')

    # Mark where blockquotes/code blocks are with a custom tag 
    # for rendering later on
    fins = fins.replace('<pre><code>', '[md]')
    fins = fins.replace('</code></pre>', '[/md]')

    # Replace <a href="...">...</a> tags inside of <p> elements with the other link 
    # style required by rich, using regex.
    # This regex pattern matches a string '<a href="', followed by one or more of the 
    # valid characters that can be in a URL 
    # (RFC 3986: https://tools.ietf.org/html/rfc3986#section-2),
    # followed by the string ' rel="nofollow">', followed by >= 1 valid URL characters, 
    # followed by '</a>', which indicates the end of an anchor tag
    fins = re.sub(
        r'<a href="([a-zA-Z0-9:~/.#@!$&+,;=()\'-]+)" rel="nofollow">([a-zA-Z0-9:~/.#@!$&+,;=()\'-]+)</a>',
        r'[link=\1]\2[/link]',
        fins)

    # Insert newlines where <p> tags are,
    # and empty strings where '</p>' are
    fins = fins.replace('<p>', '\n\n')
    fins = fins.replace('</p>', '')

    return fins

def make_comment_tree_ds(comment_tree_table: bs4.Tag) -> Tuple[List[int], List[int],
    List[Item], List[slice]]:
    """Generates data structures representing a comment tree."""
    raw_comments = comment_tree_table.find_all('tr', attrs={'class' : 'athing comtr'})
    indents = list()
    ids = list()
    items = list()
    for comment in raw_comments:
        # get indent, indicating nesting amount
        img = comment.find('img', attrs={'src' : 's.gif'})
        indent = int(img['width'])
        indents.append(indent)

        # get comment ID
        comment_id = int(comment['id'])
        ids.append(comment_id)

        # get comment content and create an Item with it
        content = extract_comment_info(comment)
        i = Item(comment_id, content=content)
        items.append(i)

    # get minimum indent
    min_indent = min(indents)
    # get indices of minimum indent over all the comments. These correspond to 
    # the first-level children of the main post/comment on a page, and will allow
    # us to optimize slices we make over a particular range of comments.
    min_indent_indices = list()
    for index, indent in enumerate(indents):
        if indent == min_indent:
            min_indent_indices.append(index)
    
    # A list of slice objects needed for later. The slices all start and stop
    # (inclusively) at an indices that correspond to first-level children.
    slices = list()
    start_pos = min_indent_indices[0]
    for index in min_indent_indices:
        if start_pos != index:
            slices.append(slice(start_pos, index + 1))
            start_pos = index
    
    # Here, we check to see whether or not the last indent in our list
    # of comments is a first-level comment or not. If it is a first-level
    # comment, that indent will have a value equal to the minimum indent.
    # However, if the last indent is _not_ a first-level comment, 
    # we need to add another slice that will encompass the comments from the
    # last first-level comment on the page to the last comment on the page. To do
    # so, we add dummy values at the ends of the ids, indents, and items lists in
    # order to signal an end to recursion when we work with these data structures
    # later on. This is why the slice extends to a stopping point of 
    # len(indents) + 1; as the stopping point is non-inclusive, this will 
    # encompass the range [min_indent_indices[-1] : len(indents)], where
    # the index with value equal to len(indents) corresponds to the index of the 
    # "dummy" values being inserted.
    if indents[-1] != min_indent:
        slices.append(slice(min_indent_indices[-1], len(indents) + 1))
        ids.append(DUMMY_ID)
        indents.append(min_indent)
        items.append(DUMMY_ITEM)

    # a sorted list of unique indents, used to help us determine
    # other indents relative to any item's given indent.
    sorted_indents = sorted(list(set(indents)))

    return ids, indents, sorted_indents, items, slices

def extract_comment_tree(item_id: int, comment_tree_ds: Tuple[List[int], List[int],
    List[int], List[Item], List[slice]]) -> Tree:
    """Extracts the comment tree for a given item."""
    ids, indents, sorted_indents, items, slices = comment_tree_ds
    tree = Tree(node_id=item_id)

    # Here, we partition the big comment tree into smaller slices whose
    # indices encompass adjacent first-level children.
    for sl in slices:
        # partial data based on slices
        prtl_comment_tree_ds = ids[sl], indents[sl], sorted_indents, items[sl]

        # the ID of the first item in this slice of ids is a first-level child
        p_id = ids[sl.start]
        # create the partial tree rooted at one of the first-level children
        p_tree = extract_partial_tree(p_id, prtl_comment_tree_ds)
        # add this subtree to the larger tree, which has a root at the
        # main item for a Post Page or Comment Page
        tree.add_child(p_id, p_tree)

    return tree

def extract_partial_tree(p_id: int, partial_tree_ds: Tuple[List[int], List[int],
    List[int], List[Item]]) -> Tree:
    """Extract a partial tree rooted at a first-level child."""
    ids, indents, sorted_indents, items = partial_tree_ds

    # get parent information using index of parent ID
    parent_index = ids.index(p_id)
    parent_id = ids[parent_index]
    parent_indent = indents[parent_index]
    parent_item = items[parent_index]

    # form parent tree
    tree = Tree(parent_id, data=parent_item)

    for idx, item_id_and_indent in enumerate(zip(ids, indents)):
        item_id, indent = item_id_and_indent
        # ignore ourselves and items before us
        if idx <= parent_index:
            continue
        else:
            idx_in_sorted_indents = sorted_indents.index(parent_indent)

            # Base Case 0: we're at the deepest possible indentation level for comments
            # on this page, so there's no way we'll see anymore children. 
            # We should stop here.
            if idx_in_sorted_indents == len(sorted_indents) - 1:
                break
            elif indent <= parent_indent:
                # Base Case 1: If indent is less than parent_indent, we are iterating over an
                # item that is at least at the indentation level of our direct parent 
                # (potentially more), meaning we don't have any of our own children left
                # to process and should stop where we are.
                # 
                # Base Case 2: If indent == parent_indent, we've reached an item at the same
                # level of indentation as we are, meaning we've already processed all of the
                # items that could've been our children, so we're done and should stop where
                # we are.
                break
            elif indent == sorted_indents[idx_in_sorted_indents + 1]:
                # Case: we've encountered an item with an indent that is exactly one
                # level greater than our own indentation level, meaning that this 
                # item is our direct child. So, we should add this child to our list
                # of children, then recurse to add that child's children. Note that we
                # can't break after adding this child, as it's possible we have more
                # direct children aside from the one we just found.
                child_tree = extract_partial_tree(item_id, partial_tree_ds)
                tree.add_child(item_id, child_tree)
            else:
                # Case: we've encountered one of our non-direct children, and should ignore
                # them since they'll be taken care of by one of our direct children.
                continue

    return tree

def extract_post_item_main(t: bs4.Tag) -> Dict:
    """Extract the information from the main/header content of a post."""              
    content = dict()
    item_id = int(t['id'])
  
    # get post title, associated links, if present
    story_a = t.find('a', attrs={'class': 'storylink'})
    if story_a is not None:
        url = story_a['href']
        title = story_a.string
        content['url'] = url
        content['title'] = title

    # get sitebit description beside main site title, if it exists
    sitebit_space = t.find('span', attrs={'class': 'sitestr'})
    site_bit = sitebit_space.string if sitebit_space is not None else ''
    content['sitebit'] = site_bit
    sitebit_present = bool(site_bit)

    # see if votelinks are present, indicating if post is a jobs post or not
    votelinks = t.find('td', attrs={'class': 'votelinks'})
    votelink_present = True if votelinks is not None else False

    content['type'] = extract_item_type(item_id, title, votelink_present,
        sitebit_present)

    return content

def extract_post_item_subtext(t: bs4.Tag) -> Tuple[int, Dict]:
    """Extract information from the subtext of a post."""
    content = dict()

    # get the score/points, if it exists
    score_span = t.find('span', attrs={'class' : 'score'})
    score = ''
    if score_span is not None:
        score_string = score_span.string
        # find 'point' in the score string
        point_idx = score_string.find('points')
        score = int(score_string[0:point_idx])
    content['score'] = score

    # get the HN user, if it exists (it won't for jobs posts)
    hnuser_a = t.find('a', attrs={'class' : 'hnuser'})
    hnuser = hnuser_a.string if hnuser_a is not None else ''
    content['hnuser'] = hnuser

    # use the age of the post to get the ID of it for matching with main title
    age_span = t.find('span', attrs={'class' : 'age'})
    a_tag = age_span.find('a')
    # example: href="item?id=3785593"
    item_id = int(a_tag['href'].split('id=')[1])

    # get the number of comments
    item_id_string = 'item?id={}'.format(item_id)
    comment_a = t.find_all('a', attrs={'href' : item_id_string})
    # jobs posts don't have comments, so the tag will only have one <a>
    if len(comment_a) == 1:
        num_comments = 0
    else:
        comments = comment_a[-1].string
        if comments == 'discuss':
            num_comments = 0
        else:
            # example: "99 comments"
            num_comments = int(comments.split('comment')[0])
    content['total_comments'] = num_comments

    return item_id, content

def extract_item_type(item_id: int, title: str , votelink_present: bool,
    sitebit_present: bool):
    """Extract the type of an item."""

    # Jobs posts are the only ones that don't have voting links
    if not votelink_present:
        return ITEM_TYPE['JOB']
    elif title.startswith('Ask HN:') or title.startswith('Tell HN:') or \
        title.startswith('Show HN:'):
        return ITEM_TYPE['STORY']
    elif sitebit_present:
        # "normal" story posts on HN that don't fall into the Ask/Show/Tell HN
        # have a sitebit present since they link to some URL
        return ITEM_TYPE['STORY']
    else:
        # call the API to get the type for the given post
        # this should only catch Poll types
        p_data = get_item_json_by_id(item_id)
        p_type = p_data['type'].upper()
        return ITEM_TYPE[p_type]

# Getting functions: these functions make the HTTP requests to
# HN or the HN API to get raw HTML or JSON that will be used by
# the extraction functions
def get_item_html_by_id(item_id: int) -> str:
    """Return the HTML content of the item with the given ID."""
    post_url = HN_ITEMS_URL + '?id={}'.format(item_id)
    return get_html(post_url)

def get_item_json_by_id(item_id: int) -> str:
    """Return the JSON data of the item with the given ID."""
    url = HN_API_ITEMS_URL + '{}.json'.format(item_id)
    p_data = requests.get(url).json()
    return p_data