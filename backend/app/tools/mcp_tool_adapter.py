"""
MCP工具适配器
将MCP工具转换为ADK Agent可用的工具格式
"""
import json
import inspect
from typing import Dict, Any, List, Callable, Optional
from functools import wraps
from core.logger import LoggerFactory
from services.mcp_service import get_mcp_service

logger = LoggerFactory.get_service_logger(__name__)

# 全局工具调用计数器（按工具名统计，用于防止无限循环）
_tool_call_counts: Dict[str, int] = {}
MAX_CALLS_PER_TOOL = 5  # 每个工具最多调用5次（每次对话会话）

def reset_tool_call_counts():
    """
    重置所有工具调用计数器
    应该在每次新对话开始时调用此函数
    """
    global _tool_call_counts
    if _tool_call_counts:
        logger.debug(f"重置工具调用计数器（之前有 {len(_tool_call_counts)} 个工具的计数）")
        _tool_call_counts.clear()

def _create_mcp_tool_wrapper(tool_name: str, tool_schema: Dict[str, Any]) -> Callable:
    """
    为MCP工具创建Python函数包装器
    
    Args:
        tool_name: 工具名称
        tool_schema: 工具的schema定义（可能包含description、arguments或inputSchema）
    
    Returns:
        Python函数，可以传递给ADK Agent
    """
    # MCP工具可能使用不同的schema格式
    # 1. 标准格式: {"description": "...", "arguments": {"properties": {...}, "required": [...]}}
    # 2. GitHub MCP格式: {"description": "...", "inputSchema": {"type": "object", "properties": {...}, "required": [...]}}
    
    description = tool_schema.get("description", f"Call {tool_name} MCP tool")
    
    # 尝试多种可能的schema格式
    arguments_schema = tool_schema.get("arguments", {})
    if not arguments_schema or "properties" not in arguments_schema:
        # 尝试inputSchema格式（GitHub MCP使用这种格式）
        input_schema = tool_schema.get("inputSchema", {})
        if input_schema and input_schema.get("type") == "object":
            arguments_schema = input_schema
    
    properties = arguments_schema.get("properties", {})
    required = arguments_schema.get("required", [])
    
    # 调试日志：记录schema提取结果
    logger.debug(f"工具 {tool_name} schema提取: properties={list(properties.keys())}, required={required}")
    if not properties:
        logger.debug(f"工具 {tool_name} 没有properties（可能是无参数工具），原始schema: {tool_schema}")
        # 对于无参数工具，properties为空是正常的，不需要警告
    
    # 构建函数文档字符串（更详细的提示）
    docstring = f"{description}\n\n"
    if properties:
        docstring += "Args:\n"
        for param_name, param_info in properties.items():
            param_desc = param_info.get("description", "")
            param_type = param_info.get("type", "string")
            is_required = param_name in required
            docstring += f"    {param_name} ({param_type}): {param_desc}"
            if is_required:
                docstring += " [REQUIRED]"
            else:
                docstring += " (optional)"
            docstring += "\n"
    else:
        docstring += "Args: None\n"
    
    if required:
        docstring += f"\n⚠️ REQUIRED PARAMETERS: {', '.join(required)}\n"
    
    docstring += "\nReturns:\n    Tool execution result as JSON string"
    
    # 创建一个基础的内核函数来处理实际逻辑
    async def _mcp_tool_internal(**kwargs) -> str:
        """
        内部函数：实际执行MCP工具调用
        """
        # 检查调用次数限制（使用全局计数器，按工具名统计）
        _tool_call_counts[tool_name] = _tool_call_counts.get(tool_name, 0) + 1
        current_count = _tool_call_counts[tool_name]
        
        if current_count > MAX_CALLS_PER_TOOL:
            error_msg = (
                f"Error: Tool '{tool_name}' has been called {current_count} times "
                f"(max: {MAX_CALLS_PER_TOOL}). This indicates an infinite loop or repeated parameter errors.\n\n"
                f"Common causes:\n"
                f"1. Parameter name mismatch (e.g., using 'q' instead of 'query')\n"
                f"2. Missing required parameters\n"
                f"3. Invalid parameter values\n\n"
                f"Required parameters: {required if required else 'None'}\n"
                f"Available parameters: {list(properties.keys())}\n\n"
                f"Please review the tool documentation and use correct parameter names and values."
            )
            logger.error(f"工具 {tool_name} 调用次数超限: {current_count} > {MAX_CALLS_PER_TOOL}")
            logger.error(f"工具 {tool_name} 可用参数: {list(properties.keys())}, 必需参数: {required}")
            return error_msg
        
        try:
            # 添加调试日志
            logger.debug(f"工具 {tool_name} 调用参数: {kwargs}")
            logger.debug(f"工具 {tool_name} 必需参数: {required}")
            logger.debug(f"工具 {tool_name} 可用参数: {list(properties.keys())}")
            
            # 验证必需参数（只有在required列表不为空时才检查）
            if required:
                missing_params = [p for p in required if p not in kwargs or kwargs.get(p) is None or kwargs.get(p) == ""]
                if missing_params:
                    # 检查是否是参数值的问题（None或空字符串）
                    actually_missing = []
                    for p in missing_params:
                        if p not in kwargs:
                            actually_missing.append(p)
                        elif kwargs.get(p) is None:
                            actually_missing.append(f"{p} (value is None)")
                        elif kwargs.get(p) == "":
                            actually_missing.append(f"{p} (value is empty string)")
                    
                    if actually_missing:
                        error_msg = (
                            f"Error: Missing required parameters: {', '.join(actually_missing)}.\n"
                            f"Received parameters: {list(kwargs.keys())}\n"
                            f"Required parameters: {required}\n"
                            f"Available parameters: {list(properties.keys())}\n"
                            f"Please ensure all required parameters are provided with valid values."
                        )
                        logger.warning(f"工具 {tool_name} 参数验证失败: 收到 {list(kwargs.keys())}, 必需 {required}, 缺少 {actually_missing}")
                        return error_msg
            
            # 过滤参数，只保留schema中定义的参数
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in properties}
            
            # 如果有未识别的参数，记录警告
            unknown_params = set(kwargs.keys()) - set(properties.keys())
            if unknown_params:
                logger.warning(f"工具 {tool_name} 收到未知参数: {unknown_params}，将忽略这些参数。有效参数: {list(properties.keys())}")
            
            # 调用MCP服务
            mcp_service = get_mcp_service()
            result = await mcp_service.call_tool(tool_name, filtered_kwargs)
            
            # 解析MCP工具返回的结果
            # MCP工具可能返回: {"result": "..."} 或直接的dict
            if isinstance(result, dict):
                # 检查是否是错误响应（GitHub MCP格式）
                result_str = result.get("result", "")
                if isinstance(result_str, str):
                    try:
                        # 尝试解析result中的JSON字符串
                        parsed_result = json.loads(result_str)
                        if isinstance(parsed_result, dict) and parsed_result.get("isError"):
                            # 这是错误响应
                            error_content = parsed_result.get("content", [])
                            error_messages = []
                            for item in error_content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    error_messages.append(item.get("text", ""))
                            error_msg = " | ".join(error_messages) if error_messages else "Unknown error"
                            
                            # 如果错误是参数相关，提供更详细的提示
                            if "parameter" in error_msg.lower() or "missing" in error_msg.lower():
                                error_msg += f"\n\n提示: 该工具需要的参数包括: {list(properties.keys())}"
                                if required:
                                    error_msg += f"\n必需参数: {required}"
                                error_msg += "\n请确保使用正确的参数名称和格式。"
                            
                            logger.error(f"工具 {tool_name} 返回错误: {error_msg}")
                            return f"Error: {error_msg}"
                        else:
                            # 正常结果
                            return json.dumps(parsed_result, ensure_ascii=False, indent=2)
                    except (json.JSONDecodeError, TypeError):
                        # result不是JSON字符串，直接使用
                        pass
                
                # 直接返回dict结果
                return json.dumps(result, ensure_ascii=False, indent=2)
            elif isinstance(result, str):
                return result
            else:
                return str(result)
                
        except Exception as e:
            error_msg = f"Error calling {tool_name}: {str(e)}"
            logger.error(f"MCP工具调用失败: {tool_name}, 错误: {e}")
            return error_msg
    
    # 动态创建带有明确参数的函数签名
    # 为了ADK Agent能够识别参数，我们需要创建一个带有明确参数的函数
    # 使用exec动态生成函数代码
    # 重要：Python要求必需参数（无默认值）必须在可选参数（有默认值）之前
    param_names = list(properties.keys())
    required_params = []
    optional_params = []
    param_types = {}
    
    for param_name, param_info in properties.items():
        param_type = param_info.get("type", "string")
        # 将JSON Schema类型映射到Python类型
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        python_type = type_mapping.get(param_type, str)
        param_types[param_name] = python_type
        
        # 构建参数定义字符串，区分必需和可选参数
        param_def = f"{param_name}: {python_type.__name__}"
        if param_name in required:
            required_params.append(param_def)
        else:
            optional_params.append(f"{param_def} = None")
    
    # 构建函数参数字符串：必需参数在前，可选参数在后
    all_param_defs = required_params + optional_params
    if all_param_defs:
        params_str = ", ".join(all_param_defs)
    else:
        params_str = ""
    
    # 构建函数体代码
    call_params = {name: name for name in param_names}
    call_params_str = ", ".join([f"{k}=v" for k, v in call_params.items()])
    
    # 动态创建函数
    func_code = f"""
async def mcp_tool_function({params_str}) -> str:
    \"\"\"{docstring}\"\"\"
    kwargs = {{k: v for k, v in locals().items() if k != 'self' and v is not None}}
    return await _mcp_tool_internal(**kwargs)
"""
    
    # 执行代码以创建函数
    func_namespace = {"_mcp_tool_internal": _mcp_tool_internal}
    exec(func_code, func_namespace)
    mcp_tool_function = func_namespace["mcp_tool_function"]
    
    # 设置函数元数据
    mcp_tool_function.__name__ = tool_name
    mcp_tool_function.__doc__ = docstring
    
    return mcp_tool_function

async def get_github_mcp_tools() -> List[Callable]:
    """
    获取所有GitHub MCP工具并转换为ADK工具格式
    
    Returns:
        ADK工具函数列表
    """
    try:
        mcp_service = get_mcp_service()
        tools = await mcp_service.list_tools()
        
        if not tools:
            logger.warning("未获取到MCP工具，返回空列表")
            return []
        
        adk_tools = []
        for tool in tools:
            tool_name = tool.get("name")
            if not tool_name:
                continue
            
            try:
                # 创建工具包装器
                tool_function = _create_mcp_tool_wrapper(tool_name, tool)
                adk_tools.append(tool_function)
                logger.debug(f"✓ 创建MCP工具包装器: {tool_name}")
            except Exception as e:
                logger.error(f"创建工具包装器失败: {tool_name}, 错误: {e}")
                continue
        
        logger.info(f"✓ 成功创建 {len(adk_tools)} 个GitHub MCP工具")
        return adk_tools
        
    except Exception as e:
        logger.error(f"获取GitHub MCP工具失败: {type(e).__name__}: {e}")
        return []
