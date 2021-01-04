import json

from get_posts import get_item_json, get_post_html

import requests
import bs4

# Steps:
#   - Call API to get kid comments list, title of post, number of comments, URL and/or description
#       text if it's included
    post_id = 0
    p_data = get_item_json(post_id)
    kids_list = p_data['kids']
    title = p_data['title']
    post_type = p_data['type']
    post_text = p_data['text']

    # get comment tree
    p_html = get_item_html(post_id)
    soup = bs4.BeautifulSoup(p_html, 'html.parser')
    comment_tree = soup.find('table', attrs={'class': 'comment-tree'})
    comments = comment_tree.find_all('tr')
    kids_dict = dict()
    kids_ranges = list()
    start_index = 0
    # construct data structures: a tuple with start and stop ranges for the
    # direct kids' indices, and a dictionary mapping those kids ID's to tags
    for index, comment in enumerate(comments):
        if int(comment['id']) in kids_list:
            # iterate over it, adding to the dict of kid ID - tag value
            kids_dict['id'] = comment
            # simultaneously create list of 3-tuples where a given tuple is form
            # (post_id, start_idx, end_idx) and end_ids is 1 + the first index of the next tag with ID
            # in the kids list
            if index != start_index:
                kids_ranges.append((comment['id'], start_index, index + 1))
                start_index = index
    
    # construct the comment tree

#   - For each <tr> tag in the comment-tree tag:
#       - if tag['id'] is not in kids:
#           - append tag to indirect-kids list
#       - else:
#           - if len(indirect-kids) > 0:
#               - c = get_children(tag, indirect-kids), a list of children Post objects
#               - make a Post object, p, out of current tag
#               - set this Post's object's content like so:
#                   - p.content['children'] = c
#           - else:
#               - set kids[tag['id']] = tag
#
#
#
#   get_children(tag: bs4.tag, indirect-kids: List[bs4.Tag])
#       need to think about this some more
#       

# Notes: every comment has the following HTML:
# <td class="ind">
#   <img src="s.gif" width="0" height="1">
# </td>
# notice that the img tag inside of class "ind" has a width that indicates how indented an item is