# Description

This document describes the architecture of the `rich-hn` reader app.

# High-Level Overview
`rich-hn`'s design emphasizes performance and modularity. The app uses caching and fast-access data structures like dictionaries in order to maintain a fast, performant experience.

- Data Model
    - `Item`: the "meat" of the application, both in terms of data and presentation. `Item`s correspond directly with HN's notion of items described by their [API](https://github.com/HackerNews/API).
    - `Page`: a presentation layer over a given `Item`, as an `Item` can have multiple pages associated with it.
    - `Pages`: a collection of `Page` objects, which in sum represent all of the content associated with a given `Item`.
    - `ItemDB`: a database that keeps track of global `Item` state throughout the lifetime of the application.

- Display
    - TODO
- UX
    - TODO

# Low-Level Overview
- Data Model
    - `Item`
        - Content-wise, everything on HN (i.e. everything you read) is an `Item`.
        - `Item`s are displayed on different `Page`s of HN in different forms. `Item`s can be displayed on a news page (as shown [here](https://news.ycombinator.com/news)), the main page for a post (as shown [here](https://news.ycombinator.com/item?id=25630011)), or on a comment page for comments on a post (as seen [here](https://news.ycombinator.com/item?id=25630456)).
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
    - `Page`
        - The specification for a Page looks like:
            ```bash
            Page {
                pg_number: int
                has_next: bool
            }
            ```
            where the `pg_number` field is used to indicate the current page on HN, and `has_next` is a field used to indicate if there's a next page or not.
            - There are currently three subclasses of `Page`: `NewsPage`, `CommentPage`, and `PostPage`. These correspond to the types of ways the content of different `Item`s are displayed on HN.
                - `NewsPage`s correspond to the page one sees when visiting the main site, [news.ycombinator.com](https://news.ycombinator.com).  
                    - `NewsPage`s retain a notion of the rank of the `Item`s displayed on them.
                - `CommentPage`s correspond to the page one sees when they click on a comment. `PostPage`s encompass everything else, including jobs posts, normal story posts, and polls. 
                    - Both `CommentPage`s and `PostPage`s maintain an idea of things like the ID of the post they're associated with, what, if any, child comments are associated with the particular comment/post, they type of `Item` they refer to (for `CommentPage`s, this is always "comment", but for `PostPage`s, these can be "jobs", "poll", or "story" -- note that while `Item`s can also have a "pollopt" type, "pollopt"s don't correspond directly with pages in the way that the other `Item` types do).
    - `Pages`
        - A collection of pages
    - `ItemDB`
        - This class is implemented using the [Singleton Pattern](https://python-patterns.guide/gang-of-four/singleton/), since only one `ItemDB` is ever needed throughout the life cycle of the application.
- Display
- UX