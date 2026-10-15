import asyncio
import json
import subprocess
import time
import pytest
from unittest.mock import patch
from pydantic import AnyUrl


class TestMCPServer:
    """测试MCP服务器功能"""
    
    def test_server_can_start(self):
        """测试服务器能够启动并处理退出"""
        # 启动服务器进程
        process = subprocess.Popen(
            ["uv", "run", "python", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 等待一小段时间让服务器启动
        time.sleep(1)
        
        # 发送EOF信号让服务器正常退出
        process.stdin.close() if process.stdin else None
        
        # 等待进程结束
        try:
            return_code = process.wait(timeout=5)
            # MCP服务器在接收到EOF后正常退出，返回码通常是0
            assert return_code == 0, f"服务器异常退出，返回码: {return_code}"
        except subprocess.TimeoutExpired:
            process.terminate()
            process.wait()
            pytest.fail("服务器无法正常退出")

    @pytest.mark.asyncio
    async def test_server_handlers(self):
        """测试服务器处理函数"""
        from main import handle_list_tools, handle_list_resources, handle_call_tool, handle_read_resource
        
        # 测试列出工具
        tools = await handle_list_tools()
        assert len(tools) == 3
        tool_names = [tool.name for tool in tools]
        expected_tools = ["get_papers_by_date", "get_today_papers", "get_yesterday_papers"]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    @pytest.mark.asyncio
    async def test_list_resources_handler(self):
        """测试列出资源的处理函数"""
        from main import handle_list_resources
        
        resources = await handle_list_resources()
        assert len(resources) == 2
        
        resource_uris = [str(resource.uri) for resource in resources]
        expected_uris = ["papers://today", "papers://yesterday"]
        for expected_uri in expected_uris:
            assert expected_uri in resource_uris

    @pytest.mark.asyncio 
    async def test_call_tool_get_papers_by_date(self):
        """测试调用get_papers_by_date工具"""
        from main import handle_call_tool
        
        # 模拟一个返回空结果的调用（避免实际网络请求）
        with patch('main.scraper.get_papers_by_date', return_value=[]):
            result = await handle_call_tool("get_papers_by_date", {"date": "2024-01-01"})
            assert len(result) == 1
            assert "No papers found" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_get_today_papers(self):
        """测试调用get_today_papers工具"""
        from main import handle_call_tool
        
        with patch('main.scraper.get_today_papers', return_value=[]):
            result = await handle_call_tool("get_today_papers", {})
            assert len(result) == 1
            assert "No papers found" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_get_yesterday_papers(self):
        """测试调用get_yesterday_papers工具"""
        from main import handle_call_tool
        
        with patch('main.scraper.get_yesterday_papers', return_value=[]):
            result = await handle_call_tool("get_yesterday_papers", {})
            assert len(result) == 1
            assert "No papers found" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_with_papers_data(self):
        """测试工具返回论文数据时的格式"""
        from main import handle_call_tool
        
        # 模拟论文数据
        mock_papers = [{
            "title": "Test Paper",
            "authors": ["Author One", "Author Two"],
            "abstract": "This is a test abstract",
            "url": "https://huggingface.co/papers/test",
            "pdf_url": "https://arxiv.org/pdf/test.pdf",
            "tags": ["machine-learning"],
            "votes": 42,
            "submitted_by": "testuser",
            "scraped_at": "2024-01-01T12:00:00"
        }]
        
        with patch('main.scraper.get_papers_by_date', return_value=mock_papers):
            result = await handle_call_tool("get_papers_by_date", {"date": "2024-01-01"})
            assert len(result) == 1
            assert "Found 1 papers" in result[0].text
            assert "Test Paper" in result[0].text
            assert "Author One, Author Two" in result[0].text

    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        """测试调用未知工具"""
        from main import handle_call_tool
        
        result = await handle_call_tool("unknown_tool", {})
        assert len(result) == 1
        assert "Error:" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_with_invalid_arguments(self):
        """测试使用无效参数调用工具"""
        from main import handle_call_tool
        
        # get_papers_by_date需要date参数
        result = await handle_call_tool("get_papers_by_date", None)
        assert len(result) == 1
        assert "Error:" in result[0].text

    @pytest.mark.asyncio
    async def test_read_resource_today(self):
        """测试读取今日资源"""
        from main import handle_read_resource
        
        with patch('main.scraper.get_today_papers', return_value=[]):
            uri = AnyUrl("papers://today")
            result = await handle_read_resource(uri)
            
            # 验证返回的是有效的JSON字符串
            papers_data = json.loads(result)
            assert isinstance(papers_data, list)

    @pytest.mark.asyncio
    async def test_read_resource_yesterday(self):
        """测试读取昨日资源"""
        from main import handle_read_resource
        
        with patch('main.scraper.get_yesterday_papers', return_value=[]):
            uri = AnyUrl("papers://yesterday")
            result = await handle_read_resource(uri)
            
            # 验证返回的是有效的JSON字符串
            papers_data = json.loads(result)
            assert isinstance(papers_data, list)

    @pytest.mark.asyncio
    async def test_read_resource_with_data(self):
        """测试读取包含数据的资源"""
        from main import handle_read_resource
        
        mock_papers = [{
            "title": "Test Paper",
            "authors": ["Author One"],
            "abstract": "Test abstract",
            "url": "https://example.com",
            "votes": 10
        }]
        
        with patch('main.scraper.get_today_papers', return_value=mock_papers):
            uri = AnyUrl("papers://today")
            result = await handle_read_resource(uri)
            papers_data = json.loads(result)
            
            assert len(papers_data) == 1
            assert papers_data[0]["title"] == "Test Paper"
            assert papers_data[0]["authors"] == ["Author One"]

    @pytest.mark.asyncio
    async def test_read_invalid_resource(self):
        """测试读取无效资源"""
        from main import handle_read_resource
        
        try:
            uri = AnyUrl("papers://invalid")
            await handle_read_resource(uri)
            pytest.fail("应该抛出异常")
        except Exception as e:
            assert "Unknown resource" in str(e)

    @pytest.mark.asyncio
    async def test_scraper_integration(self):
        """测试与scraper的集成"""
        from main import scraper
        
        # 验证scraper对象存在并且有正确的方法
        assert hasattr(scraper, 'get_papers_by_date')
        assert hasattr(scraper, 'get_today_papers') 
        assert hasattr(scraper, 'get_yesterday_papers')
        assert callable(scraper.get_papers_by_date)
        assert callable(scraper.get_today_papers)
        assert callable(scraper.get_yesterday_papers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])