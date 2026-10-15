import subprocess
import json
from typing import Optional, Dict, Any, List

def arjun_wrapper(
    url: str,
    method: str = "GET",
    wordlist: Optional[str] = None,
    headers: Optional[List[str]] = None,
    data: Optional[str] = None,
    delay: int = 0,
    timeout: int = 10,
    threads: int = 25,
    stable: bool = False,
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    Wrapper for Arjun HTTP parameter discovery tool.
    
    Args:
        url (str): Target URL to scan for parameters
        method (str): HTTP method to use (GET, POST, PUT, etc.)
        wordlist (str): Custom wordlist file path
        headers (List[str]): Custom headers to include
        data (str): POST data for POST requests
        delay (int): Delay between requests in seconds
        timeout (int): Request timeout in seconds
        threads (int): Number of threads to use
        stable (bool): Use stable mode for fewer false positives
        output_format (str): Output format (json, txt)
    
    Returns:
        Dict[str, Any]: Results containing discovered parameters
    """
    try:
        # Build the command
        cmd = ["arjun", "-u", url]
        
        # Add method
        cmd.extend(["-m", method.upper()])
        
        # Add options
        if wordlist:
            cmd.extend(["-w", wordlist])
            
        if headers:
            for header in headers:
                cmd.extend(["-H", header])
                
        if data:
            cmd.extend(["-d", data])
            
        if delay > 0:
            cmd.extend(["--delay", str(delay)])
            
        cmd.extend(["-t", str(timeout)])
        cmd.extend(["--threads", str(threads)])
        
        if stable:
            cmd.append("--stable")
            
        if output_format == "json":
            cmd.append("-oJ")
            cmd.append("-")  # Output to stdout
        else:
            cmd.append("-oT")
            cmd.append("-")  # Output to stdout
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Parse the output
        parameters = []
        
        if output_format == "json":
            try:
                # Arjun outputs each URL's results as separate JSON objects
                for line in result.stdout.splitlines():
                    if line.strip():
                        data = json.loads(line)
                        if "parameters" in data:
                            parameters.extend(data["parameters"])
                        elif isinstance(data, list):
                            parameters.extend(data)
                        elif isinstance(data, str):
                            parameters.append(data)
            except json.JSONDecodeError:
                # Fallback to parsing as text
                for line in result.stdout.splitlines():
                    if line.strip() and not line.startswith("["):
                        parameters.append(line.strip())
        else:
            # Parse plain text output
            for line in result.stdout.splitlines():
                if line.strip() and not line.startswith("["):
                    parameters.append(line.strip())
        
        return {
            "success": True,
            "target": url,
            "method": method.upper(),
            "parameters": parameters,
            "count": len(parameters)
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

def arjun_bulk_scan(
    urls: List[str],
    method: str = "GET",
    wordlist: Optional[str] = None,
    threads: int = 25,
    stable: bool = False
) -> Dict[str, Any]:
    """
    Enhanced Arjun wrapper for scanning multiple URLs.
    
    Args:
        urls (List[str]): List of target URLs to scan
        method (str): HTTP method to use
        wordlist (str): Custom wordlist file path
        threads (int): Number of threads to use
        stable (bool): Use stable mode
        
    Returns:
        Dict[str, Any]: Aggregated results from all scanned URLs
    """
    all_results = {}
    successful_scans = 0
    failed_scans = 0
    
    for url in urls:
        result = arjun_wrapper(
            url=url,
            method=method,
            wordlist=wordlist,
            threads=threads,
            stable=stable
        )
        
        if result["success"]:
            all_results[url] = {
                "parameters": result["parameters"],
                "count": result["count"]
            }
            successful_scans += 1
        else:
            all_results[url] = {
                "error": result["error"],
                "parameters": [],
                "count": 0
            }
            failed_scans += 1
    
    return {
        "success": True,
        "method": method.upper(),
        "total_urls": len(urls),
        "successful_scans": successful_scans,
        "failed_scans": failed_scans,
        "results": all_results
    }

def arjun_with_custom_payloads(
    url: str,
    method: str = "GET",
    custom_params: Optional[List[str]] = None,
    wordlist: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Arjun wrapper with custom parameter testing capabilities.
    
    Args:
        url (str): Target URL to scan
        method (str): HTTP method to use
        custom_params (List[str]): Custom parameters to test
        wordlist (str): Custom wordlist file path
        **kwargs: Additional arguments passed to arjun_wrapper
        
    Returns:
        Dict[str, Any]: Results with custom parameter testing
    """
    # Get base results
    results = arjun_wrapper(url, method, wordlist, **kwargs)
    
    if not results["success"]:
        return results
    
    # Test custom parameters if provided
    if custom_params:
        custom_found = []
        for param in custom_params:
            # Simple test by checking if parameter is in discovered list
            if param in results["parameters"]:
                custom_found.append(param)
        
        results["custom_parameters_tested"] = custom_params
        results["custom_parameters_found"] = custom_found
        results["custom_match_count"] = len(custom_found)
    
    return results
