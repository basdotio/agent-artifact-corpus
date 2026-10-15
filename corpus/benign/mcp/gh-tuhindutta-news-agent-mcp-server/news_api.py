import requests
from endpoint import EndPoint
from article import Article



def _fetch_article_from_latest_article_dict(article_dict:dict):
    extract = {i:article_dict.get(i) for i in list(Article.model_json_schema()['properties'].keys())}
    obj = Article(**extract)
    return obj

def _fetch_articles_from_latest_news(article_dict_list:list[dict]):
    objs = [_fetch_article_from_latest_article_dict(i) for i in article_dict_list]
    return objs




class NewsAPI:

    def __init__(self, endpoint:EndPoint):
        self.__endpoint = endpoint

    @property
    def endpoint(self):
        return self.__endpoint
    
    def get_latest_news(self, query:str):
        response = requests.get(self.endpoint.latest_news(query))
        data = response.json()
        return _fetch_articles_from_latest_news(data['results'])
    
    def news_sources_details(self):
        response = requests.get(self.endpoint.news_sources_details())
        data = response.json()
        return data
    
