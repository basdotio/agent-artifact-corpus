from core.gemma import Gemma
from mcp_client import MCPClient
from core.tools import ToolManager

class Chat:
    def __init__(self, gemma_service: Gemma, clients: dict[str, MCPClient]):
        self.gemma_service: Gemma = gemma_service
        self.clients: dict[str, MCPClient] = clients
        self.messages: list = []

    async def _process_query(self, query: str):
        self.messages.append({"role": "user", "content": query})

    async def run(
        self,
        query: str,
    ) -> str:
        final_text_response = ""

        await self._process_query(query)

        while True:
            response = self.gemma_service.chat(
                messages=self.messages,
                tools=await ToolManager.get_all_tools(self.clients),
            )

            self.gemma_service.add_assistant_message(self.messages, response)
            
            if self.gemma_service.has_tool_calls(response):
                text = self.gemma_service.text_from_message(response)
                if text:
                    print(text)
                tool_result_parts = await ToolManager.execute_tool_requests(
                    self.clients, response
                )

                self.gemma_service.add_user_message(
                    self.messages, tool_result_parts
                )
            else:
                final_text_response = self.gemma_service.text_from_message(
                    response
                )
                break

        return final_text_response
