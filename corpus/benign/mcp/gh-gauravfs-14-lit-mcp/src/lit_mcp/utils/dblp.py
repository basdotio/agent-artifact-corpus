import requests
from typing import List, Dict, Any

def find_dblp_publications(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Search DBLP database for computer science papers.
    
    Args:
        query: The search query string
        max_results: Maximum number of results to return
        
    Returns:
        List of dictionaries with publication data including:
        - authors: List of author names
        - title: Publication title
        - venue: Publication venue
        - volume: Volume number
        - number: Publication number
        - pages: Page numbers
        - publisher: Publisher name
        - year: Publication year
        - type: Publication type
        - access: Access type
        - key: DBLP key
        - doi: DOI identifier
        - ee: Electronic edition link
        - url: DBLP page URL
    """
    try:
        # DBLP API endpoint
        url = f"https://dblp.org/search/publ/api"
        params = {
            'q': query,
            'format': 'json',
            'h': max_results
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract publications from the response
        publications = []
        if 'result' in data and 'hits' in data['result'] and 'hit' in data['result']['hits']:
            hits = data['result']['hits']['hit']
            
            # Ensure hits is a list
            if not isinstance(hits, list):
                hits = [hits]
            
            for hit in hits:
                info = hit.get('info', {})
                
                # Extract authors
                authors = []
                if 'authors' in info and 'author' in info['authors']:
                    author_data = info['authors']['author']
                    if isinstance(author_data, list):
                        authors = author_data
                    else:
                        authors = [author_data]
                
                # Create publication dictionary
                publication = {
                    'title': info.get('title', ''),
                    'authors': authors,
                    'venue': info.get('venue', ''),
                    'volume': info.get('volume', ''),
                    'number': info.get('number', ''),
                    'pages': info.get('pages', ''),
                    'publisher': info.get('publisher', ''),
                    'year': info.get('year', ''),
                    'type': info.get('type', ''),
                    'access': info.get('access', ''),
                    'key': info.get('key', ''),
                    'doi': info.get('doi', ''),
                    'ee': info.get('ee', ''),
                    'url': info.get('url', '')
                }
                
                publications.append(publication)
        
        return publications
        
    except requests.RequestException as e:
        print(f"Error fetching DBLP data: {e}")
        return []
    except Exception as e:
        print(f"Error processing DBLP data: {e}")
        return []