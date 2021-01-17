from typing import Dict, Tuple, List
import re
import html

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

    def get_text(self):
        """Get text content of this Item or return None if there is no content."""
        if self.content is not None:
            return self.content.get('text', None)

    def get_id(self):
        """Get ID of this Item."""
        return self.item_id

    def get_kids(self):
        """Get child comment Tree of this Item or return None if there are None."""
        if self.content is not None:
            return self.content.get('kids', None)

    def get_score(self):
        """Get score of this Item or return None if there is no score."""
        if self.content is not None:
            return self.content.get('score', None)

    def get_user(self):
        """Get the user who posted this Item or return None if there is no user."""
        if self.content is not None:
            return self.content.get('user', None)

    def get_total_comments(self):
        """Get the total number of comments on this Item or return None if there are None."""
        if self.content is not None:
            return self.content.get('total_comments', None)

    def get_item_type(self):
        """Get the type of this Item."""
        if self.content is not None:
            return self.content.get('type')

    def get_parent_id(self):
        """Get ID of the parent of this Item, or return None if there is no parent."""
        if self.content is not None:
            return self.content.get('parent', None)

    def get_title(self):
        """Get the title of this Item, or return None if there is no title."""
        if self.content is not None:
            return self.content.get('title', None)

    def get_url(self):
        """Get the URL of this Item."""
        if self.content is not None:
            return self.content.get('url')

    def get_sitebit(self):
        """Get the sitebit of this Item, or return None if there is no sitebit."""
        if self.content is not None:
            return self.content.get('sitebit', None)

ITEM_TYPE = {
    'STORY' : 'story',
    'JOB' : 'job',
    'COMMENT' : 'comment',
    'POLL' : 'poll',
    'POLLOPT' : 'pollopt'
}

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

def extract_comment_tree_ds(comment_tree_table: bs4.Tag) -> Tuple[List[int], List[int],
    List[Item], List[slice]]:
    """Generate data structures representing a comment tree."""
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

    # a sorted list of unique indents, used to help us determine
    # other indents relative to any comment's given indent.
    sorted_indents = sorted(list(set(indents)))

    return ids, indents, sorted_indents, items

def extract_comment_tree(item_id: int, comment_tree_ds: Tuple[List[int], List[int],
    List[int], List[Item]]) -> Dict:
    """Extracts the comment tree for a given item."""
    ids, indents, sorted_indents, items = comment_tree_ds
   
    comment_lineage = extract_lineage(item_id, (ids, indents, sorted_indents, items))

    return comment_lineage

def extract_lineage(p_id: int, partial_tree_ds: Tuple[List[int], List[int],
    List[int]]) -> Dict[int, List]:
    """Extract comment lineage."""
    ids, indents, sorted_indents, items = partial_tree_ds
    comment_lineage = {}
    lineage = []
    for index, item_id in enumerate(ids):
        # if we're not at the last comment in the list
        if index + 1 <= len(ids) - 1:
            # the current comment's lineage is complete
            lineage.append((item_id, items[index]))
            comment_lineage[item_id] = lineage.copy()

            # compare the indent of the current comment with the indent
            # of the next one to get a comparison of how indented
            # they are relative to one another. Use the list of sorted
            # indents for this purpose
            indent_diff = \
                sorted_indents.index(indents[index + 1]) - sorted_indents.index(indents[index])
            if indent_diff > 0:
                # since the next comment is more indented than the current 
                # one, the lineage for that comment will include this 
                # comment as well. The code is more readable with this explanation,
                # which is why this conditional is left here.
                pass
            elif indent_diff == 0:
                # since the next comment has the same level of indentation as the
                # current one, their lineages are almost the same, with the only 
                # difference being those comments themselves. So, after forming the 
                # proper lineage for the current comment (done above), remove it 
                # from the lineage so the next comment can add itself to the lineage.
                lineage.pop()
            else:
                # as the next comment is less indented than the current one, the 
                # lineage for that comment will not include one or more of the 
                # members of the current comment's lineage. We should remove 
                # members from the lineage until the indent difference is zero,
                # meaning that we've found a common ancestor for the two commments.
                # It's possible we won't find a common ancestor, in which case, the
                # lineage will be empty, implying that the next comment is a first-level
                # comment
                lineage.pop()
                while indent_diff < 0:
                    lineage.pop()
                    indent_diff += 1
        else:
            # the last comment on the page, regardless of indentation level,
            # only needs to add itself to the existing lineage in whatever
            # form that might take. This is because the second-to-last comment
            # has already examined the indentation level of the last comment
            # with respect to itself, and appropriately adjusted the lineage
            # to be accurate.
            lineage.append((item_id, items[index]))
            comment_lineage[item_id] = lineage.copy()
    
    return comment_lineage

def extract_post_item_main(post_tr: bs4.Tag) -> Dict:
    """Extract the information from the main/header content of a post."""              
    content = dict()
    item_id = int(post_tr['id'])
  
    # get post title, associated links, if present
    story_a = post_tr.find('a', attrs={'class': 'storylink'})
    if story_a is not None:
        url = story_a['href']
        title = story_a.string
        content['url'] = url
        content['title'] = title

    # get sitebit description beside main site title, if it exists
    sitebit_space = post_tr.find('span', attrs={'class': 'sitestr'})
    site_bit = sitebit_space.string if sitebit_space is not None else ''
    content['sitebit'] = site_bit
    sitebit_present = bool(site_bit)

    # see if votelinks are present, indicating if post is a jobs post or not
    votelinks = post_tr.find('td', attrs={'class': 'votelinks'})
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
    user_a = t.find('a', attrs={'class' : 'hnuser'})
    user = user_a.string if user_a is not None else ''
    content['user'] = user

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