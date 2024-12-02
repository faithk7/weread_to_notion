import argparse
import logging

import requests
from notion_client import Client

from book import (
    Book,
    get_bookmark_list,
    get_chapter_info,
    get_children,
    get_notebooklist,
    get_review_list,
)
from constants import WEREAD_URL
from notion import NotionManager
from util import parse_cookie_string

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("weread_cookie")
    parser.add_argument("notion_token")
    parser.add_argument("database_id")
    # TODO: add a arg parse method in the util.py
    options = parser.parse_args()

    weread_cookie = options.weread_cookie
    database_id = options.database_id
    notion_token = options.notion_token

    notion_manager = NotionManager(notion_token, database_id)

    session = requests.Session()
    session.cookies = parse_cookie_string(weread_cookie)
    client = Client(auth=notion_token, log_level=logging.ERROR)
    session.get(WEREAD_URL)

    latest_sort = notion_manager.get_sort()
    # NOTE: this is the starting point of getting all books
    books = get_notebooklist(session)

    assert books is not None, "获取书架和笔记失败"

    for book_json in books:
        # TODO: have a book object defined
        sort = book_json.get("sort")
        if sort <= latest_sort:
            continue

        book = Book(
            book_json.get("bookId"),
            book_json.get("title"),
            book_json.get("author"),
            book_json.get("cover"),
            book_json.get("sort"),
        )

        notion_manager.check_and_delete(book.book_id)
        chapter = get_chapter_info(session, book.book_id)
        bookmark_list = get_bookmark_list(session, book.book_id)
        summary, reviews = get_review_list(session, book.book_id)
        bookmark_list.extend(reviews)

        bookmark_list = sorted(
            bookmark_list,
            key=lambda x: (
                x.get("chapterUid", 1),
                (
                    0
                    if (x.get("range", "") == "" or x.get("range").split("-")[0] == "")
                    else int(x.get("range").split("-")[0])
                ),
            ),
        )
        book.set_bookinfo(session)

        children, grandchild = get_children(chapter, summary, bookmark_list)
        # TODO: have a NotionDBManager object
        id = notion_manager.insert_to_notion(book)
        results = notion_manager.add_children(id, children)
        if len(grandchild) > 0 and results is not None:
            notion_manager.add_grandchild(grandchild, results)
