from typing import Dict, Tuple
import json
import collections

import bs4
import requests

class Post(object):
    """Represents a post on Hacker News."""
    post_id = None
    content = None

    def __init__(self, post_id: int, content: dict = None):
        self.post_id = post_id
        self.content = content

    def __str__(self):
        return str(self.post_id) + ' ' + str(self.content)

POST_TYPE = {
    'STORY' : 'story',
    'JOB' : 'job',
    'COMMENT' : 'comment',
    'POLL' : 'poll',
    'POLLOPT' : 'pollopt'
}

HN_BASE = 'https://news.ycombinator.com/'
HN_NEWS = HN_BASE + 'news'
HN_API_BASE = 'https://hacker-news.firebaseio.com/v0/'
HN_API_ITEMS = HN_API_BASE + 'item/'

def get_posts_on_page(page_num: int):
    posts = process_page(get_page(page_num))
    return posts

def process_page(text: str) -> Dict:
    """Processes text representing HTML for a page of HN, returning Posts."""
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
                    post_id = int(child['id'])
                    content = extract_thing_info(child)
                    posts[post_id] = Post(post_id, content=content)
                    # print("Added post with ID {} to dictionary. Content: {}".format(post_id, posts[post_id]))
                else:
                    continue
            else:
                for descendant in child.children:
                    if descendant.has_attr('class') and descendant['class'][0] == 'subtext':
                        item_id, subtext_info = extract_subtext_info(child)
                        # find the appropriate Post and update its content
                        p = posts[item_id]
                        p.content.update(subtext_info)
    else:
        posts = None

    return posts

def extract_subtext_info(t: bs4.Tag) -> Tuple[int, Dict]:
    """Extract the information from a tag corresponding to subtext of a post on main page of HN."""
    subtext_info = dict()

    # get the score/points, if it exists
    score_span = t.find('span', attrs={'class' : 'score'})
    score = ''
    if score_span is not None:
        score_string = score_span.string
        # find 'point' in the score string
        point_idx = score_string.find('points')
        score = int(score_string[0:point_idx])
    subtext_info['score'] = score

    # get the HN user, if it exists (it won't for jobs posts)
    hnuser_a = t.find('a', attrs={'class' : 'hnuser'})
    hnuser = hnuser_a.string if hnuser_a is not None else ''
    subtext_info['hnuser'] = hnuser

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
    subtext_info['total_comments'] = num_comments

    return post_id, subtext_info

def extract_thing_info(t: bs4.Tag) -> Dict:
    """Extract the information from a tag corresponding to title of a post on main page of HN."""              
    content = dict()

    # get rank, if it exists
    rank_span = t.find('span', attrs={'class': 'rank'})
    rank = int(rank_span.string.split('.')[0]) if rank_span.string else ''
    content['rank'] = rank

    # get post title, associated links
    story_a = t.find('a', attrs={'class': 'storylink'})
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

    votelinks = t.find('td', attrs={'class': 'votelinks'})
    votelink_present = True if votelinks is not None else False
    post_id = int(t['id'])
    content['type'] = extract_type(post_id, title, votelink_present, sitebit_present)

    return content

def extract_type(post_id: int, title: str , votelink_present: bool,
    sitebit_present: bool):
    """Extracts the type of a post on main page of HN using tag-derived information."""

    # Jobs posts are the only ones that don't have voting links
    if not votelink_present:
        return POST_TYPE['JOB']
    elif title.startswith('Ask HN:') or title.startswith('Tell HN:') or \
        title.startswith('Show HN:'):
        return POST_TYPE['STORY']
    elif sitebit_present:
        # "normal" story posts on HN that don't fall into the Ask/Show/Tell HN
        # conditional have a sitebit present since they link to URLs
        return POST_TYPE['STORY']
    elif title.startswith('Poll:'):
        return POST_TYPE['POLL']
    else:
        # call the API to get the type for the given post
        url = HN_API_ITEMS + '{}.json'.format(post_id)
        p_data = requests.get(url).json()
        p_type = p_data['type'].upper()
        return POST_TYPE[p_type]
    
def get_page(page_num: int) -> str:
    """Returns the HTML content for a given page of HN."""
    page_url = HN_NEWS + '?p={}'.format(page_num)

    return get_html(page_url)

def get_html(url: str) -> str:
    # no caching here
    headers = {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    r = requests.get(url, headers=headers)
    return r.text
