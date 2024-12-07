from typing import Dict, List, Optional, Tuple

import requests

from constants import (
    WEREAD_BOOK_INFO,
    WEREAD_BOOKMARKLIST_URL,
    WEREAD_CHAPTER_INFO,
    WEREAD_NOTEBOOKS_URL,
    WEREAD_READ_INFO_URL,
    WEREAD_REVIEW_LIST_URL,
)
from logger import logger
from util import get_callout_block


class Book:
    def __init__(self, book_id: str, title: str, author: str, cover: str, sort: int):
        self.book_id = book_id

        self.title = title
        self.author = author
        self.cover = cover
        self.sort = sort

        self.isbn = ""
        self.rating = 0.0

        self.bookmark_list = []
        self.summary = []
        self.reviews = []
        self.chapter_info = {}

    def set_bookinfo(self, session: requests.Session):
        params = dict(book_id=self.book_id)
        r = session.get(WEREAD_BOOK_INFO, params=params)
        if r.ok:
            data = r.json()
            self.isbn = data["isbn"]
            self.rating = data["newRating"] / 1000

    def set_summary(self, session: requests.Session):
        params = dict(book_id=self.book_id, listType=11, mine=1, syncKey=0)
        r = session.get(WEREAD_REVIEW_LIST_URL, params=params)
        reviews = r.json().get("reviews")
        self.summary = list(filter(lambda x: x.get("review").get("type") == 4, reviews))
        self.reviews = list(filter(lambda x: x.get("review").get("type") == 1, reviews))
        self.reviews = list(map(lambda x: x.get("review"), self.reviews))
        self.reviews = list(
            map(lambda x: {**x, "markText": x.pop("content")}, self.reviews)
        )

    def set_bookmark_list(self, session: requests.Session):
        params = dict(book_id=self.book_id)
        r = session.get(WEREAD_BOOKMARKLIST_URL, params=params)

        if r.ok:
            updated = r.json().get("updated")
            logger.info(f"Updated bookmark list: {updated}")

            updated = sorted(
                updated,
                key=lambda x: (
                    x.get("chapterUid", 1),
                    int(x.get("range").split("-")[0]),
                ),
            )
            self.bookmark_list = r.json()["updated"]
        else:
            self.bookmark_list = None

    def set_chapter_info(self, session: requests.Session):
        body = {"book_ids": [self.book_id], "synckeys": [0], "teenmode": 0}
        r = session.post(WEREAD_CHAPTER_INFO, json=body)
        if (
            r.ok
            and "data" in r.json()
            and len(r.json()["data"]) == 1
            and "updated" in r.json()["data"][0]
        ):
            update = r.json()["data"][0]["updated"]
            self.chapter_info = {item["chapterUid"]: item for item in update}
        else:
            self.chapter_info = None


def get_bookmark_list(session: requests.Session, book_id: str) -> Optional[List[Dict]]:
    """获取我的划线
    Returns:
        List[Dict]: 本书的划线列表
    """

    params = dict(book_id=book_id)
    r = session.get(WEREAD_BOOKMARKLIST_URL, params=params)

    if r.ok:
        updated = r.json().get("updated")
        logger.info(f"Updated bookmark list: {updated}")

        updated = sorted(
            updated,
            key=lambda x: (x.get("chapterUid", 1), int(x.get("range").split("-")[0])),
        )
        return r.json()["updated"]
    return None


def get_read_info(session: requests.Session, book_id: str) -> Optional[Dict]:
    params = dict(book_id=book_id, readingDetail=1, readingBookIndex=1, finishedDate=1)
    r = session.get(WEREAD_READ_INFO_URL, params=params)
    if r.ok:
        return r.json()
    return None


def get_bookinfo(session: requests.Session, book_id: str) -> Tuple[str, float]:
    """获取书的详情"""
    params = dict(book_id=book_id)
    r = session.get(WEREAD_BOOK_INFO, params=params)
    isbn = ""
    newRating = 0.0
    if r.ok:
        data = r.json()
        isbn = data["isbn"]
        newRating = data["newRating"] / 1000
    return (isbn, newRating)


def get_notebooklist(session: requests.Session) -> Optional[List[Dict]]:
    """获取笔记本列表"""
    r = session.get(WEREAD_NOTEBOOKS_URL)
    if r.ok:
        data = r.json()
        books = data.get("books")
        print("len(books)", len(books))
        print("books", books[:5])
        books.sort(key=lambda x: x["sort"])
        return books
    else:
        print(r.text)
    return None


def get_chapter_info(
    session: requests.Session, book_id: str
) -> Optional[Dict[int, Dict]]:
    """获取章节信息"""
    body = {"book_ids": [book_id], "synckeys": [0], "teenmode": 0}
    r = session.post(WEREAD_CHAPTER_INFO, json=body)
    if (
        r.ok
        and "data" in r.json()
        and len(r.json()["data"]) == 1
        and "updated" in r.json()["data"][0]
    ):
        update = r.json()["data"][0]["updated"]
        return {item["chapterUid"]: item for item in update}
    return None


def get_review_list(
    session: requests.Session, book_id: str
) -> Tuple[List[Dict], List[Dict]]:
    """获取笔记"""
    params = dict(book_id=book_id, listType=11, mine=1, syncKey=0)
    r = session.get(WEREAD_REVIEW_LIST_URL, params=params)
    reviews = r.json().get("reviews")
    summary = list(filter(lambda x: x.get("review").get("type") == 4, reviews))
    reviews = list(filter(lambda x: x.get("review").get("type") == 1, reviews))
    reviews = list(map(lambda x: x.get("review"), reviews))
    reviews = list(map(lambda x: {**x, "markText": x.pop("content")}, reviews))
    return (summary, reviews)


def get_table_of_contents() -> Dict:
    """获取目录"""
    return {"type": "table_of_contents", "table_of_contents": {"color": "default"}}


def get_heading(level: int, content: str) -> Dict:
    if level == 1:
        heading = "heading_1"
    elif level == 2:
        heading = "heading_2"
    else:
        heading = "heading_3"
    return {
        "type": heading,
        heading: {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content,
                    },
                }
            ],
            "color": "default",
            "is_toggleable": False,
        },
    }


def get_quote(content: str) -> Dict:
    return {
        "type": "quote",
        "quote": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": content},
                }
            ],
            "color": "default",
        },
    }


def get_children(
    chapter: Optional[Dict[int, Dict]], summary: List[Dict], bookmark_list: List[Dict]
) -> Tuple[List[Dict], Dict[int, Dict]]:
    children = []
    grandchild = {}

    if chapter is not None:
        # 添加目录
        children.append(get_table_of_contents())
        d = {}
        for data in bookmark_list:
            chapterUid = data.get("chapterUid", 1)
            if chapterUid not in d:
                d[chapterUid] = []
            d[chapterUid].append(data)

        for key, value in d.items():
            if key in chapter:
                # 添加章节
                children.append(
                    get_heading(
                        chapter.get(key).get("level"), chapter.get(key).get("title")
                    )
                )

            for i in value:
                callout = get_callout_block(
                    i.get("markText"),
                    data.get("style"),
                    i.get("colorStyle"),
                    i.get("reviewId"),
                )
                children.append(callout)

                if i.get("abstract") is not None and i.get("abstract") != "":
                    quote = get_quote(i.get("abstract"))
                    grandchild[len(children) - 1] = quote

    else:
        # 如果没有章节信息 - grandchild 为空
        for data in bookmark_list:
            children.append(
                get_callout_block(
                    data.get("markText"),
                    data.get("style"),
                    data.get("colorStyle"),
                    data.get("reviewId"),
                )
            )

    if summary is not None and len(summary) > 0:
        children.append(get_heading(1, "点评"))
        for i in summary:
            children.append(
                get_callout_block(
                    i.get("review").get("content"),
                    i.get("style"),
                    i.get("colorStyle"),
                    i.get("review").get("reviewId"),
                )
            )
    logger.info(f"Children: {children}")
    logger.info(f"Grandchild: {grandchild}")
    return children, grandchild
