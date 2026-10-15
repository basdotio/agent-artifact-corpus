import subprocess
import json
from typing import Optional, Dict, Any, List

def gospider_wrapper(
    target: str, 
    depth: int = 3, 
    concurrent: int = 10,
    timeout: int = 10,
    user_agent: Optional[str] = None,
    headers: Optional[List[str]] = None,
    include_subs: bool = False,
    include_other_source: bool = False,
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    Wrapper for Gospider web crawling tool.
    
    Args:
        target (str): Target URL or domain to crawl
        depth (int): Maximum crawling depth (default: 3)
        concurrent (int): Number of concurrent requests (default: 10)
        timeout (int): Request timeout in seconds (default: 10)
        user_agent (str): Custom User-Agent string
        headers (List[str]): Custom headers to include
        include_subs (bool): Include subdomains in crawling
        include_other_source (bool): Include other sources like robots.txt, sitemap.xml
        output_format (str): Output format (json, txt)
    
    Returns:
        Dict[str, Any]: Results containing discovered URLs and related information
    """
    try:
        # Build the command
        cmd = ["gospider", "-s", target]
        
        # Add options
        cmd.extend(["-d", str(depth)])
        cmd.extend(["-c", str(concurrent)])
        cmd.extend(["-t", str(timeout)])
        
        if user_agent:
            cmd.extend(["-u", user_agent])
            
        if headers:
            for header in headers:
                cmd.extend(["-H", header])
                
        if include_subs:
            cmd.append("--subs")
            
        if include_other_source:
            cmd.append("--other-source")
            
        if output_format == "json":
            cmd.append("--json")
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output
        urls = []
        forms = []
        secrets = []
        
        if output_format == "json":
            for line in result.stdout.splitlines():
                if line.strip():
                    try:
                        data = json.loads(line)
                        
                        if data.get("type") == "url":
                            urls.append({
                                "url": data.get("output"),
                                "source": data.get("source"),
                                "tag": data.get("tag"),
                                "status": data.get("status_code")
                            })
                        elif data.get("type") == "form":
                            forms.append({
                                "url": data.get("output"),
                                "source": data.get("source"),
                                "tag": data.get("tag")
                            })
                        elif data.get("type") == "secret":
                            secrets.append({
                                "secret": data.get("output"),
                                "source": data.get("source"),
                                "tag": data.get("tag")
                            })
                            
                    except json.JSONDecodeError:
                        continue
        else:
            # Parse plain text output
            for line in result.stdout.splitlines():
                if line.strip() and line.startswith("http"):
                    urls.append({
                        "url": line.strip(),
                        "source": "crawl",
                        "tag": "url",
                        "status": None
                    })
        
        return {
            "success": True,
            "target": target,
            "urls": urls,
            "forms": forms,
            "secrets": secrets,
            "stats": {
                "total_urls": len(urls),
                "total_forms": len(forms),
                "total_secrets": len(secrets)
            }
        }
        
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": str(e),
            "stderr": e.stderr if e.stderr else "Command execution failed"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def gospider_crawl_with_filter(
    target: str,
    extensions: Optional[List[str]] = None,
    exclude_extensions: Optional[List[str]] = None,
    filter_length: Optional[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Enhanced Gospider wrapper with filtering capabilities.
    
    Args:
        target (str): Target URL or domain to crawl
        extensions (List[str]): Only crawl URLs with these extensions
        exclude_extensions (List[str]): Exclude URLs with these extensions
        filter_length (int): Filter URLs by response length
        **kwargs: Additional arguments passed to gospider_wrapper
        
    Returns:
        Dict[str, Any]: Filtered crawling results
    """
    # Get base results
    results = gospider_wrapper(target, **kwargs)
    
    if not results["success"]:
        return results
    
    # Apply filters
    filtered_urls = results["urls"]
    
    if extensions:
        filtered_urls = [
            url for url in filtered_urls 
            if any(url["url"].endswith(f".{ext}") for ext in extensions)
        ]
    
    if exclude_extensions:
        filtered_urls = [
            url for url in filtered_urls 
            if not any(url["url"].endswith(f".{ext}") for ext in exclude_extensions)
        ]
    
    # Update results with filtered data
    results["urls"] = filtered_urls
    results["stats"]["total_urls"] = len(filtered_urls)
    results["filtered"] = True
    
    return results
