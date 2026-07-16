from fastmcp import FastMCP
import requests

# 1. 初始化一个 MCP 服务器实例
mcp = FastMCP(name="MyURLFetcher")

# 2. 定义一个工具函数，并用 @mcp.tool 装饰它
@mcp.tool
def fetch_url_content(url: str) -> str:
    """
    抓取指定 URL 的网页内容并返回纯文本。
    
    Args:
        url: 要抓取的网页链接 (例如: https://example.com)
    """
    try:
        # 设置一个常见的 User-Agent，避免被一些网站拒绝
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # 发送 GET 请求， timeout 防止卡死
        response = requests.get(url, headers=headers, timeout=10)
        # 如果请求失败，则抛出异常
        response.raise_for_status()
        # 返回文本内容，并设置正确的编码
        return response.text
    except requests.exceptions.RequestException as e:
        # 如果出错，返回错误信息，让 AI 知道发生了什么
        return f"获取URL时出错: {e}"

# 3. 让服务器跑起来
if __name__ == "__main__":
    mcp.run()