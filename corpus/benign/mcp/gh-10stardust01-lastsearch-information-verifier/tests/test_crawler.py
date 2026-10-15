import pytest

pytest.importorskip("bs4")
crawler_module = pytest.importorskip("crawler")

from bs4 import BeautifulSoup


def test_extract_field_reads_meta_content():
    crawler = crawler_module.CivicCrawler()
    soup = BeautifulSoup(
        "<html><head><meta name='date' content='2026-05-09'></head></html>",
        "html.parser",
    )

    assert (
        crawler.extract_field(
            soup,
            {"field_name": "published_date", "selector": "meta[name='date']"},
        )
        == "2026-05-09"
    )


def test_prepare_document_omits_blank_published_date():
    crawler = crawler_module.CivicCrawler()

    document = crawler.prepare_document(
        {
            "title": "BWSSB Notice",
            "published_date": "   ",
            "crawled_at": "2026-05-09T10:00:00+00:00",
            "source_url": "https://bwssb.gov.in/home",
        }
    )

    assert "published_date" not in document


def test_normalize_date_handles_indian_numeric_dates():
    crawler = crawler_module.CivicCrawler()

    assert crawler.normalize_date("Last Updated: 09-05-2026") == "2026-05-09"


def test_domain_parking_pages_are_not_indexable():
    crawler = crawler_module.CivicCrawler()

    assert not crawler.is_indexable_document(
        {
            "source_url": "https://www.bmrcl.co.in/press-releases/",
            "body": "The domain example.com may be for sale. Related Searches: deals",
        }
    )
