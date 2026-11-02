# Import packages
import re
import unicodedata
import trafilatura

# URL scrape and export method
def scrape_url(url: str, export: str) -> str:
    content = ''
    try:
        # Download the webpage
        print(f'Scraping URL: {url}')
        downloaded = trafilatura.fetch_url(url)

        # Extract the main content
        content = trafilatura.extract(downloaded)
        print('URL scraped successfully')

        # Replace 3 or more \n with 2 \n
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Normalize unicode
        content = unicodedata.normalize('NFKD', content)

        # Remove non-ASCII characters
        content = content.encode('ascii', 'ignore').decode('ascii')
        print('Word count:', len(content.split()))
    
    except Exception as e:
        print(f'\nError scraping URL: {e}')
        
    if content: 
        print(f'Saving content to file: {export}.txt')
        try:
            # Export text to file
            with open(f'documents/{export}.txt', 'w', encoding='ascii') as file:
                file.write(content)
            print('Content saved successfully')
        
        except Exception as e:
            print(f'Error saving content: {e}')
    
    return content