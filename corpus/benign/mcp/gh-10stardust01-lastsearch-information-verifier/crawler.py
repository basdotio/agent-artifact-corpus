#!/usr/bin/env python3
"""
Bengaluru Civic Sources Crawler

Crawls official Bengaluru civic websites and indexes documents into Elasticsearch.
Uses the .crawler.yml configuration for sources and extraction rules.
"""

import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
import yaml
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

OFFICIAL_SOURCE_NAMES = {'BMRCL', 'BBMP', 'BWSSB', 'BESCOM', 'BDA', 'PIB Karnataka'}
REQUEST_TIMEOUT = (10, 25)
MAX_REQUEST_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
UNINDEXABLE_BODY_MARKERS = (
    'may be for sale',
    'related searches:',
    'buy this domain',
)


class CivicCrawler:
    def __init__(self, config_path: str = ".crawler.yml"):
        self.config = self.load_config(config_path)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (compatible; Bengaluru-Misinfo-Layer-Crawler/1.0; '
                '+https://example.invalid/civic-fact-checking)'
            ),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-IN,en;q=0.9',
        })
        self.session.verify = True
        self._load_dotenv()

    def _load_dotenv(self) -> None:
        env_path = Path(__file__).resolve().parent / '.env'
        if load_dotenv is not None and env_path.exists():
            load_dotenv(env_path)

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load crawler configuration from YAML file."""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def should_crawl_url(self, url: str) -> bool:
        """Check if URL should be crawled based on crawl rules."""
        decision = False
        for rule in self.config['crawl_rules']:
            if self._matches_rule(url, rule):
                decision = rule['policy'] == 'allow'
        return decision

    def get_extraction_rules(self, url: str) -> Optional[Dict[str, Any]]:
        """Get extraction rules for a URL."""
        for rule in self.config['extraction_rules']:
            for url_filter in rule['url_filters']:
                if self._matches_rule(url, url_filter):
                    return rule
        return None

    def _matches_rule(self, url: str, rule: Dict[str, Any]) -> bool:
        pattern = rule['pattern']
        rule_type = rule['type']
        if rule_type == 'begins':
            return url.startswith(pattern)
        if rule_type == 'ends':
            return url.endswith(pattern)
        if rule_type == 'regex':
            return re.match(pattern, url) is not None
        return False

    def extract_field(self, soup: BeautifulSoup, field_config: Dict[str, Any]) -> str:
        """Extract a field from HTML using selector or fixed value."""
        if 'value' in field_config:
            return field_config['value']

        selector = field_config['selector']
        elements = soup.select(selector)

        if not elements:
            return ""

        values = []
        for element in elements:
            attribute = field_config.get('attribute')
            if attribute:
                value = element.get(attribute, '')
            elif element.name == 'meta':
                value = element.get('content', '') or element.get('value', '')
            elif element.name == 'time':
                value = element.get('datetime', '') or element.get_text(' ', strip=True)
            else:
                value = element.get_text(' ', strip=True)

            value = re.sub(r'\s+', ' ', str(value)).strip()
            if value:
                if field_config['field_name'] == 'body':
                    values.append(value)
                    continue
                return value

        if values:
            return max(values, key=len)

        return ""

    def normalize_date(self, raw_value: str) -> Optional[str]:
        """Normalize common civic-site date strings into ISO-8601 dates."""
        value = re.sub(r'\s+', ' ', raw_value.replace('\xa0', ' ')).strip()
        if not value:
            return None

        value = re.sub(
            r'^(published|posted|release date|date|last updated|updated)'
            r'\s*(on|at)?\s*[:\-]?\s*',
            '',
            value,
            flags=re.IGNORECASE,
        ).strip()

        iso_match = re.search(
            r'\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?'
            r'(?:Z|[+-]\d{2}:?\d{2})?)?',
            value,
        )
        if iso_match:
            candidate = iso_match.group(0).replace('Z', '+00:00')
            try:
                parsed = datetime.fromisoformat(candidate)
                return parsed.date().isoformat()
            except ValueError:
                return candidate[:10]

        try:
            parsed_email_date = parsedate_to_datetime(value)
            if parsed_email_date:
                return parsed_email_date.date().isoformat()
        except (TypeError, ValueError, IndexError, OverflowError):
            pass

        numeric_match = re.search(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b', value)
        if numeric_match:
            day, month, year = (int(part) for part in numeric_match.groups())
            if year < 100:
                year += 2000
            try:
                return datetime(year, month, day).date().isoformat()
            except ValueError:
                return None

        month_name_match = re.search(
            r'\b(?:\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4}|'
            r'[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})\b',
            value,
        )
        if month_name_match:
            candidate = month_name_match.group(0).replace(',', '')
            for fmt in ('%d %B %Y', '%d %b %Y', '%B %d %Y', '%b %d %Y'):
                try:
                    return datetime.strptime(candidate, fmt).date().isoformat()
                except ValueError:
                    continue

        return None

    def prepare_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Clean extracted fields before sending them to Elasticsearch."""
        cleaned: Dict[str, Any] = {}
        for key, value in document.items():
            if isinstance(value, str):
                value = re.sub(r'\s+', ' ', value).strip()
                if not value:
                    continue
            cleaned[key] = value

        raw_date = cleaned.get('published_date')
        if raw_date:
            normalized_date = self.normalize_date(str(raw_date))
            if normalized_date:
                cleaned['published_date'] = normalized_date
            else:
                logger.warning(
                    "Could not parse published_date %r for %s; using crawled_at fallback",
                    raw_date,
                    cleaned.get('source_url', 'unknown URL'),
                )
                cleaned.pop('published_date', None)
        else:
            cleaned.pop('published_date', None)

        return cleaned

    def is_indexable_document(self, document: Dict[str, Any]) -> bool:
        body = str(document.get('body', '')).lower()
        if not document.get('title') and not body:
            return False
        return not any(marker in body for marker in UNINDEXABLE_BODY_MARKERS)

    def fetch_url(self, url: str) -> requests.Response:
        """Fetch a URL, retrying transient failures and falling back for bad civic TLS."""
        try:
            return self._fetch_url_with_retries(url, verify=True)
        except requests.exceptions.SSLError as ssl_exc:
            logger.warning(
                "SSL verification failed for %s, retrying without certificate verification: %s",
                url,
                ssl_exc,
            )
            requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
            return self._fetch_url_with_retries(url, verify=False)

    def _fetch_url_with_retries(self, url: str, *, verify: bool) -> requests.Response:
        for attempt in range(1, MAX_REQUEST_ATTEMPTS + 1):
            try:
                response = self.session.get(url, timeout=REQUEST_TIMEOUT, verify=verify)
                if (
                    response.status_code in RETRYABLE_STATUS_CODES
                    and attempt < MAX_REQUEST_ATTEMPTS
                ):
                    logger.warning(
                        "Retrying %s after HTTP %s (%s/%s)",
                        url,
                        response.status_code,
                        attempt,
                        MAX_REQUEST_ATTEMPTS,
                    )
                    time.sleep(attempt)
                    continue

                response.raise_for_status()
                if urlparse(response.url).path.lower().endswith(('/404.php', '/404.html')):
                    raise requests.exceptions.HTTPError(
                        f"Resolved to soft 404 page: {response.url}",
                        response=response,
                    )
                return response
            except requests.exceptions.SSLError:
                raise
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
                if attempt == MAX_REQUEST_ATTEMPTS:
                    raise
                logger.warning(
                    "Retrying %s after connection error (%s/%s): %s",
                    url,
                    attempt,
                    MAX_REQUEST_ATTEMPTS,
                    error,
                )
                time.sleep(attempt)

        raise RuntimeError(f"Failed to fetch {url}")

    def crawl_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Crawl a single URL and extract document data."""
        try:
            logger.info(f"Crawling: {url}")
            response = self.fetch_url(url)

            soup = BeautifulSoup(response.content, 'html.parser')
            rules = self.get_extraction_rules(url)

            if not rules:
                logger.warning(f"No extraction rules for {url}")
                return None

            document = {
                'source_url': url,
                'crawled_at': datetime.now(timezone.utc).isoformat(),
                'content_type': 'text/html'
            }

            # Extract fields according to rules
            for field in rules['fields']:
                field_name = field['field_name']
                document[field_name] = self.extract_field(soup, field)

            # Set source_tier based on source_name
            source_name = document.get('source_name', '')
            if source_name in OFFICIAL_SOURCE_NAMES:
                document['source_tier'] = 'official'
            else:
                document['source_tier'] = 'news'

            document = self.prepare_document(document)
            if not self.is_indexable_document(document):
                logger.warning("Skipping unindexable document from %s", url)
                return None
            logger.info(f"Extracted document: {document.get('title', 'No title')}")
            return document

        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return None

    def crawl_source_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Crawl multiple URLs and return extracted documents."""
        documents = []
        for url in urls:
            if self.should_crawl_url(url):
                doc = self.crawl_url(url)
                if doc:
                    documents.append(doc)
            else:
                logger.info(f"Skipping disallowed URL: {url}")
        return documents

    def index_to_elasticsearch(self, documents: List[Dict[str, Any]]) -> None:
        """Index documents into Elasticsearch."""
        try:
            from elasticsearch import Elasticsearch
            import os

            # Load environment variables
            es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
            es_api_key = os.getenv('ELASTICSEARCH_API_KEY')
            index_name = os.getenv('ELASTICSEARCH_INDEX', 'bengaluru-sources')

            if not es_api_key:
                raise ValueError("ELASTICSEARCH_API_KEY environment variable required")

            es = Elasticsearch(es_url, api_key=es_api_key)

            for doc in documents:
                doc = self.prepare_document(dict(doc))
                if not self.is_indexable_document(doc):
                    logger.warning("Skipping unindexable document from %s", doc.get('source_url'))
                    continue
                try:
                    es.index(index=index_name, document=doc)
                    logger.info(f"Indexed: {doc.get('title', 'No title')}")
                except Exception as e:
                    logger.error(f"Failed to index document: {e}")

        except ImportError:
            logger.error("Elasticsearch dependencies not installed. Run: pip install -e .[live]")
        except Exception as e:
            logger.error(f"Elasticsearch indexing error: {e}")

def main():
    """Main crawler entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Crawl Bengaluru civic sources")
    parser.add_argument('--urls', nargs='+', help='Specific URLs to crawl')
    parser.add_argument('--config', default='.crawler.yml', help='Crawler config file')
    parser.add_argument('--dry-run', action='store_true', help='Extract but do not index')

    args = parser.parse_args()

    crawler = CivicCrawler(args.config)

    if args.urls:
        urls = args.urls
    else:
        # Default URLs to crawl (recent press releases, notices)
        urls = [
            "https://www.bmrcl.co.in/press-releases/",
            "https://site.bbmp.gov.in/circulars.html",
            "https://bwssb.gov.in/home",
            "https://bescom.karnataka.gov.in/new-page/Planned%20Outages%20-%20BESCOM%20Works/en",
        ]

    logger.info(f"Starting crawl of {len(urls)} URLs")
    documents = crawler.crawl_source_urls(urls)

    if args.dry_run:
        print(json.dumps(documents, indent=2, ensure_ascii=False))
    else:
        crawler.index_to_elasticsearch(documents)

    logger.info(f"Crawled {len(documents)} documents successfully")

if __name__ == "__main__":
    main()
