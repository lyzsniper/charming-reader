from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# 创建数据库引擎
try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # 自动检测连接是否有效
        echo=False  # 设置为 True 可以看到 SQL 语句
    )
    logger.info(f"数据库引擎创建成功: {settings.DATABASE_URL.split('@')[1]}")  # 隐藏密码
except Exception as e:
    logger.error(f"数据库引擎创建失败: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_db_connection():
    """
    测试数据库连接
    返回: (是否成功, 消息)
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("✓ 数据库连接测试成功")
        return True, "数据库连接正常"
    except Exception as e:
        logger.error(f"✗ 数据库连接测试失败: {e}")
        return False, str(e)

def check_tables_exist():
    """
    检查数据库表是否存在
    """
    from sqlalchemy import inspect
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            logger.warning("⚠ 数据库中没有表！请运行数据库迁移: alembic upgrade head")
            return False, []
        
        logger.info(f"✓ 发现 {len(tables)} 个表: {', '.join(tables)}")
        return True, tables
    except Exception as e:
        logger.error(f"✗ 检查表失败: {e}")
        return False, []

