# pip install firecrawl-py
from firecrawl import Firecrawl


class WebsiteScraper:

    def __init__(self, api_key:str):
        self.__app = Firecrawl(api_key=api_key)

    def scrape_contents(self, url:str):
        scrape = self.__app.scrape(url)
        return scrape.model_dump()

    def data(self, url:str):
        data = self.scrape_contents(url)
        txt = ""
        for key, value in data.items():
            if key in ['markdown', 'metadata'] and value:
                tag = f"**{key}**:\n\n{value}".strip()
                txt += tag+f"\n\n{'-'*120}\n\n"
        txt = txt.strip()
        return txt