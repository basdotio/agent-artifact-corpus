#!/usr/bin/env python
import os
import asyncio
import logging
import json
import time
import snowflake.connector
from dotenv import load_dotenv
import mcp.server.stdio
from mcp.server import Server
from mcp.types import Tool, ServerResult, TextContent
from contextlib import closing
from typing import Optional, Any

# 配置日志 / Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('snowflake_server')

load_dotenv()

class SnowflakeConnection:
    """
    Snowflake数据库连接管理类
    Snowflake database connection management class
    """
    def __init__(self):
        # 初始化配置信息 / Initialize configuration
        self.config = {
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD"),
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "database": os.getenv("SNOWFLAKE_DATABASE"),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE"),
        }
        self.conn: Optional[snowflake.connector.SnowflakeConnection] = None
        logger.info(f"Initialized with config (excluding password): {json.dumps({k:v for k,v in self.config.items() if k != 'password'})}")
    
    def ensure_connection(self) -> snowflake.connector.SnowflakeConnection:
        """
        确保数据库连接可用，如果连接不存在或已断开则重新建立连接
        Ensure database connection is available, create new connection if it doesn't exist or is disconnected
        """
        try:
            # 检查连接是否需要重新建立 / Check if connection needs to be re-established
            if self.conn is None:
                logger.info("Creating new Snowflake connection...")
                self.conn = snowflake.connector.connect(
                    **self.config,
                    client_session_keep_alive=True,
                    network_timeout=15,
                    login_timeout=15
                )
                self.conn.cursor().execute("ALTER SESSION SET TIMEZONE = 'UTC'")
                logger.info("New connection established and configured")
            
            # 测试连接是否有效 / Test if connection is valid
            try:
                self.conn.cursor().execute("SELECT 1")
            except:
                logger.info("Connection lost, reconnecting...")
                self.conn = None
                return self.ensure_connection()
                
            return self.conn
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            raise

    def execute_query(self, query: str) -> list[dict[str, Any]]:
        """
        执行SQL查询并返回结果
        Execute SQL query and return results
        
        Args:
            query (str): SQL查询语句 / SQL query statement
            
        Returns:
            list[dict[str, Any]]: 查询结果列表 / List of query results
        """
        start_time = time.time()
        logger.info(f"Executing query: {query[:200]}...")  # 只记录前200个字符 / Log only first 200 characters
        
        try:
            conn = self.ensure_connection()
            with conn.cursor() as cursor:
                # 对于写操作使用事务 / Use transaction for write operations
                if any(query.strip().upper().startswith(word) for word in ['INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER']):
                    cursor.execute("BEGIN")
                    try:
                        cursor.execute(query)
                        conn.commit()
                        logger.info(f"Write query executed in {time.time() - start_time:.2f}s")
                        return [{"affected_rows": cursor.rowcount}]
                    except Exception as e:
                        conn.rollback()
                        raise
                else:
                    # 读操作 / Read operations
                    cursor.execute(query)
                    if cursor.description:
                        columns = [col[0] for col in cursor.description]
                        rows = cursor.fetchall()
                        results = [dict(zip(columns, row)) for row in rows]
                        logger.info(f"Read query returned {len(results)} rows in {time.time() - start_time:.2f}s")
                        return results
                    return []
                
        except snowflake.connector.errors.ProgrammingError as e:
            logger.error(f"SQL Error: {str(e)}")
            logger.error(f"Error Code: {getattr(e, 'errno', 'unknown')}")
            raise
        except Exception as e:
            logger.error(f"Query error: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            raise

    def close(self):
        """
        关闭数据库连接
        Close database connection
        """
        if self.conn:
            try:
                self.conn.close()
                logger.info("Connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")
            finally:
                self.conn = None

class SnowflakeServer(Server):
    """
    Snowflake MCP服务器类，处理与客户端的交互
    Snowflake MCP server class, handles client interactions
    """
    def __init__(self):
        super().__init__(name="snowflake-server")
        self.db = SnowflakeConnection()
        logger.info("SnowflakeServer initialized")

        @self.list_tools()
        async def handle_tools():
            """
            返回可用工具列表
            Return list of available tools
            """
            return [
                Tool(
                    name="execute_query",
                    description="Execute a SQL query on Snowflake",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "SQL query to execute"
                            }
                        },
                        "required": ["query"]
                    }
                )
            ]

        @self.call_tool()
        async def handle_call_tool(name: str, arguments: dict):
            """
            处理工具调用请求
            Handle tool call requests
            
            Args:
                name (str): 工具名称 / Tool name
                arguments (dict): 工具参数 / Tool arguments
                
            Returns:
                list[TextContent]: 执行结果 / Execution results
            """
            if name == "execute_query":
                start_time = time.time()
                try:
                    result = self.db.execute_query(arguments["query"])
                    execution_time = time.time() - start_time
                    
                    return [TextContent(
                        type="text",
                        text=f"Results (execution time: {execution_time:.2f}s):\n{result}"
                    )]
                except Exception as e:
                    error_message = f"Error executing query: {str(e)}"
                    logger.error(error_message)
                    return [TextContent(
                        type="text",
                        text=error_message
                    )]

    def __del__(self):
        """
        清理资源，关闭数据库连接
        Clean up resources, close database connection
        """
        if hasattr(self, 'db'):
            self.db.close()

async def main():
    """
    主函数，启动服务器并处理请求
    Main function, starts server and handles requests
    """
    try:
        server = SnowflakeServer()
        initialization_options = server.create_initialization_options()
        logger.info("Starting server")
        
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                initialization_options
            )
    except Exception as e:
        logger.critical(f"Server failed: {str(e)}", exc_info=True)
        raise
    finally:
        logger.info("Server shutting down")

if __name__ == "__main__":
    asyncio.run(main())