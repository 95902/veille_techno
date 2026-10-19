import pytest

from veille_worker.urls import normalize_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://lab.example.com/news/model-x?utm_source=rss&utm_medium=feed#top",
            "https://lab.example.com/news/model-x",
        ),
        ("HTTPS://LAB.Example.COM/news/model-x?UTM_Campaign=x", "https://lab.example.com/news/model-x"),
        ("https://example.com:443/a", "https://example.com/a"),
        ("http://example.com:8080/a", "http://example.com:8080/a"),
        ("https://example.com", "https://example.com/"),
        ("https://hn.example/item?id=42&utm_source=x&p=2", "https://hn.example/item?id=42&p=2"),
        ("  https://example.com/a#section  ", "https://example.com/a"),
    ],
)
def test_normalize_url(url, expected):
    assert normalize_url(url) == expected


def test_tracking_variants_share_one_key():
    variants = [
        "https://lab.example.com/news/model-x?utm_source=rss&utm_medium=feed#top",
        "https://LAB.example.com/news/model-x?utm_campaign=dup",
        "https://lab.example.com/news/model-x",
    ]

    assert len({normalize_url(v) for v in variants}) == 1


def test_path_case_is_preserved():
    assert normalize_url("https://example.com/Path/A") == "https://example.com/Path/A"
