# Description

This document describes the architecture of the `rich-hn` reader app.

# High-Level Overview
`rich-hn`'s design emphasizes performance and modularity. The app uses caching and fast-access data structures like dictionaries in order to maintain a fast, performant experience.

- Data Model
    - Content-wise, everything on HN (i.e. everything you read) is an Item.
    - Items are displayed on different Pages of HN in different forms. Items can be displayed on a news page (as shown [here](https://news.ycombinator.com/news)), the main page for a post (as shown [here](https://news.ycombinator.com/item?id=25630011)), or on a comment page for comments on a post (as seen [here](https://news.ycombinator.com/item?id=25630456)).
    - All Items have an associated type, which is one of poll, pollopt, job, story, or comment.
    - The unique identifier of an Item is an `id`, and as such, this is the only identifier that Items must have. Most items, however, have many more attributes as well.
        - The result of this specification is that an Item, defined generically, looks like:
        ```bash
        Item {
            id: int
            content: dict
        }
        ```
        where `content` is a `dict` that holds arbitrary key-value pairs. This allows us to process various types of Items in a fairly general way, but creates more complexity when we have to display the items in a given Page. This also makes parsing out the features of an item more difficult.

# Low-Level Overview
