"""
数据库初始化脚本
运行此脚本来初始化数据库和创建表
"""
import sys
import os

# 添加项目路径到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.logger import get_logger
from app.core.db import engine, test_db_connection, check_tables_exist
from sqlalchemy import text

logger = get_logger(__name__)


def check_database_exists():
    """检查数据库是否存在"""
    logger.info("检查数据库连接...")
    success, message = test_db_connection()
    
    if not success:
        logger.error("=" * 60)
        logger.error("✗ 数据库连接失败！")
        logger.error(f"错误信息: {message}")
        logger.error("=" * 60)
        logger.error("\n请检查以下内容：")
        logger.error("1. PostgreSQL 服务是否正在运行")
        logger.error("2. 数据库配置是否正确 (backend/app/core/config.py)")
        logger.error("   当前配置: postgresql://jensenlyz:****@localhost:35432/paperagent")
        logger.error("3. 数据库 'paperagent' 是否已创建")
        logger.error("\n创建数据库的 SQL 命令：")
        logger.error("   CREATE DATABASE paperagent;")
        logger.error("   CREATE EXTENSION IF NOT EXISTS vector;  -- 如果使用 pgvector")
        return False
    
    logger.info("✓ 数据库连接成功")
    return True


def check_pgvector_extension():
    """检查 pgvector 扩展是否已安装"""
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            )
            if result.fetchone():
                logger.info("✓ pgvector 扩展已安装")
                return True
            else:
                logger.warning("⚠ pgvector 扩展未安装")
                logger.warning("请在数据库中运行: CREATE EXTENSION IF NOT EXISTS vector;")
                return False
    except Exception as e:
        logger.error(f"检查 pgvector 扩展失败: {e}")
        return False


def run_migrations():
    """运行数据库迁移"""
    logger.info("=" * 60)
    logger.info("开始运行数据库迁移...")
    logger.info("=" * 60)
    
    import subprocess
    
    try:
        # 运行 alembic upgrade head
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=os.path.dirname(__file__),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            logger.info("✓ 数据库迁移成功")
            logger.info(result.stdout)
            return True
        else:
            logger.error("✗ 数据库迁移失败")
            logger.error(result.stderr)
            return False
    except FileNotFoundError:
        logger.error("✗ 找不到 alembic 命令")
        logger.error("请确保已安装 alembic: pip install alembic")
        return False
    except Exception as e:
        logger.error(f"✗ 运行迁移时发生错误: {e}")
        return False


def verify_tables():
    """验证表是否创建成功"""
    logger.info("=" * 60)
    logger.info("验证数据库表...")
    logger.info("=" * 60)
    
    has_tables, tables = check_tables_exist()
    
    if has_tables and tables:
        logger.info(f"✓ 成功创建 {len(tables)} 个表:")
        for table in sorted(tables):
            logger.info(f"  - {table}")
        return True
    else:
        logger.error("✗ 没有发现任何表")
        return False


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("PaperAgent 数据库初始化")
    logger.info("=" * 60)
    
    # 1. 检查数据库连接
    if not check_database_exists():
        logger.error("\n初始化失败：无法连接到数据库")
        sys.exit(1)
    
    # 2. 检查 pgvector 扩展
    check_pgvector_extension()
    
    # 3. 检查是否已有表
    has_tables, tables = check_tables_exist()
    if has_tables:
        logger.warning("\n⚠ 数据库中已经存在表")
        logger.warning(f"发现的表: {', '.join(tables)}")
        
        response = input("\n是否要重新运行迁移？(y/N): ").strip().lower()
        if response != 'y':
            logger.info("取消操作")
            return
    
    # 4. 运行迁移
    if not run_migrations():
        logger.error("\n初始化失败：迁移执行失败")
        sys.exit(1)
    
    # 5. 验证表
    if not verify_tables():
        logger.error("\n初始化失败：表验证失败")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("✓ 数据库初始化完成！")
    logger.info("=" * 60)
    logger.info("\n现在可以启动应用了:")
    logger.info("  python app/main.py")
    logger.info("或者:")
    logger.info("  uvicorn app.main:app --host 0.0.0.0 --port 18000 --reload")


if __name__ == "__main__":
    main()

