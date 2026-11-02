from .fetcher import url2md
from .md_handler import google_query_md_handler
from urllib.parse import quote_plus


async def search_google_paper(keywords: str, page=1, year=None, sort_bd=False, proxy=None) -> str:
    """谷歌学术搜索并返回处理后的结果"""
    # 实际搜索逻辑...
    url = "https://scholar.google.com/scholar?"
    misc = "&hl=en&as_sdt=0,5"
    year = f"as_ylo={year}&" if year else ""
    if sort_bd:
        sort = "&scisbd=1"
    else:
        sort = ""

    if not page == 1:
        page = "start=" + str(int((page - 1) * 10)) + "&"
    else:
        page = ""

    print(f"\nSearching on Google Scholar: {keywords}")
    keywords = "q=" + quote_plus(keywords.replace(' ', '+'))
    url = url + page + year + keywords + misc + sort
    print(f"URL={url}\n")
    search_result = await url2md(url=url, proxy=proxy, timeout=10000)
    return google_query_md_handler(search_result)


if __name__ == "__main__":
    keywords = "High Q Organic Laser"
    page = 1
    year = "2025"
    proxy = "http://10.6.22.1:1080"
    print(search_google_paper(keywords=keywords, page=page, year=year, sort_bd=False, proxy=proxy))