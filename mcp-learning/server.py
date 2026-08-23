from fastmcp import FastMCP

mcp = FastMCP("My First MCP Server")


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two integers together."""
    return a + b


if __name__ == "__main__":
    mcp.run()