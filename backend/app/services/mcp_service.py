"""
MCP客户端服务
用于连接GitHub MCP服务器并调用工具
"""
import httpx
import json
import uuid
from typing import List, Dict, Any, Optional
from core.config import settings
from core.logger import LoggerFactory

logger = LoggerFactory.get_service_logger(__name__)

class MCPService:
    """MCP客户端服务"""
    
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        """
        初始化MCP客户端
        
        Args:
            base_url: MCP服务器URL
            token: 认证token（如果已包含"Bearer "前缀则直接使用）
        """
        self.base_url = base_url or settings.GITHUB_MCP_URL
        # 处理token：如果已包含"Bearer "则直接使用，否则添加
        raw_token = token or settings.GITHUB_MCP_TOKEN or ""
        if raw_token.startswith("Bearer "):
            self.token = raw_token
        elif raw_token:
            self.token = f"Bearer {raw_token}"
        else:
            self.token = None
        self._client = None
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        self._request_id = 0
    
    def _get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端"""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.token:
                headers["Authorization"] = self.token
            
            self._client = httpx.AsyncClient(
                base_url=self.base_url.rstrip("/") + "/",
                headers=headers,
                timeout=30.0
            )
        return self._client
    
    def _get_next_id(self) -> int:
        """获取下一个请求ID"""
        self._request_id += 1
        return self._request_id
    
    async def _send_jsonrpc_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        发送JSON-RPC 2.0格式的请求
        
        Args:
            method: 方法名（如 "tools/list"）
            params: 请求参数
            
        Returns:
            JSON-RPC响应结果
        """
        client = self._get_client()
        request_id = self._get_next_id()
        
        # 构建JSON-RPC 2.0请求
        request_payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        logger.debug(f"发送MCP JSON-RPC请求: method={method}, id={request_id}")
        
        try:
            # GitHub MCP可能使用不同的协议格式
            # 首先尝试JSON-RPC 2.0格式（标准MCP协议）
            # 然后尝试REST风格API
            
            # JSON-RPC格式尝试的端点
            jsonrpc_endpoints = [
                "",  # 根路径
                "rpc",  # 标准的JSON-RPC端点
                "jsonrpc",  # 另一个常见的JSON-RPC端点
            ]
            
            last_error = None
            
            # 先尝试JSON-RPC格式
            for endpoint in jsonrpc_endpoints:
                try:
                    logger.debug(f"尝试端点: {endpoint or 'root'}")
                    response = await client.post(
                        endpoint,
                        json=request_payload
                    )
                    response.raise_for_status()
                    
                    # 检查响应内容类型
                    content_type = response.headers.get("content-type", "")
                    response_text = response.text
                    
                    logger.debug(f"响应状态: {response.status_code}, Content-Type: {content_type}")
                    logger.debug(f"响应内容前500字符: {response_text[:500]}")
                    
                    # 检查是否是SSE格式（Server-Sent Events）
                    if "text/event-stream" in content_type or response_text.strip().startswith("event:"):
                        # 解析SSE格式
                        logger.debug("检测到SSE格式响应，开始解析...")
                        json_data = None
                        for line in response_text.splitlines():
                            line = line.strip()
                            if line.startswith("data:"):
                                # 提取data行中的JSON
                                json_str = line[5:].strip()  # 移除"data:"前缀
                                try:
                                    json_data = json.loads(json_str)
                                    logger.debug("✓ 成功从SSE格式中提取JSON")
                                    break
                                except json.JSONDecodeError as e:
                                    logger.debug(f"SSE data行JSON解析失败: {json_str[:200]}, 错误: {e}")
                                    continue
                        
                        if json_data:
                            result = json_data
                        else:
                            logger.error(f"SSE格式中未找到有效的JSON数据")
                            last_error = Exception("SSE响应中未找到有效的JSON数据")
                            continue
                    else:
                        # 尝试直接解析JSON
                        try:
                            result = response.json()
                        except json.JSONDecodeError as json_err:
                            logger.error(f"JSON解析失败，端点: {endpoint or 'root'}, 响应内容: {response_text[:500]}")
                            last_error = json_err
                            continue  # 尝试下一个端点
                    
                    # 检查JSON-RPC错误
                    if "error" in result:
                        error = result["error"]
                        error_msg = f"JSON-RPC错误 {error.get('code')}: {error.get('message')}"
                        logger.error(error_msg)
                        raise Exception(error_msg)
                    
                    # 返回结果
                    logger.debug(f"✓ 成功从端点 '{endpoint or 'root'}' 获取响应")
                    return result.get("result", {})
                    
                except httpx.HTTPStatusError as http_err:
                    # 如果是4xx或5xx错误，记录详细信息
                    error_detail = ""
                    try:
                        error_body = http_err.response.json()
                        error_detail = f" - JSON: {error_body}"
                    except:
                        error_detail = f" - Text: {http_err.response.text[:500]}"
                    
                    logger.debug(f"端点 '{endpoint or 'root'}' HTTP错误 {http_err.response.status_code}: {error_detail}")
                    last_error = http_err
                    continue  # 尝试下一个端点
                    
            # 如果JSON-RPC格式都失败，尝试REST风格API（工具列表使用GET方法）
            if method == "tools/list":
                logger.debug("JSON-RPC格式失败，尝试REST风格API...")
                try:
                    # REST风格：GET /tools/list 或 POST /tools/list
                    for rest_endpoint in ["tools/list", "api/tools"]:
                        try:
                            # 先尝试GET
                            response = await client.get(rest_endpoint)
                            if response.status_code == 200:
                                result = response.json()
                                if "tools" in result:
                                    return {"tools": result["tools"]}
                                elif isinstance(result, list):
                                    return {"tools": result}
                            
                            # 再尝试POST（空body）
                            response = await client.post(rest_endpoint, json={})
                            if response.status_code == 200:
                                result = response.json()
                                if "tools" in result:
                                    return {"tools": result["tools"]}
                                elif isinstance(result, list):
                                    return {"tools": result}
                        except Exception as rest_err:
                            logger.debug(f"REST端点 '{rest_endpoint}' 失败: {rest_err}")
                            continue
                except Exception as rest_attempt_err:
                    logger.debug(f"REST API尝试失败: {rest_attempt_err}")
            
            # 所有端点都失败了，抛出最后一个错误
            if last_error:
                if isinstance(last_error, httpx.HTTPStatusError):
                    # 记录完整的错误信息
                    try:
                        error_text = last_error.response.text[:1000]
                        error_headers = dict(last_error.response.headers)
                        logger.error(f"最终HTTP错误详情:\n状态码: {last_error.response.status_code}\nURL: {last_error.response.url}\n响应头: {error_headers}\n响应内容: {error_text}")
                    except:
                        pass
                    raise last_error
                else:
                    raise Exception(f"所有端点都失败，最后一个错误: {last_error}")
            else:
                raise Exception("所有端点都失败，但没有记录到具体错误")
            
        except httpx.HTTPStatusError as e:
            # 最终的错误处理
            error_detail = ""
            try:
                error_body = e.response.json()
                error_detail = f" - JSON: {error_body}"
            except:
                error_detail = f" - Text: {e.response.text[:500]}"
            
            logger.error(f"HTTP错误 {e.response.status_code} 请求URL: {e.response.url}{error_detail}")
            raise
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        获取MCP服务器上的所有可用工具
        
        Returns:
            工具列表，每个工具包含name, description, arguments等信息
        """
        if self._tools_cache is not None:
            return self._tools_cache
        
        try:
            # 使用JSON-RPC 2.0格式调用MCP工具列表接口
            result = await self._send_jsonrpc_request("tools/list", {})
            
            # 解析MCP响应格式
            if "tools" in result:
                tools = result["tools"]
            elif isinstance(result, list):
                tools = result
            else:
                tools = []
            
            self._tools_cache = tools
            logger.info(f"✓ 获取到 {len(tools)} 个MCP工具")
            return tools
            
        except Exception as e:
            logger.error(f"获取MCP工具列表失败: {type(e).__name__}: {e}")
            # 如果MCP协议调用失败，返回空列表
            return []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用MCP工具
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
        
        Returns:
            工具调用结果
        """
        try:
            # 使用JSON-RPC 2.0格式调用MCP工具
            result = await self._send_jsonrpc_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            logger.info(f"✓ 工具调用成功: {tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"工具调用失败: {tool_name}, 错误: {type(e).__name__}: {e}")
            raise
    
    async def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具的schema定义
        
        Args:
            tool_name: 工具名称
        
        Returns:
            工具的schema定义，如果不存在则返回None
        """
        tools = await self.list_tools()
        for tool in tools:
            if tool.get("name") == tool_name:
                return tool
        return None
    
    async def close(self):
        """关闭HTTP客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

# 创建全局MCP服务实例
_mcp_service: Optional[MCPService] = None

def get_mcp_service() -> MCPService:
    """获取MCP服务实例（单例）"""
    global _mcp_service
    if _mcp_service is None:
        _mcp_service = MCPService()
    return _mcp_service
