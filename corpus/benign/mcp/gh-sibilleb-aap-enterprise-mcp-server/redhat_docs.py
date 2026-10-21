#!/usr/bin/env python3
"""
Red Hat Documentation MCP Server - Streamlined Version

A streamlined Model Context Protocol server focused on two core functions:
1. Efficient web search-based discovery of Red Hat documentation
2. Reliable content fetching handling Red Hat's rendering issues

Key Features:
- Web search-based discovery using official Red Hat domains
- Smart content fetching with PDF-first strategy for rendering issues
- Domain validation for security
- Minimal tool set to reduce API calls
"""

import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx
import urllib3
from mcp.server.fastmcp import FastMCP

# Disable SSL warnings for lab environments
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize FastMCP
mcp = FastMCP("redhat-docs-streamlined")

# Base URLs for Red Hat documentation
REDHAT_DOCS_BASE = "https://docs.redhat.com"
REDHAT_ACCESS_BASE = "https://access.redhat.com"

# Official Red Hat domains for validation (from README)
OFFICIAL_REDHAT_DOMAINS = {
    # Core Red Hat domains
    "redhat.com", "docs.redhat.com", "access.redhat.com",
    "console.redhat.com", "cloud.redhat.com", "marketplace.redhat.com",
    "customer-portal.redhat.com", "connect.redhat.com", "catalog.redhat.com",
    "subscriptions.redhat.com",
    # Container registries and CDN
    "registry.redhat.com", "registry.access.redhat.com", "registry.connect.redhat.com",
    "registry.redhat.io", "quay.io", "cdn.quay.io", "cdn.redhat.com",
    "cdn-ubi.redhat.com", "download.redhat.com",
    # Product-specific domains
    "openshift.com", "docs.openshift.com", "console.openshift.com",
    "try.openshift.com", "learn.openshift.com",
    "ansible.com", "docs.ansible.com", "galaxy.ansible.com",
    "automation-hub.redhat.com",
    # Community and open source
    "opensource.com", "redhat.io", "developers.redhat.com",
    "research.redhat.com", "enable.redhat.com", "blog.redhat.com",
    # Enterprise services and support
    "npm.registry.redhat.com", "insights.redhat.com",
    "hybrid-cloud-console.redhat.com", "support.redhat.com",
    "labs.redhat.com", "training.redhat.com", "learn.redhat.com",
    # Events and community
    "summit.redhat.com", "events.redhat.com", "community.redhat.com",
    "partnerships.redhat.com",
    # Security and compliance
    "security.redhat.com", "errata.redhat.com", "cve.redhat.com",
    # Business and enterprise
    "investors.redhat.com", "jobs.redhat.com", "careers.redhat.com",
}

# Domain patterns for subdomain matching
REDHAT_DOMAIN_PATTERNS = [
    r".*\.redhat\.com$",
    r".*\.openshift\.com$", 
    r".*\.ansible\.com$",
    r".*\.quay\.io$",
]

# HTTP client configuration
default_headers = {
    "User-Agent": "Red Hat Documentation MCP Server/1.0",
    "Accept": "application/json, text/html, application/pdf, */*",
}
timeout = httpx.Timeout(30.0)


def is_official_redhat_domain(url: str) -> bool:
    """
    Validate that a URL is from an official Red Hat domain.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is from official Red Hat domain, False otherwise
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix if present
        if domain.startswith("www."):
            domain = domain[4:]
            
        # Check exact domain matches
        if domain in OFFICIAL_REDHAT_DOMAINS:
            return True
            
        # Check subdomain patterns
        for pattern in REDHAT_DOMAIN_PATTERNS:
            if re.match(pattern, domain):
                return True
                
        return False
        
    except Exception:
        return False


async def make_request(url: str, method: str = "GET", **kwargs) -> httpx.Response | str:
    """Make HTTP request with proper error handling."""
    try:
        async with httpx.AsyncClient(timeout=timeout, verify=False) as client:
            response = await client.request(method, url, headers=default_headers, **kwargs)
            
        if response.status_code == 200:
            return response
        else:
            return f"HTTP Error {response.status_code}: {response.text[:200]}"
            
    except httpx.TimeoutException:
        return "Request timeout - Red Hat service may be slow"
    except httpx.RequestError as e:
        return f"Request error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


def extract_pdf_url(html_url: str) -> str:
    """Convert HTML documentation URL to corresponding PDF URL."""
    # Pattern: /html/guide_name/index -> /pdf/guide_name/index
    html_pattern = r"/html(?:-single)?/([^/]+)/?(?:index)?$"
    match = re.search(html_pattern, html_url)
    
    if match:
        guide_name = match.group(1)
        # Replace html with pdf and add index
        pdf_url = re.sub(html_pattern, f"/pdf/{guide_name}/index", html_url)
        return pdf_url
        
    return html_url


@mcp.tool()
async def search_redhat_content(
    query: str,
    content_types: list[str] = None,
    limit: int = 10
) -> dict[str, Any]:
    """
    Generate optimized Red Hat search queries for use with WebSearch MCP tool.
    
    Args:
        query: Search terms (e.g., "AAP 2.5 containerized install")
        content_types: List of content types to search ["docs", "access", "all"] (default: ["all"])
        limit: Maximum number of results per content type (default: 10)
        
    Returns:
        Optimized search queries and guidance for external WebSearch usage
    """
    if content_types is None:
        content_types = ["all"]
        
    search_queries = {
        "query": query,
        "documentation_queries": [],
        "support_queries": [],
        "instructions": "",
        "workflow": []
    }
    
    # Generate documentation search queries (docs.redhat.com)
    if "docs" in content_types or "all" in content_types:
        docs_queries = [
            f"{query} site:docs.redhat.com",
            f"{query} site:docs.redhat.com filetype:pdf",
            f"{query} installation guide site:docs.redhat.com",
            f"{query} documentation site:docs.redhat.com"
        ]
        
        for i, q in enumerate(docs_queries[:2]):  # Limit to top 2 queries
            search_queries["documentation_queries"].append({
                "query": q,
                "purpose": f"Find official Red Hat documentation for {query}",
                "expected_domains": ["docs.redhat.com"],
                "content_type": "documentation",
                "requires_auth": False,
                "priority": i + 1
            })
    
    # Generate support content queries (access.redhat.com)  
    if "access" in content_types or "all" in content_types:
        support_queries = [
            f"{query} site:access.redhat.com",
            f"{query} troubleshooting site:access.redhat.com",
            f"{query} solution site:access.redhat.com",
            f"{query} error site:access.redhat.com"
        ]
        
        for i, q in enumerate(support_queries[:2]):  # Limit to top 2 queries
            search_queries["support_queries"].append({
                "query": q,
                "purpose": f"Find Red Hat support content for {query}",
                "expected_domains": ["access.redhat.com"],
                "content_type": "support",
                "requires_auth": "varies",
                "priority": i + 1
            })
    
    # Generate usage instructions
    search_queries["instructions"] = """
To use these search queries:
1. Use the WebSearch MCP tool with each query
2. Validate all returned URLs are from official Red Hat domains
3. Use fetch_redhat_content() to access the documentation
4. For docs.redhat.com URLs, prefer PDF format for reliable content extraction
5. For access.redhat.com URLs, check if authentication is required
    """
    
    # Generate workflow steps
    total_queries = len(search_queries["documentation_queries"]) + len(search_queries["support_queries"])
    search_queries["workflow"] = [
        f"1. Execute {total_queries} web searches using the provided queries",
        "2. Filter results to Red Hat official domains only",
        "3. Categorize results by content type (docs vs support)",
        "4. Use fetch_redhat_content() for each relevant URL",
        "5. Handle authentication requirements for premium content"
    ]
    
    search_queries["total_queries"] = total_queries
    
    return search_queries


@mcp.tool()
async def fetch_redhat_content(url: str, format_preference: str = "auto") -> str:
    """
    Fetch Red Hat documentation content handling rendering issues.
    
    Args:
        url: Red Hat documentation URL (must be from official domains)
        format_preference: "pdf", "html", or "auto" (default: auto tries PDF first)
        
    Returns:
        Content from the documentation or error message
    """
    # Validate URL is from Red Hat domains
    if not is_official_redhat_domain(url):
        return f"Error: URL must be from official Red Hat domains. Provided: {url}"
    
    parsed_url = urlparse(url)
    content_info = {
        "url": url,
        "domain": parsed_url.netloc,
        "format_attempted": [],
        "content": "",
        "status": ""
    }
    
    # Try PDF first if auto or pdf preference (handles rendering issues)
    if format_preference in ["auto", "pdf"]:
        if "/html" in url:
            pdf_url = extract_pdf_url(url)
            if pdf_url != url:
                content_info["format_attempted"].append("pdf")
                response = await make_request(pdf_url)
                if not isinstance(response, str) and response.status_code == 200:
                    # Check if it's actually a PDF
                    content_type = response.headers.get("content-type", "")
                    if "pdf" in content_type.lower():
                        content_info["status"] = "success_pdf"
                        content_info["content"] = (
                            f"PDF Content successfully accessed from {pdf_url}\n\n"
                            f"Content-Type: {content_type}\n"
                            f"Size: {len(response.content):,} bytes\n\n"
                            f"Note: PDF content extraction would require additional processing.\n"
                            f"This confirms the PDF is accessible and can be processed by PDF libraries."
                        )
                        return f"SUCCESS: {content_info['content']}"
    
    # Fall back to HTML if PDF not available or html preference
    if format_preference in ["auto", "html"]:
        content_info["format_attempted"].append("html")
        response = await make_request(url)
        if isinstance(response, str):  # Error occurred
            content_info["status"] = "error"
            content_info["content"] = f"Error accessing content: {response}"
            return f"ERROR: {content_info['content']}"
        
        # Check content type and handle appropriately
        content_type = response.headers.get("content-type", "")
        
        # For docs.redhat.com - often requires JavaScript rendering
        if "docs.redhat.com" in url:
            content_info["status"] = "html_js_required"
            content_info["content"] = (
                f"HTML content from {url}\n\n"
                f"Note: docs.redhat.com content often requires JavaScript rendering.\n"
                f"Content-Type: {content_type}\n"
                f"Status: {response.status_code}\n\n"
                f"Recommendation: Try the PDF version for reliable content extraction.\n"
                f"Alternative: Use browser automation for full content access."
            )
        
        # For access.redhat.com - may be directly accessible
        elif "access.redhat.com" in url:
            if response.status_code == 200:
                # Check if we got actual content or a login page
                text_content = response.text.lower()
                if "login" in text_content or "sign in" in text_content:
                    content_info["status"] = "auth_required"
                    content_info["content"] = (
                        f"Authentication required for {url}\n\n"
                        f"This content requires Red Hat Customer Portal login.\n"
                        f"Content-Type: {content_type}\n"
                        f"Status: {response.status_code}\n\n"
                        f"Note: Some access.redhat.com content is subscription-only."
                    )
                else:
                    content_info["status"] = "success_html"
                    # Return first 2000 characters of content
                    content_preview = response.text[:2000]
                    content_info["content"] = (
                        f"HTML content from {url}\n\n"
                        f"Content-Type: {content_type}\n"
                        f"Status: {response.status_code}\n"
                        f"Content length: {len(response.text):,} characters\n\n"
                        f"Content preview:\n{content_preview}"
                        f"{'...[truncated]' if len(response.text) > 2000 else ''}"
                    )
        
        return f"{'SUCCESS' if 'success' in content_info['status'] else 'INFO'}: {content_info['content']}"
    
    return "Error: Unable to access content in requested format"


if __name__ == "__main__":
    import asyncio
    mcp.run()