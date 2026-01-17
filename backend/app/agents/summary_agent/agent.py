"""
总结智能体 - 将对话历史总结为完整的 MD 方案
"""
from typing import List, Dict, Any, Tuple, Optional
from io import BytesIO
from datetime import datetime, timedelta
from uuid import uuid4
import re

from google.adk import Runner
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import Content, Part

from core.config import settings
from core.logger import LoggerFactory
from services.chat_service import ChatService
from services.storage_service import get_storage_service
from services.session_service import get_session_service

logger = LoggerFactory.get_service_logger(__name__)


async def score_message_importance(
    message: Dict[str, Any],
    model: LiteLlm
) -> float:
    """
    使用 LLM 对消息进行重要性打分（0-1）
    
    Args:
        message: 消息字典，包含 role, content 等字段
        model: LLM 模型实例
    
    Returns:
        float: 重要性分数（0-1）
    """
    role = message.get("role", "")
    content = message.get("content", "")
    
    # 如果是用户消息，通常更重要
    if role == "user":
        base_score = 0.7
    elif role == "assistant":
        base_score = 0.5
    else:
        base_score = 0.3
    
    # 内容长度也是一个因子（太短的消息通常不重要）
    content_length = len(content)
    length_score = min(content_length / 500, 1.0) * 0.2
    
    # 使用 LLM 进行更精确的打分
    scoring_prompt = f"""请对以下对话消息的重要性进行打分（0-1分），考虑：
1. 消息的实质性内容（是否有具体需求、方案、结论等）
2. 消息的完整性和详细程度
3. 消息的实用性（是否对方案总结有帮助）

消息角色: {role}
消息内容: {content[:500]}

请只返回一个 0-1 之间的浮点数，不要其他解释。例如：0.85"""
    
    try:
        # 创建临时 Agent 进行打分
        scorer_agent = Agent(
            name="message_scorer",
            model=model,
            tools=[],
            instruction="你是一个对话消息重要性评估专家。请根据消息的实质性、完整性和实用性，返回0-1之间的重要性分数。",
            generate_content_config={"temperature": 0.3}
        )
        
        runner = Runner(
            agent=scorer_agent,
            session_service=get_session_service(),
            app_name="summary_agent"
        )
        
        # 创建临时会话进行打分
        temp_session_id = f"temp_score_{uuid4()}"
        score_content = Content(parts=[Part(text=scoring_prompt)])
        
        response_text = ""
        async for event in runner.run_async(
            user_id="system",
            session_id=temp_session_id,
            new_message=score_content
        ):
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts') and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            response_text += part.text
        
        # 尝试从响应中提取数字
        try:
            # 提取第一个数字（可能是分数）
            numbers = re.findall(r'0\.\d+|1\.0|0|1', response_text.strip())
            if numbers:
                score = float(numbers[0])
                score = max(0.0, min(1.0, score))  # 限制在 0-1 之间
                return score
        except Exception:
            pass
        
        # 如果无法解析，使用基础分数
        return base_score + length_score
        
    except Exception as e:
        logger.warning(f"消息打分失败，使用基础分数: {e}")
        return base_score + length_score


async def rank_messages_by_importance(
    messages: List[Dict[str, Any]],
    model: LiteLlm,
    top_k: int = 20
) -> List[Dict[str, Any]]:
    """
    对消息列表进行重要性排序，返回 Top-K
    
    Args:
        messages: 消息列表
        model: LLM 模型实例
        top_k: 返回前 K 条重要消息
    
    Returns:
        排序后的消息列表（按重要性降序）
    """
    logger.info(f"开始对 {len(messages)} 条消息进行重要性打分...")
    
    # 为每条消息打分
    scored_messages = []
    for msg in messages:
        score = await score_message_importance(msg, model)
        scored_messages.append({
            **msg,
            "importance_score": score
        })
        logger.debug(f"消息重要性打分: score={score:.2f}, role={msg.get('role')}, content_preview={msg.get('content', '')[:50]}...")
    
    # 按分数降序排序
    scored_messages.sort(key=lambda x: x.get("importance_score", 0), reverse=True)
    
    # 返回 Top-K
    top_messages = scored_messages[:top_k]
    logger.info(f"✓ 已筛选出 Top-{len(top_messages)} 重要消息（平均分数: {sum(m.get('importance_score', 0) for m in top_messages) / len(top_messages):.2f}）")
    
    return top_messages


async def generate_plan_content(
    messages: List[Dict[str, Any]],
    model: LiteLlm
) -> str:
    """
    使用 LLM 将重要消息总结为完整的 MD 方案
    
    Args:
        messages: 重要消息列表（已按重要性排序）
        model: LLM 模型实例
    
    Returns:
        str: Markdown 格式的方案文档
    """
    # 构建对话历史上下文
    conversation_context = ""
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "")
        content = msg.get("content", "")
        created_at = msg.get("created_at", "")
        
        role_name = "用户" if role == "user" else "助手" if role == "assistant" else role
        conversation_context += f"\n\n--- 对话 {i} ({role_name}) ---\n"
        if created_at:
            conversation_context += f"时间: {created_at}\n"
        conversation_context += f"{content}\n"
    
    # 构建总结提示词
    summary_prompt = f"""请根据以下对话历史，生成一个完整、结构化的 Markdown 方案文档。

要求：
1. 方案应包含：背景说明、目标、核心方案/建议、实施步骤、注意事项等部分
2. 使用标准的 Markdown 格式（标题、列表、代码块等）
3. 保持专业性和实用性
4. 提取对话中的关键信息和决策点
5. 方案应完整、可执行

对话历史（按重要性排序）：
{conversation_context}

请生成完整的 Markdown 方案文档："""
    
    logger.info(f"开始生成方案文档，使用 {len(messages)} 条重要消息...")
    
    try:
        # 创建总结 Agent
        summary_agent = Agent(
            name="summary_agent",
            model=model,
            tools=[],
            instruction="你是一个专业的方案总结专家。能够从对话历史中提取关键信息，生成结构清晰、内容完整的 Markdown 方案文档。",
            generate_content_config={
                "temperature": 0.7,
                "max_output_tokens": 8000  # 允许较长的输出
            }
        )
        
        runner = Runner(
            agent=summary_agent,
            session_service=get_session_service(),
            app_name="summary_agent"
        )
        
        # 创建临时会话进行总结
        temp_session_id = f"temp_summary_{uuid4()}"
        summary_content = Content(parts=[Part(text=summary_prompt)])
        
        plan_content = ""
        async for event in runner.run_async(
            user_id="system",
            session_id=temp_session_id,
            new_message=summary_content
        ):
            if hasattr(event, 'content') and event.content:
                if hasattr(event.content, 'parts') and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            plan_content += part.text
        
        if not plan_content.strip():
            logger.warning("LLM 未返回方案内容，生成默认模板")
            plan_content = f"""# 方案总结

## 背景
基于对话历史生成的方案总结。

## 核心内容
{conversation_context[:1000]}...

## 备注
本方案由 AI 自动生成，请根据实际情况进行调整。
"""
        
        logger.info(f"✓ 方案文档生成成功，长度: {len(plan_content)} 字符")
        return plan_content.strip()
        
    except Exception as e:
        logger.error(f"✗ 生成方案文档失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise


async def upload_plan_to_storage(
    plan_content: str,
    session_id: str
) -> Tuple[str, str]:
    """
    将方案文档上传到 MinIO 存储
    
    Args:
        plan_content: Markdown 格式的方案内容
        session_id: 会话ID（用于文件命名）
    
    Returns:
        Tuple[str, str]: (object_name, download_url)
    """
    logger.info(f"开始上传方案到 MinIO 存储...")
    
    try:
        storage_service = get_storage_service()
        
        # 生成文件名（包含时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"plan_summary_{session_id}_{timestamp}.md"
        
        # 将 Markdown 内容转换为字节流
        plan_bytes = plan_content.encode('utf-8')
        file_stream = BytesIO(plan_bytes)
        
        # 上传到 MinIO
        object_name, file_size = storage_service.upload_file(
            file_data=file_stream,
            original_filename=filename,
            content_type="text/markdown"
        )
        
        # 生成预签名下载链接（有效期 7 天）
        download_url = storage_service.get_presigned_url(
            object_name,
            expires=timedelta(days=7)
        )
        
        logger.info(f"✓ 方案上传成功: object={object_name}, size={file_size}, url={download_url[:50]}...")
        
        return object_name, download_url
        
    except Exception as e:
        logger.error(f"✗ 上传方案到存储失败: {type(e).__name__}: {str(e)}", exc_info=True)
        raise


async def generate_summary_plan(
    session_id: str,
    top_k: int = 20,
    max_messages: Optional[int] = None
) -> Dict[str, Any]:
    """
    一键总结为方案：读取对话历史，生成 MD 方案并上传到 OSS
    
    Args:
        session_id: 会话ID
        top_k: 选择前 K 条重要消息用于总结
        max_messages: 最大消息数限制（None 表示不限制）
    
    Returns:
        Dict[str, Any]: {
            "success": bool,
            "object_name": str,  # MinIO 对象名称
            "download_url": str,  # 下载链接
            "plan_content": str,  # 方案内容（可选）
            "messages_used": int,  # 使用的消息数量
            "error": str  # 错误信息（如果失败）
        }
    """
    logger.info(f"开始生成方案总结: session_id={session_id}, top_k={top_k}")
    
    try:
        # 1. 读取对话历史
        chat_histories = ChatService.get_chat_history(session_id, limit=max_messages)
        
        if not chat_histories:
            return {
                "success": False,
                "error": "该会话没有对话历史记录"
            }
        
        logger.info(f"✓ 读取到 {len(chat_histories)} 条对话历史记录")
        
        # 2. 提取消息内容（从 ChatHistory 获取关联的 ChatMessage）
        from models.sql import ChatSession, ChatMessage
        from core.db import SessionLocal
        
        db = SessionLocal()
        try:
            messages = []
            
            # 从 ChatHistory 的关系对象获取消息（如果已加载）
            for history in chat_histories:
                # 尝试通过关系对象获取（如果已加载）
                if hasattr(history, 'user_message') and history.user_message:
                    user_msg = history.user_message
                    messages.append({
                        "role": user_msg.role,
                        "content": user_msg.content,
                        "created_at": user_msg.created_at.isoformat() if user_msg.created_at else "",
                        "importance_score": 0.0
                    })
                elif history.user_message_id:
                    # 从数据库查询
                    user_msg = db.query(ChatMessage).filter(
                        ChatMessage.id == history.user_message_id
                    ).first()
                    if user_msg:
                        messages.append({
                            "role": user_msg.role,
                            "content": user_msg.content,
                            "created_at": user_msg.created_at.isoformat() if user_msg.created_at else "",
                            "importance_score": 0.0
                        })
                
                # 获取助手消息
                if hasattr(history, 'assistant_message') and history.assistant_message:
                    assistant_msg = history.assistant_message
                    messages.append({
                        "role": assistant_msg.role,
                        "content": assistant_msg.content,
                        "created_at": assistant_msg.created_at.isoformat() if assistant_msg.created_at else "",
                        "importance_score": 0.0
                    })
                elif history.assistant_message_id:
                    # 从数据库查询
                    assistant_msg = db.query(ChatMessage).filter(
                        ChatMessage.id == history.assistant_message_id
                    ).first()
                    if assistant_msg:
                        messages.append({
                            "role": assistant_msg.role,
                            "content": assistant_msg.content,
                            "created_at": assistant_msg.created_at.isoformat() if assistant_msg.created_at else "",
                            "importance_score": 0.0
                        })
            
            # 如果从 ChatHistory 关系对象没有获取到消息，回退到直接从 ChatMessage 表读取
            if not messages:
                logger.warning("从 ChatHistory 关系对象未获取到消息，回退到直接查询 ChatMessage 表")
                chat_session = db.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                if not chat_session:
                    return {
                        "success": False,
                        "error": "会话不存在"
                    }
                
                chat_messages = db.query(ChatMessage).filter(
                    ChatMessage.session_id == chat_session.id,
                    ChatMessage.role.in_(["user", "assistant"])
                ).order_by(ChatMessage.created_at.asc()).all()
                
                messages = [{
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else "",
                    "importance_score": 0.0
                } for msg in chat_messages]
                
        except Exception as e:
            logger.error(f"提取消息内容失败: {e}", exc_info=True)
            db.rollback()
            # 回退方案：直接从 ChatMessage 表读取
            try:
                chat_session = db.query(ChatSession).filter(
                    ChatSession.session_id == session_id
                ).first()
                if not chat_session:
                    return {
                        "success": False,
                        "error": "会话不存在"
                    }
                
                chat_messages = db.query(ChatMessage).filter(
                    ChatMessage.session_id == chat_session.id,
                    ChatMessage.role.in_(["user", "assistant"])
                ).order_by(ChatMessage.created_at.asc()).all()
                
                messages = [{
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else "",
                    "importance_score": 0.0
                } for msg in chat_messages]
            except Exception as e2:
                logger.error(f"回退方案也失败: {e2}", exc_info=True)
                return {
                    "success": False,
                    "error": f"提取消息失败: {str(e2)}"
                }
        finally:
            db.close()
        
        if not messages:
            return {
                "success": False,
                "error": "未找到可用的对话消息"
            }
        
        logger.info(f"✓ 提取到 {len(messages)} 条消息")
        
        # 3. 初始化 LLM 模型
        model = LiteLlm(
            model="openai/" + settings.DEFAULT_LLM_MODEL,
            api_base=settings.QWEN_BASE_URL,
            api_key=settings.QWEN_API_KEY,
            custom_llm_provider="openai"
        )
        
        # 4. 对消息进行重要性打分和排序
        top_messages = await rank_messages_by_importance(messages, model, top_k=top_k)
        
        # 5. 生成方案文档
        plan_content = await generate_plan_content(top_messages, model)
        
        # 6. 上传到 OSS 存储
        object_name, download_url = await upload_plan_to_storage(plan_content, session_id)
        
        logger.info(f"✓ 方案总结生成完成: session_id={session_id}, object={object_name}")
        
        return {
            "success": True,
            "object_name": object_name,
            "download_url": download_url,
            "plan_content": plan_content[:500] + "..." if len(plan_content) > 500 else plan_content,  # 返回前500字符预览
            "messages_used": len(top_messages),
            "total_messages": len(messages)
        }
        
    except Exception as e:
        logger.error(f"✗ 生成方案总结失败: {type(e).__name__}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
