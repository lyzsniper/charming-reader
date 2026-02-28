from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from api.endpoints import router as api_router
from api.agent_skills_center import router as skills_center_router
from rag.router import router as rag_router
from core.logger import get_logger
from core.exceptions import global_exception_handler, BaseAPIException

# 配置日志
logger = get_logger(__name__)

app = FastAPI(
    title="PaperAgent API",
    version="1.0.0",
    description="学术论文智能分析助手 API",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册全局异常处理器
app.add_exception_handler(BaseAPIException, global_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

# 注册路由
app.include_router(api_router)
app.include_router(rag_router)
app.include_router(skills_center_router, prefix="/api", tags=["Agent Skills Center"])

logger.info("PaperAgent API 启动完成")
logger.info("Agent Skills Center API 已注册 @ /api/*")

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    from core.db import test_db_connection, check_tables_exist
    from core.config_validator import check_config_on_startup
    
    logger.info("=" * 60)
    logger.info("PaperAgent API 正在启动...")
    logger.info("=" * 60)
    
    # 验证配置
    logger.info("正在验证配置...")
    check_config_on_startup()
    
    # 测试数据库连接
    logger.info("正在测试数据库连接...")
    success, message = test_db_connection()
    if not success:
        logger.error(f"数据库连接失败: {message}")
        logger.error("请检查数据库配置和服务是否正常运行")
        return
    
    # 检查表是否存在
    logger.info("正在检查数据库表...")
    has_tables, tables = check_tables_exist()
    if not has_tables:
        logger.warning("=" * 60)
        logger.warning("⚠ 数据库表不存在！")
        logger.warning("请在 backend 目录下运行以下命令创建表：")
        logger.warning("  alembic upgrade head")
        logger.warning("=" * 60)
    else:
        logger.info(f"✓ 数据库表检查完成，共 {len(tables)} 个表")
    
    logger.info("=" * 60)
    logger.info("✓ PaperAgent API 启动完成")
    logger.info("=" * 60)

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("=" * 60)
    logger.info("PaperAgent API 正在关闭...")
    logger.info("=" * 60)

@app.get("/")
async def root():
    logger.debug("访问根路径")
    return {"message": "Welcome to PaperAgent API"}

if __name__ == "__main__":
    logger.info("启动 Uvicorn 服务器，监听 0.0.0.0:18000")
    uvicorn.run("main:app", host="0.0.0.0", port=18000, reload=True)
