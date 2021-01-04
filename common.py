"""Functionality used for working with Items and Pages."""
import requests

HN_BASE_URL = 'https://news.ycombinator.com/'
HN_NEWS_URL = HN_BASE_URL + 'news'
HN_ITEMS_URL = HN_BASE_URL + 'item'

HN_API_BASE_URL = 'https://hacker-news.firebaseio.com/v0/'
HN_API_ITEMS_URL = HN_API_BASE_URL + 'item/'

def get_html(url: str) -> str:
    """Gets the HTML of the content indicated by the URL."""
    # no caching here
    headers = {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    r = requests.get(url, headers=headers)
    return r.text