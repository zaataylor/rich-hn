from typing import Dict, Tuple

from common import get_html, HN_ITEMS_URL, HN_API_ITEMS_URL
from pages import Page, PostPage, CommentPage, NewsPage

import bs4

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

def get_item_html(post_id: int) -> str:
    """Returns the HTML content of the HN item with the given ID."""
    post_url = HN_ITEMS_URL + '?id={}'.format(post_id)
    return get_html(post_url)

def get_item_json(post_id: int):
    """Returns the JSON data of the HN item with the given ID."""
    url = HN_API_ITEMS_URL + '{}.json'.format(post_id)
    p_data = requests.get(url).json()
    return p_data

def extract_item_main_text(t: bs4.Tag, context: Page) -> Dict:
    """Extract the information from tag corresponding to the title of an item on HN."""              
    content = dict()

    post_id = int(t['id'])

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
    # empty strings considered False: all other strings are True
    sitebit_present = bool(site_bit)

    # see if votelinks are present, indicating if post is a jobs post or not
    votelinks = t.find('td', attrs={'class': 'votelinks'})
    votelink_present = True if votelinks is not None else False

    # see if the tag has a div with class of 'comment'.
    comment_div = t.find('div', attrs={'class': 'comment'})
    comment_present = True if comment_div is not None else False

    content['type'] = extract_item_type(post_id, title, votelink_present,
        sitebit_present, comment_present)

    return content

def extract_item_subtext(t: bs4.Tag) -> Tuple[int, Dict]:
    """Extract information from tag corresponding to subtext of an item on HN."""
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
    post_id = int(a_tag['href'].split('id=')[1])

    # get the number of comments
    item_id_string = 'item?id={}'.format(post_id)
    comment_a = t.find_all('a', attrs={'href' : item_id_string})
    # jobs posts don't have comments
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

    return post_id, content

def extract_item_type(post_id: int, title: str , votelink_present: bool,
    sitebit_present: bool, commenthead_present: bool):
    """Extracts the type of an item on HN using tag-derived information."""

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
    elif commenthead_present:
        return ITEM_TYPE['COMMENT']
    elif title.startswith('Poll:'):
        return ITEM_TYPE['POLL']
    else:
        # call the API to get the type for the given post
        p_data = get_post_by_id(post_id)
        p_type = p_data['type'].upper()
        return ITEM_TYPE[p_type]