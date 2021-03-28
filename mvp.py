#!/usr/bin/env python3
import subprocess
import tempfile
import os

import pages
from page import NewsPage, PostPage, CommentPage

# return code for errors
ERROR_RC = -1
# return code for quitting the application
QUIT_RC = 0
# paths to location of data, temporary and saved files
DATA_PATH = './data'
TMPDIR_PATH = os.path.join(DATA_PATH, 'tmpdir')
SAVED_FILES_PATH = os.path.join(DATA_PATH, 'saved_files')

def app_setup():
    """Sets up the directories needed by the application."""
    paths = [DATA_PATH, TMPDIR_PATH, SAVED_FILES_PATH]
    for path in paths:
        # create non-existent directories
        if not os.path.exists(path):
            os.mkdir(path)
        else:
            pass

def main():
    app_setup()
    pgs = None

    # Main loop
    while(True):
        usr_input = input("\n\nActions:\n" + 
        "n: See the posts on the front page of Hacker News\n" +
        "n-{num_r},{num_k},...,{num_b}: See the posts on pages r, k,...,and b of Hacker News\n" +
        "i-{item_id}: Read item with ID={item_id}\n" +
        "r-{num}: Read the item with current rank={num} on the main Hacker News Page\n" + 
        "s: Save the last read post\n" + 
        "q: Quit the application\n" +
        "Desired Action: ")

        pgs, rc = handle_input(usr_input, pgs)

        if rc == 's':
            filename = input("You've indicated you want to save the most recently read post.\n" +
            "What name would you like to save it as?: ")
            with open(os.path.join(SAVED_FILES_PATH, filename), 'w') as j:
                print(pgs, file=j, flush=True)
                print("Successfully saved the file at: {}!".format(j.name))
        elif rc == QUIT_RC:
            # clean out the temporary file directory
            for filename in os.listdir(TMPDIR_PATH):
                os.remove(os.path.join(TMPDIR_PATH, filename))
            break
        elif rc == ERROR_RC:
            print("Invalid control sequence. Please try again. :)")
        else:
            f, f_name = tempfile.mkstemp(suffix=".txt", dir=TMPDIR_PATH, prefix="hn-", text=True)
            f = os.fdopen(f, mode='w')
            print(pgs, file=f, flush=True)
            # Using less with -R in MVP to see colored output
            subprocess.run(['less', '-R', f_name])
            f.close()

def handle_input(input: str, pgs: pages.Pages):
    """Handle user input and return Pages and a return code."""
    rc = ''
    if input.strip().lower() == 'n':
        pgs = pages.get_news_pages_by_num([1])
    elif input.strip().lower() == 's':
        # save text version of a given page
        rc = 's'
    elif input.strip().lower() == 'q':
        # quit the program
        rc = QUIT_RC
    elif input.startswith('n') and len(input.split('-')) > 1:
        pg_nums = []
        values = input.split('-')[1]
        values = [int(v) for v in values.split(',')]
        pg_nums.extend(values)
        pgs = pages.get_news_pages_by_num(pg_nums)
    elif input.startswith('r') and len(input.split('-')) > 1:
        item_rank = int(input.split('-')[1])
        post_id, _ = pages.get_post_by_rank(item_rank)
        pgs = pages.get_post_pages_by_id(post_id)
    elif input.startswith('i') and len(input.split('-')) > 1:
        item_id = int(input.split('-')[1])
        pgs = pages.get_post_pages_by_id(item_id)
    else:
        # invalid control sequence
        rc = ERROR_RC

    return pgs, rc

if __name__ == "__main__":
    main()