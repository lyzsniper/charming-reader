"""
运行时工具工厂
将数据库中的工具记录转换为 ADK 可调用的工具函数
"""
from __future__ import annotations

import asyncio
import importlib
import json
from typing import Any, Callable, Dict, List, Tuple

import httpx
from core.logger import LoggerFactory
from services.mcp_service import get_mcp_service
from tools.tool_call_guard import check_and_increment_tool_call

logger = LoggerFactory.get_service_logger(__name__)


def _extract_schema(schema: Dict[str, Any] | None) -> Tuple[Dict[str, Any], List[str]]:
    if not schema:
        return {}, []
    if "properties" in schema:
        return schema.get("properties", {}) or {}, schema.get("required", []) or []
    input_schema = schema.get("inputSchema")
    if isinstance(input_schema, dict) and input_schema.get("type") == "object":
        return input_schema.get("properties", {}) or {}, input_schema.get("required", []) or []
    return {}, []


def _serialize_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False, indent=2)
    except TypeError:
        return str(result)


def _filter_kwargs(kwargs: Dict[str, Any], properties: Dict[str, Any]) -> Dict[str, Any]:
    if not properties:
        return kwargs
    return {k: v for k, v in kwargs.items() if k in properties}


def _missing_required(kwargs: Dict[str, Any], required: List[str]) -> List[str]:
    if not required:
        return []
    missing = []
    for name in required:
        if name not in kwargs or kwargs.get(name) in (None, ""):
            missing.append(name)
    return missing


def _build_function_with_signature(
    internal_func: Callable,
    name: str,
    docstring: str,
    properties: Dict[str, Any],
    required: List[str]
) -> Callable:
    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict
    }
    required_params = []
    optional_params = []
    for param_name, param_info in properties.items():
        param_type = param_info.get("type", "string")
        python_type = type_mapping.get(param_type, str)
        param_def = f"{param_name}: {python_type.__name__}"
        if param_name in required:
            required_params.append(param_def)
        else:
            optional_params.append(f"{param_def} = None")

    all_param_defs = required_params + optional_params
    params_str = ", ".join(all_param_defs)

    func_code = f"""
async def tool_function({params_str}) -> str:
    \"\"\"{docstring}\"\"\"
    kwargs = {{k: v for k, v in locals().items() if k != 'self' and v is not None}}
    return await _internal(**kwargs)
"""
    func_namespace = {"_internal": internal_func}
    exec(func_code, func_namespace)
    tool_function = func_namespace["tool_function"]
    tool_function.__name__ = name
    tool_function.__doc__ = docstring
    return tool_function


def build_tool_callable(tool) -> Callable:
    """
    将数据库 Tool 记录转换为可调用工具函数
    """
    properties, required = _extract_schema(tool.schema_config or {})
    description = tool.description or f"Call tool {tool.name}"
    docstring = f"{description}\n\n"
    if properties:
        docstring += "Args:\n"
        for param_name, param_info in properties.items():
            param_desc = param_info.get("description", "")
            param_type = param_info.get("type", "string")
            is_required = param_name in required
            docstring += f"    {param_name} ({param_type}): {param_desc}"
            docstring += " [REQUIRED]\n" if is_required else " (optional)\n"
    else:
        docstring += "Args: None\n"

    async def _run_mcp_tool(**kwargs) -> str:
        allowed, _, error_msg = check_and_increment_tool_call(tool.name)
        if not allowed:
            return error_msg or "Error: Tool call limit exceeded"
        missing = _missing_required(kwargs, required)
        if missing:
            return f"Error: Missing required parameters: {', '.join(missing)}"
        filtered = _filter_kwargs(kwargs, properties)
        mcp_service = get_mcp_service()
        result = await mcp_service.call_tool(tool.name, filtered)
        return _serialize_result(result)

    async def _run_api_tool(**kwargs) -> str:
        allowed, _, error_msg = check_and_increment_tool_call(tool.name)
        if not allowed:
            return error_msg or "Error: Tool call limit exceeded"
        missing = _missing_required(kwargs, required)
        if missing:
            return f"Error: Missing required parameters: {', '.join(missing)}"
        source = tool.source_config or {}
        url = source.get("url") or source.get("endpoint")
        if not url:
            return "Error: API tool missing url/endpoint"
        method = (source.get("method") or "POST").upper()
        headers = source.get("headers") or {}
        timeout = source.get("timeout") or 30

        filtered = _filter_kwargs(kwargs, properties)
        path_params = {k: v for k, v in filtered.items() if f"{{{k}}}" in url}
        if path_params:
            url = url.format(**path_params)
            for key in path_params:
                filtered.pop(key, None)

        params = filtered if method in ("GET", "DELETE") else None
        json_body = None if method in ("GET", "DELETE") else filtered

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(method, url, params=params, json=json_body, headers=headers)
        try:
            payload = response.json()
        except ValueError:
            payload = response.text

        return _serialize_result(
            {
                "status_code": response.status_code,
                "data": payload,
            }
        )

    async def _run_python_tool(**kwargs) -> str:
        allowed, _, error_msg = check_and_increment_tool_call(tool.name)
        if not allowed:
            return error_msg or "Error: Tool call limit exceeded"
        missing = _missing_required(kwargs, required)
        if missing:
            return f"Error: Missing required parameters: {', '.join(missing)}"
        source = tool.source_config or {}
        module_path = source.get("module_path")
        function_name = source.get("function_name")
        if not module_path or not function_name:
            return "Error: Python tool missing module_path/function_name"

        try:
            module = importlib.import_module(module_path)
        except Exception as exc:
            return f"Error: Cannot import module {module_path}: {exc}"

        func = getattr(module, function_name, None)
        if not callable(func):
            return f"Error: Function {function_name} not found in {module_path}"

        filtered = _filter_kwargs(kwargs, properties)
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(**filtered)
            else:
                result = await asyncio.to_thread(func, **filtered)
            return _serialize_result(result)
        except Exception as exc:
            logger.error(f"Python tool execution failed: {tool.name} - {exc}")
            return f"Error: Python tool execution failed: {exc}"

    if tool.tool_type == "mcp":
        internal = _run_mcp_tool
    elif tool.tool_type == "python":
        internal = _run_python_tool
    else:
        internal = _run_api_tool

    return _build_function_with_signature(internal, tool.name, docstring, properties, required)
