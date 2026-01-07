from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from api.endpoints import router as api_router
from rag.router import router as rag_router
from core.logger import get_logger

# 配置日志
logger = get_logger(__name__)

app = FastAPI(title="PaperAgent API")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)
app.include_router(rag_router)

logger.info("PaperAgent API 启动完成")

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    from core.db import test_db_connection, check_tables_exist
    
    logger.info("=" * 60)
    logger.info("PaperAgent API 正在启动...")
    logger.info("=" * 60)
    
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
