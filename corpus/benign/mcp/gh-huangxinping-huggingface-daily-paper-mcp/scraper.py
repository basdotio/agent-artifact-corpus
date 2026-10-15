import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import time
import re


class HuggingFacePapersScraper:
    
    def __init__(self):
        self.base_url = "https://huggingface.co/papers/date"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def get_papers_by_date(self, date: str, fetch_details: bool = True) -> List[Dict]:
        url = f"{self.base_url}/{date}"
        try:
            response = self.session.get(url)
            response.raise_for_status()
            papers = self._parse_papers(response.text)
            
            if fetch_details and papers:
                # 获取所有论文的详细信息，包括具体作者姓名
                for i, paper in enumerate(papers):
                    if paper.get('url'):
                        details = self._fetch_paper_details(paper['url'])
                        if details:
                            paper.update(details)
                        time.sleep(1)  # 避免请求过快
                        
            return papers
        except requests.RequestException as e:
            logging.error(f"Failed to fetch papers for {date}: {e}")
            return []
    
    def get_today_papers(self, fetch_details: bool = True) -> List[Dict]:
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_papers_by_date(today, fetch_details)
    
    def get_yesterday_papers(self, fetch_details: bool = True) -> List[Dict]:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        return self.get_papers_by_date(yesterday, fetch_details)
    
    def _parse_papers(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, 'html.parser')
        papers = []
        
        # 解析论文卡片
        paper_cards = soup.find_all('article', class_='relative')
        
        for card in paper_cards:
            paper_data = self._extract_paper_data(card)
            if paper_data:
                papers.append(paper_data)
        
        return papers
    
    def _extract_paper_data(self, card) -> Optional[Dict]:
        try:
            # 提取论文标题
            title_link = None
            title_candidates = [
                card.find('h3'),
                card.find('h2'), 
                card.find('h1')
            ]
            
            for candidate in title_candidates:
                if candidate:
                    link = candidate.find('a')
                    if link:
                        title_link = link
                        break
            
            if not title_link:
                # 备用方案：查找包含论文ID的链接
                links = card.find_all('a', href=True)
                for link in links:
                    if '/papers/' in link.get('href', ''):
                        text = link.get_text(strip=True)
                        if len(text) > 10:  # 标题通常比较长
                            title_link = link
                            break
            
            title = title_link.get_text(strip=True) if title_link else "Unknown Title"
            paper_url = f"https://huggingface.co{title_link.get('href')}" if title_link and title_link.get('href') else ""
            
            # 提取作者数量信息 - 从所有链接的文本中查找
            authors_count = ""
            all_links = card.find_all('a', href=True)
            
            # 方法1: 从链接文本中查找作者信息
            for link in all_links:
                link_text = link.get_text(strip=True)
                if 'authors' in link_text.lower() and '·' in link_text:
                    authors_count = link_text
                    break
            
            # 方法2: 如果上面没找到，用正则表达式在整个卡片文本中搜索
            if not authors_count:
                all_text = card.get_text()
                author_match = re.search(r'·(\d+)\s+authors?', all_text)
                if author_match:
                    count = author_match.group(1)
                    authors_count = f"·{count} authors"
            
            # 方法3: 最后的备选方案，搜索所有包含"authors"的文本
            if not authors_count:
                all_strings = list(card.stripped_strings)
                for text in all_strings:
                    if 'authors' in text.lower() and any(char.isdigit() for char in text):
                        authors_count = text
                        break
            
            # 提取摘要（列表页面通常没有）
            abstract = "Abstract not available in listing page"
            
            # 提取摘要（列表页面通常没有）
            abstract = "Abstract not available in listing page"
            
            # 提取PDF链接（需要从详情页获取）
            pdf_link = ""
            
            # 提取点赞数
            vote_count = 0
            # 尝试多种方式查找投票数
            vote_selectors = [
                'div[class*="leading-none"]',
                'div[class*="vote"]',
                'span[class*="vote"]',
                'button[class*="vote"]',
                'div[class*="like"]'
            ]
            
            for selector in vote_selectors:
                vote_elements = card.select(selector)
                for elem in vote_elements:
                    text = elem.get_text(strip=True)
                    if text.isdigit() and int(text) >= 0:
                        vote_count = int(text)
                        break
                if vote_count > 0:
                    break
            
            # 备用方案：在所有数字文本中查找可能的投票数
            if vote_count == 0:
                all_texts = list(card.stripped_strings)
                for text in all_texts:
                    if text.isdigit() and 0 <= int(text) <= 1000:  # 合理的投票数范围
                        vote_count = int(text)
                        break
            
            # 提取提交者信息
            submitted_by = ""
            
            # 方法1：查找包含"Submitted by"文本的元素
            submit_elements = card.find_all(string=lambda text: text and 'Submitted by' in text)
            for submit_text in submit_elements:
                parent = submit_text.parent
                if parent:
                    # 在父元素中查找用户链接或用户名
                    user_links = parent.find_all('a', href=True)
                    for link in user_links:
                        href = link.get('href', '')
                        if '/user/' in href or href.startswith('/') and not href.startswith('/papers/'):
                            submitted_by = link.get_text(strip=True)
                            break
                    
                    # 如果没找到链接，尝试从文本中提取
                    if not submitted_by:
                        parent_text = parent.get_text()
                        if 'Submitted by' in parent_text:
                            # 提取"Submitted by"后面的文本
                            parts = parent_text.split('Submitted by')
                            if len(parts) > 1:
                                after_text = parts[1].strip()
                                # 取第一个单词或短语作为用户名
                                username = after_text.split()[0] if after_text.split() else ""
                                if username and len(username) <= 30:
                                    submitted_by = username
                if submitted_by:
                    break
            
            # 方法2：查找用户相关的链接
            if not submitted_by:
                user_links = card.find_all('a', href=True)
                for link in user_links:
                    href = link.get('href', '')
                    if '/user/' in href:
                        submitted_by = link.get_text(strip=True)
                        break
            
            # 方法3：查找可能的用户名模式
            if not submitted_by:
                all_links = card.find_all('a')
                for link in all_links:
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    # 如果链接文本看起来像用户名且不是论文链接
                    if (text and 3 <= len(text) <= 25 and 
                        not any(skip in text.lower() for skip in ['view', 'paper', 'download', 'authors', 'pdf']) and
                        not href.startswith('/papers/')):
                        submitted_by = text
                        break
            
            return {
                'title': title,
                'authors': [authors_count] if authors_count else [],
                'abstract': abstract,
                'url': paper_url,
                'pdf_url': pdf_link,
                'votes': vote_count,
                'submitted_by': submitted_by,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error extracting paper data: {e}")
            return None
    
    def _fetch_paper_details(self, paper_url: str) -> Optional[Dict]:
        """获取论文详情页面的额外信息"""
        try:
            response = self.session.get(paper_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            details = {}
            
            # 尝试获取摘要
            abstract_selectors = [
                '.text-md',
                '.text-gray-700',
                '[class*="abstract"]',
                '.paper-abstract',
                'div p'
            ]
            
            for selector in abstract_selectors:
                abstract_elems = soup.select(selector)
                for elem in abstract_elems:
                    abstract_text = elem.get_text(strip=True)
                    # 查找看起来像摘要的长文本
                    if len(abstract_text) > 100 and len(abstract_text.split()) > 20:
                        # 过滤掉明显不是摘要的内容
                        if not any(skip_word in abstract_text.lower() for skip_word in 
                                 ['submitted by', 'view model', 'download', 'github', 'demo']):
                            details['abstract'] = abstract_text
                            break
                if 'abstract' in details:
                    break
            
            # 尝试获取PDF链接并从ArXiv获取作者信息
            arxiv_abs_url = None
            pdf_links = soup.find_all('a', href=True)
            for link in pdf_links:
                href = link.get('href', '')
                if 'arxiv.org/abs/' in href:
                    arxiv_abs_url = href
                    # 将 arxiv abs 链接转换为 PDF 链接
                    details['pdf_url'] = href.replace('/abs/', '/pdf/') + '.pdf'
                    break
                elif 'arxiv.org/pdf/' in href or '.pdf' in href:
                    details['pdf_url'] = href
                    break
            
            # 如果找到ArXiv链接，从ArXiv页面获取完整作者列表
            if arxiv_abs_url:
                authors = self._fetch_arxiv_authors(arxiv_abs_url)
                if authors:
                    details['authors'] = authors
            
            return details
            
        except Exception as e:
            logging.error(f"Error fetching paper details from {paper_url}: {e}")
            return None
    
    def _fetch_arxiv_authors(self, arxiv_url: str) -> Optional[List[str]]:
        """从ArXiv页面获取完整作者列表"""
        try:
            response = self.session.get(arxiv_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 使用正确的CSS选择器获取作者信息
            # 使用nth-of-type而不是nth-child，因为可能有其他非div元素
            authors_div = soup.select_one('#abs > div:nth-of-type(2)')
            
            if authors_div:
                authors_text = authors_div.get_text(strip=True)
                
                if authors_text and authors_text.lower().startswith('authors:'):
                    # 移除"Authors:"前缀
                    authors_text = authors_text[8:].strip()
                    # 按逗号分割作者姓名
                    authors = [name.strip() for name in authors_text.split(',') if name.strip()]
                    
                    if authors:
                        return authors
                        
            return None
            
        except Exception as e:
            logging.error(f"Error fetching authors from ArXiv {arxiv_url}: {e}")
            return None


def test_scraper():
    """测试爬虫功能的完整测试函数"""
    scraper = HuggingFacePapersScraper()
    
    print("=== 测试今天论文获取 ===")
    papers = scraper.get_today_papers()
    print(f"Found {len(papers)} papers for today")
    for paper in papers[:3]:
        print(f"Title: {paper['title']}")
        print(f"Authors: {', '.join(paper['authors']) if paper['authors'] else 'No authors info'}")
        print(f"Abstract: {paper['abstract'][:100]}...")
        print(f"URL: {paper['url']}")
        print(f"PDF URL: {paper['pdf_url']}")
        print(f"Votes: {paper['votes']}")
        print(f"Submitted by: {paper['submitted_by']}")
        print(f"Scraped by: {paper['scraped_at']}")
        print("-" * 50)
        
    print("\n=== 测试昨天论文获取 ===")
    yesterday_papers = scraper.get_yesterday_papers()
    print(f"Found {len(yesterday_papers)} papers for yesterday")
    for paper in yesterday_papers[:2]:
        print(f"Title: {paper['title']}")
        print(f"Authors: {', '.join(paper['authors']) if paper['authors'] else 'No authors info'}")
        print(f"Abstract: {paper['abstract'][:100]}...")
        print(f"URL: {paper['url']}")
        print(f"PDF URL: {paper['pdf_url']}")
        print(f"Votes: {paper['votes']}")
        print(f"Submitted by: {paper['submitted_by']}")
        print(f"Scraped by: {paper['scraped_at']}")
        print("-" * 50)
    
    print("\n=== 测试指定日期论文获取（前天） ===")
    # 获取前天的日期
    day_before_yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    specific_date_papers = scraper.get_papers_by_date(day_before_yesterday)
    print(f"Found {len(specific_date_papers)} papers for {day_before_yesterday}")
    for paper in specific_date_papers[:2]:
        print(f"Title: {paper['title']}")
        print(f"Authors: {', '.join(paper['authors']) if paper['authors'] else 'No authors info'}")
        print(f"Abstract: {paper['abstract'][:100]}...")
        print(f"URL: {paper['url']}")
        print(f"PDF URL: {paper['pdf_url']}")
        print(f"Votes: {paper['votes']}")
        print(f"Submitted by: {paper['submitted_by']}")
        print(f"Scraped by: {paper['scraped_at']}")
        print("-" * 50)
    
    print("\n=== 测试无详细信息获取 ===")
    simple_papers = scraper.get_today_papers(fetch_details=False)
    if simple_papers:
        paper = simple_papers[0]
        print(f"Title: {paper['title']}")
        print(f"URL: {paper['url']}")
        print(f"Votes: {paper['votes']}")
        print(f"Submitted by: {paper['submitted_by']}")
        print(f"Scraped by: {paper['scraped_at']}")
        print("-" * 50)


if __name__ == "__main__":
    test_scraper()