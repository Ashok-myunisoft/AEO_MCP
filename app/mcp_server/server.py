import logging
from mcp.server.mcpserver import MCPServer
from app.config.settings import settings
from app.mcp_server import tools

logging.basicConfig(level=settings.LOG_LEVEL)
mcp=MCPServer(name=settings.MCP_SERVER_NAME,version="1.0.0",instructions="Read-only access to the GoodBooks Marketing FAQ knowledge registry.",log_level=settings.LOG_LEVEL.upper())

@mcp.tool(name="search_faq",description="Search registered FAQ knowledge and return matching answers with source references.")
async def search_faq(query: str, category: str | None=None, source_id: str | None=None, limit: int=5):
    return await tools.search_faq(query,category,source_id,limit)

@mcp.tool(name="get_faq_answer",description="Retrieve a specific FAQ by its UUID.")
def get_faq_answer(faq_id: str): return tools.get_faq_answer(faq_id)

@mcp.tool(name="list_knowledge_sources",description="List registered URL and document knowledge sources.")
def list_knowledge_sources(source_type: str | None=None, status: str | None=None, category: str | None=None):
    return tools.list_knowledge_sources(source_type,status,category)

@mcp.tool(name="search_by_category",description="Search FAQ content within a specific product or category.")
async def search_by_category(category: str, query: str, limit: int=5):
    return await tools.search_by_category(category,query,limit)

app=mcp.streamable_http_app(streamable_http_path="/mcp",json_response=True,stateless_http=True,host=settings.MCP_SERVER_HOST)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host=settings.MCP_SERVER_HOST,port=settings.MCP_SERVER_PORT,log_level=settings.LOG_LEVEL.lower())
