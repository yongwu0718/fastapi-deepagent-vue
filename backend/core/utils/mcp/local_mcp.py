from fastmcp import FastMCP
from backend.config.logger import setup_logging, get_logger

logger = get_logger(__name__)

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers
    Args:
        a (int): The first number.
        b (int): The second number.
    Returns:
        int: The sum of a and b.
    """
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers
    Args:
        a (int): The first number.
        b (int): The second number.
    Returns:
        int: The product of a and b.
    """
    return a * b

if __name__ == "__main__":
    setup_logging()
    logger.info("MCP Server 启动")
    mcp.run(transport="stdio")