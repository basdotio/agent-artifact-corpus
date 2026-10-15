import logging
import re

import requests
from bs4 import BeautifulSoup

from config import (
    DEFAULT_SITEMAP_URL,
    WEBSITE_URL_BLACKLIST,
    WEBSITE_URL_BLACKLIST_REGEX,
    WEBSITE_URLS,
)

logger = logging.getLogger(__name__)


def extract_urls_from_sitemap(url_sitemap: str):
    """
    Extract URLs and metadata from a sitemap XML file.
    PS: Designed for RoboCup Small Size League sitemap

    Args:
        url_sitemap (str): URL of the sitemap to parse

    Returns:
        list: List of dictionaries containing URL information
        Each dictionary contains:
            - url: The page URL
            - lastmod: Last modification date
            - changefreq: How often the page changes
            - priority: Page priority (0.0 to 1.0)
    """

    try:
        # Fetch sitemap
        response = requests.get(url_sitemap)
        response.raise_for_status()  # Raise exception for bad status codes

        # Parse XML with lxml parser
        soup = BeautifulSoup(response.content, "lxml-xml")

        # Initialize results list
        urls_info = []

        # Check if this is a sitemap index
        if soup.find("sitemapindex"):
            logger.info("Found sitemap index, processing sub-sitemaps...")
            # Get all sitemap URLs
            sitemap_urls = [
                sitemap.find("loc").text for sitemap in soup.find_all("sitemap")
            ]

            # Process each sub-sitemap
            for sitemap_url in sitemap_urls:
                try:
                    sub_response = requests.get(sitemap_url)
                    sub_response.raise_for_status()
                    sub_soup = BeautifulSoup(sub_response.content, "lxml-xml")

                    # Process URLs in sub-sitemap
                    for url_elem in sub_soup.find_all("url"):
                        url_info = extract_url_info(url_elem)
                        if url_info:
                            urls_info.append(url_info)

                except Exception as e:
                    logger.error(
                        f"Error processing sub-sitemap {sitemap_url}: {str(e)}"
                    )
                    continue

        else:
            # Process URLs in single sitemap
            logger.info("Processing single sitemap...")
            for url_elem in soup.find_all("url"):
                url_info = extract_url_info(url_elem)
                if url_info:
                    urls_info.append(url_info)

        logger.info(f"Successfully extracted {len(urls_info)} URLs from sitemap")
        return urls_info

    except requests.RequestException as e:
        logger.error(f"Error fetching sitemap: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error processing sitemap: {str(e)}")
        return []


def extract_url_info(url_elem):
    """
    Extract information from a URL element in the sitemap.

    Args:
        url_elem: BeautifulSoup element containing URL information

    Returns:
        dict: Dictionary containing URL information or None if invalid
    """
    try:
        # Extract required URL
        url = url_elem.find("loc")
        if not url:
            return None

        # Extract optional fields with defaults
        lastmod = url_elem.find("lastmod")
        changefreq = url_elem.find("changefreq")
        priority = url_elem.find("priority")

        # Build info dictionary
        url_info = {
            "url": url.text.strip(),
            "lastmod": lastmod.text.strip() if lastmod else None,
            "changefreq": changefreq.text.strip() if changefreq else None,
            "priority": float(priority.text.strip()) if priority else 0.5,
        }

        return url_info

    except Exception as e:
        logger.error(f"Error extracting URL info: {str(e)}")
        return None


def process_urls(urls_info):
    extracted_urls = [info["url"] for info in urls_info]

    all_urls = WEBSITE_URLS + extracted_urls

    website_urls = list(set(all_urls))

    filtered_urls = [
        url
        for url in website_urls
        if not any(keyword in url for keyword in WEBSITE_URL_BLACKLIST)
        and not any(re.match(regex, url) for regex in WEBSITE_URL_BLACKLIST_REGEX)
    ]

    return filtered_urls


if __name__ == "__main__":
    urls_info = extract_urls_from_sitemap(DEFAULT_SITEMAP_URL)

    filtered_urls = process_urls(urls_info)

    print(filtered_urls)
