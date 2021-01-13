from typing import Dict, Tuple
import re
import html

from common import get_html, HN_ITEMS_URL, HN_API_ITEMS_URL

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

# Extraction functions: here, we extract useful information from
# the HTML or JSON obtained from the HN site directly or the HN API.
def extract_comment_info(t: bs4.Tag) -> Dict:
    """Extract information from a comment on HN."""
    content = dict()
    content['type'] = ITEM_TYPE['COMMENT']

    comhead_span = t.find('span', attrs={'class' : 'comhead'})

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

    commtext_span = t.find('span', attrs={'class' : 'commtext c00'})
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