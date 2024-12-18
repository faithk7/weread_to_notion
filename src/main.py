import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, Tuple

import requests
from notion_client import Client

from book import Book, BookService, get_children, get_notebooklist
from constants import WEREAD_URL
from logger import logger
from notion import NotionManager
from util import parse_cookie_string
from weread import WeReadClient


def parse_arguments() -> Tuple[str, str, str]:
    parser = argparse.ArgumentParser()
    for arg in ["weread_cookie", "notion_token", "database_id"]:
        parser.add_argument(arg)
    options = parser.parse_args()
    return options.weread_cookie, options.notion_token, options.database_id


def process_book(
    book_json: Dict[str, Any],
    latest_sort: int,
    notion_manager: NotionManager,
    book_service: BookService,
) -> None:
    sort = book_json.get("sort")
    if sort <= latest_sort:
        return
    book = Book.from_json(book_json)
    book = book_service.load_book_details(book)

    notion_manager.check_and_delete(book.bookId)

    children, grandchild = get_children(book.chapters, book.summary, book.bookmark_list)
    logger.info(
        f"Current book: {book.bookId} - {book.title} - {book.isbn} - bookmark_list: {book.bookmark_list}"
    )
    id = notion_manager.insert_to_notion(book, session)
    results = notion_manager.add_children(id, children)
    if len(grandchild) > 0 and results is not None:
        notion_manager.add_grandchild(grandchild, results)


if __name__ == "__main__":
    weread_cookie, notion_token, database_id = parse_arguments()

    notion_manager = NotionManager(notion_token, database_id)
    latest_sort = notion_manager.get_latest_sort()

    session = requests.Session()
    session.cookies = parse_cookie_string(weread_cookie)
    session.get(WEREAD_URL)

    notion_client = Client(auth=notion_token, log_level=logging.ERROR)
    weread_client = WeReadClient(session)
    book_service = BookService(weread_client)

    # NOTE: this is the starting point of getting all books
    books = get_notebooklist(session)

    assert books is not None, "获取书架和笔记失败"

    time = datetime.now()
    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(
                process_book,
                book_json,
                latest_sort,
                notion_manager,
                book_service,
            )
            for book_json in books
        ]
        for future in futures:
            future.result()
    logger.info("Total time: %s", datetime.now() - time)
