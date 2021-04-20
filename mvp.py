#!/usr/bin/env python3
import subprocess
import tempfile
import os
import sqlite3

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
BOOKMARK_DB_PATH = os.path.join(DATA_PATH, 'bookmarks')

bookmarks = []

def app_setup() -> sqlite3.Connection:
    """Sets up the directories and DB needed by the application."""
    # Initialize paths
    paths = [DATA_PATH, TMPDIR_PATH, SAVED_FILES_PATH, BOOKMARK_DB_PATH]
    for path in paths:
        # create non-existent directories
        if not os.path.exists(path):
            os.mkdir(path)
        else:
            pass

    # Initialize persisted (or load the existing) DB
    con = sqlite3.connect(os.path.join(BOOKMARK_DB_PATH, 'bookmark.db'))
    cur = con.cursor()
    # Check to see if there is a table already by looking at count of tables with name == bookmarks
    cur.execute(''' SELECT count(name) from sqlite_master WHERE type='table' AND name='bookmarks' ''')
    if cur.fetchone()[0] == 1:
        # the table exists, get any bookmarks that might
        # already be in there
        bkmk_ids = [bkmk_id[0] for bkmk_id in cur.execute(''' SELECT id FROM bookmarks ''')]
        bookmarks.extend(bkmk_ids)
    else:
        # the table doesn't exist. Let's create it!
        cur.execute(''' CREATE TABLE bookmarks
                        (id integer UNIQUE, title text, url text) ''')
        # commit the change
        con.commit()
    
    # return the connection for later use
    return con

def main():
    con = app_setup()
    pgs = None

    # Main loop
    while(True):
        usr_input = input("\n\nActions:\n" + 
        "n: See the posts on the front page of Hacker News\n" +
        "n-{num_r},{num_k},...,{num_b}: See the posts on pages r, k,...,and b of Hacker News\n" +
        "i-{item_id}: Read item with ID={item_id}\n" +
        "r-{num}: Read the item with current rank={num} on the main Hacker News Page\n" + 
        "s: Save the last read post\n" +
        "b: Bookmark the last read post\n" +
        "b-a: Examine all currently saved bookmarks\n" +
        "q: Quit the application\n" +
        "Desired Action: ")

        pgs, rc = handle_input(usr_input, pgs)

        if rc == 's':
            filename = input("You've indicated you want to save the most recently read post.\n" +
            "What name would you like to save it as?: ")
            with open(os.path.join(SAVED_FILES_PATH, filename), 'w') as j:
                print(pgs, file=j, flush=True)
                print("Successfully saved the file at: {}!".format(j.name))
        elif rc == 'b':
            pg = pgs.get_current_page()
            pg_id = pg.item.get_id()
            pg_title = pg.item.get_title()
            pg_url = pg.item.get_url()

            try:
                cur = con.cursor()
                cur.execute(''' INSERT INTO bookmarks VALUES (?, ?, ?) ''', (pg_id, pg_title, pg_url))
                con.commit()
                bookmarks.append(pg_id)
            except sqlite3.IntegrityError:
                # we've tried to add a previously existing bookmark (based on ID)
                print("\nPost with ID={} already bookmarked!".format(pg_id))
        elif rc == 'b-a':
            cur = con.cursor()
            cur.execute(''' SELECT * FROM bookmarks ''')
            bkmks = cur.fetchall()
            for bkmk in bkmks:
                s = '{} || {} || {}'.format(bkmk[0], bkmk[1], bkmk[2]) 
                print(s)
        elif rc == QUIT_RC:
            # clean out the temporary file directory
            for filename in os.listdir(TMPDIR_PATH):
                os.remove(os.path.join(TMPDIR_PATH, filename))
            
            # close the DB connection
            con.close()
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
    elif input.strip().lower() == 'b':
        # bookmark the ID and title of the last read post
        rc = 'b'
    elif input.strip().lower() == 'b-a':
        # Examine all bookmarks
        rc = 'b-a'
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