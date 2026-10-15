class EndPoint:

    def __init__(self, api_key:str):
        self.__api_key = api_key

    def latest_news(self, query:str):
        url = f"""https://newsdata.io/api/1/latest? 
        apikey={self.__api_key}
        &q=<query>
        &country=in,us,gb,ru,cn
        &language=en
        &category=breaking,science,politics,technology,world
        &timezone=asia/kolkata
        &removeduplicate=1
        &sort=relevancy
        &size=10""".replace(' ','').replace('\n','').replace('<query>', query)
        return url
    
    def news_sources_details(self):
        url = f"""https://newsdata.io/api/1/sources? 
        apikey={self.__api_key}
        &country=in,us,gb,cn,ru
        &language=en""".replace(' ','').replace('\n','').strip()
        return url