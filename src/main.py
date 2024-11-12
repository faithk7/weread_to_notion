import argparse
import logging

import requests
from notion_client import Client

from book import get_bookinfo, get_bookmark_list, get_chapter_info, get_review_list
from constants import WEREAD_URL
from notion import (
    add_children,
    add_grandchild,
    check,
    get_children,
    get_notebooklist,
    get_sort,
    insert_to_notion,
)
from util import parse_cookie_string

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("weread_cookie")
    parser.add_argument("notion_token")
    parser.add_argument("database_id")
    options = parser.parse_args()
    weread_cookie = options.weread_cookie
    database_id = options.database_id
    notion_token = options.notion_token
    session = requests.Session()
    session.cookies = parse_cookie_string(weread_cookie)
    client = Client(auth=notion_token, log_level=logging.ERROR)
    session.get(WEREAD_URL)
    latest_sort = get_sort()
    books = get_notebooklist()
    if books is not None:
        for book in books:
            sort = book["sort"]
            if sort <= latest_sort:
                continue
            book = book.get("book")
            title = book.get("title")
            cover = book.get("cover")
            bookId = book.get("bookId")
            author = book.get("author")
            check(bookId)
            chapter = get_chapter_info(session, bookId)
            bookmark_list = get_bookmark_list(session, bookId)
            summary, reviews = get_review_list(session, bookId)
            bookmark_list.extend(reviews)
            bookmark_list = sorted(
                bookmark_list,
                key=lambda x: (
                    x.get("chapterUid", 1),
                    (
                        0
                        if (
                            x.get("range", "") == ""
                            or x.get("range").split("-")[0] == ""
                        )
                        else int(x.get("range").split("-")[0])
                    ),
                ),
            )
            isbn, rating = get_bookinfo(session, bookId)
            children, grandchild = get_children(chapter, summary, bookmark_list)
            id = insert_to_notion(title, bookId, cover, sort, author, isbn, rating)
            results = add_children(id, children)
            if len(grandchild) > 0 and results is not None:
                add_grandchild(grandchild, results)