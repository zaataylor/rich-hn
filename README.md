# Description

This is a CLI-based reader for [Hacker News](https://news.ycombinator.com/)! `rich-hn` will use the `curses` library (and potentially some capabilities from the [`rich`](https://github.com/willmcgugan/rich) Python library) to format Hacker News in a beautiful way.

Currently, an MVP version of the application is available, and details on how to run it can be found below. 

# Prerequisites

- Python 3.7+
- Pipenv tool

# Running the App

## MVP
1. Clone the project repo and `cd` into it:
```bash
git clone https://github.com/zaataylor/rich-hn
cd rich-hn
```
2. Install the required dependencies and activate a virtual environment by running the following:
```bash
pipenv install
```
3. Run `python mvp.py` to start the application
4. Have fun! :)

## Final Version
- Not Implemented Yet

# Feature Roadmap

Here's a quick summary of `rich-hn`'s feature roadmap:

Implementation Status Symbols
| Symbol     | Description             |
|------------|-------------------------|
| **&check;**| **Done**                |
| **_WIP_**  | **Work In Progress**    |
| **_NYI_**  | **Not Yet Implemented** |


- [**_NYI_**] Vim standard keybindings (`h`, `j`, `k`, `l`) for scrolling up and down, and navigating forward and backward through pages.
- [**_NYI_**] Up and down arrow keys for scrolling up and down, and navigating to forward and backward through pages using the left and right arrow keys.
- [**_NYI_**] Make the keybindings for scrolling and navigating customizable
- [**_NYI_**] Different colors for `Ask HN`, `Show HN`, `stories`, and `jobs` posts.
- [**_NYI_**] Manual updating of a page's contents using a specific keybinding.
- [**_WIP_**] `more` style scrolling UI.
- [**_WIP_**] Display posts in a table or list style.