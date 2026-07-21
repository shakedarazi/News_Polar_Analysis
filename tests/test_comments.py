"""Tests for comment ID helpers and parsers."""

import json
from datetime import datetime

from src.crawling.comments.channel14 import channel14_post_id
from src.crawling.comments.haaretz import (
    _parse_published_at,
    haaretz_article_id,
)
from src.crawling.comments.mako import extract_vcm_id
from src.crawling.comments.ynet import ynet_article_id
from src.db.comments import make_comment_id


def test_ynet_article_id():
    url = "https://www.ynet.co.il/news/article/hj2t1ygqme?utm=1"
    assert ynet_article_id(url) == "hj2t1ygqme"


def test_haaretz_article_id():
    url = (
        "https://www.haaretz.co.il/news/politics/2026-07-01/"
        "ty-article/0000019f-1c24-d9e1-a7df-3fbde9f70000"
    )
    assert haaretz_article_id(url) == "0000019f-1c24-d9e1-a7df-3fbde9f70000"


def test_haaretz_parse_published_at():
    url = (
        "https://www.haaretz.co.il/news/politics/2026-07-01/"
        "ty-article/0000019f-1c24-d9e1-a7df-3fbde9f70000"
    )
    assert _parse_published_at(url, "16:05") == datetime(2026, 7, 1, 16, 5)


def test_channel14_post_id():
    assert channel14_post_id("https://www.c14.co.il/article/1605445/") == 1605445


def test_make_comment_id():
    assert make_comment_id("abc", "99") == "abc:99"


def test_extract_vcm_id_from_next_data():
    payload = {
        "props": {
            "pageProps": {
                "pageData": {"vcmId": "4ef1a905f7a1f910VgnVCM100000700a10acRCRD"},
            }
        }
    }
    html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script>'
    assert extract_vcm_id(html) == "4ef1a905f7a1f910VgnVCM100000700a10acRCRD"
