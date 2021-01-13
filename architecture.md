# Description

This document describes the architecture of the `rich-hn` reader app.

# High-Level Overview
`rich-hn`'s design emphasizes performance and modularity. The app uses caching and fast-access data structures like dictionaries in order to maintain a fast, performant experience.

- Data Model
    - Content-wise, everything on HN (i.e. everything you read) is an Item.
    - `Item`s are displayed on different `Page`s of HN in different forms. Items can be displayed on a news page (as shown [here](https://news.ycombinator.com/news)), the main page for a post (as shown [here](https://news.ycombinator.com/item?id=25630011)), or on a comment page for comments on a post (as seen [here](https://news.ycombinator.com/item?id=25630456)).
    - All `Item`s have an associated type, which is one of poll, pollopt, job, story, or comment.
    - The unique identifier of an `Item` is an `id`, and as such, this is the only identifier that `Item`s _must_ have. Most `Item`s, however, have many more attributes as well.
        - The result of this specification is that an Item, defined generically, looks like:
        ```bash
        Item {
            id: int
            content: dict
        }
        ```
        where `content` is a `dict` that holds arbitrary key-value pairs. This allows us to process various types of `Item`s in a fairly generic way, but creates more complexity when we have to display the `Item`s on a given Page. This also makes parsing out the features of an `Item` more difficult.
    - The specification for a Page looks like:
        ```bash
        Page {
            pg_number: int
            items: dict
        }
        ```
        where `items` is a `dict` that has integer keys and `Item` values. The integer keys will correspond to `Item` IDs, and the values will be the `Item` with the ID identified by the key. The `pg_number` field is used to indicate the current page on HN.

- Display
    - TODO
- UX
    - TODO

# Low-Level Overview
