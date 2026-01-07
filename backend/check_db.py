"""
数据库连接诊断脚本
快速检查数据库连接和表状态
"""
import sys
import os

# 添加项目路径到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from sqlalchemy import create_engine, text, inspect
import traceback


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_connection():
    """检查数据库连接"""
    print_section("1. 数据库连接测试")
    
    # 显示连接信息（隐藏密码）
    db_url = settings.DATABASE_URL
    safe_url = db_url.split('@')[1] if '@' in db_url else db_url
    print(f"数据库地址: {safe_url}")
    
    try:
        engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✓ 连接成功")
            print(f"PostgreSQL 版本: {version[:50]}...")
            return engine
    except Exception as e:
        print(f"✗ 连接失败")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print("\n可能的原因:")
        print("  1. PostgreSQL 服务未启动")
        print("  2. 端口号错误（检查是否是 35432）")
        print("  3. 数据库名称错误（检查是否是 paperagent）")
        print("  4. 用户名或密码错误")
        print("  5. 防火墙阻止连接")
        return None


def check_database_exists(engine):
    """检查数据库是否存在"""
    print_section("2. 数据库状态")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database()"))
            db_name = result.fetchone()[0]
            print(f"✓ 当前数据库: {db_name}")
            
            # 检查数据库大小
            result = conn.execute(text(
                "SELECT pg_size_pretty(pg_database_size(current_database()))"
            ))
            db_size = result.fetchone()[0]
            print(f"数据库大小: {db_size}")
            
            return True
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        return False


def check_extensions(engine):
    """检查数据库扩展"""
    print_section("3. 数据库扩展")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT extname, extversion FROM pg_extension ORDER BY extname"
            ))
            extensions = result.fetchall()
            
            if extensions:
                print(f"已安装的扩展:")
                for ext_name, ext_version in extensions:
                    print(f"  - {ext_name} (版本 {ext_version})")
                
                # 检查 pgvector
                has_vector = any(ext[0] == 'vector' for ext in extensions)
                if has_vector:
                    print("\n✓ pgvector 扩展已安装")
                else:
                    print("\n⚠ pgvector 扩展未安装")
                    print("如需使用向量功能，请运行:")
                    print("  CREATE EXTENSION IF NOT EXISTS vector;")
            else:
                print("没有安装任何扩展")
            
            return True
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        return False


def check_tables(engine):
    """检查数据库表"""
    print_section("4. 数据库表")
    
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if not tables:
            print("✗ 数据库中没有表！")
            print("\n需要运行数据库迁移来创建表:")
            print("  cd backend")
            print("  alembic upgrade head")
            print("\n或者运行初始化脚本:")
            print("  python init_db.py")
            return False
        
        print(f"✓ 发现 {len(tables)} 个表:\n")
        
        expected_tables = [
            'knowledge_bases',
            'documents', 
            'document_chunks',
            'document_knowledge_base',
            'model_configurations',
            'alembic_version'
        ]
        
        for table in sorted(tables):
            status = "✓" if table in expected_tables else "?"
            print(f"  {status} {table}")
            
            # 显示表的行数
            try:
                with engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"      ({count} 行)")
            except:
                pass
        
        # 检查缺失的表
        missing = set(expected_tables) - set(tables)
        if missing:
            print(f"\n⚠ 缺少预期的表: {', '.join(missing)}")
            print("请运行数据库迁移: alembic upgrade head")
        
        return True
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        traceback.print_exc()
        return False


def check_alembic_version(engine):
    """检查 Alembic 迁移版本"""
    print_section("5. 数据库迁移状态")
    
    try:
        with engine.connect() as conn:
            # 检查 alembic_version 表是否存在
            result = conn.execute(text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                "WHERE table_name = 'alembic_version')"
            ))
            has_alembic = result.fetchone()[0]
            
            if has_alembic:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                version = result.fetchone()
                if version:
                    print(f"✓ 当前迁移版本: {version[0]}")
                else:
                    print("⚠ alembic_version 表存在但为空")
            else:
                print("✗ 未找到 alembic_version 表")
                print("这表示从未运行过数据库迁移")
                print("\n请运行:")
                print("  cd backend")
                print("  alembic upgrade head")
            
            return has_alembic
    except Exception as e:
        print(f"✗ 检查失败: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  PaperAgent 数据库诊断工具")
    print("=" * 60)
    
    # 1. 检查连接
    engine = check_connection()
    if not engine:
        print("\n" + "=" * 60)
        print("诊断失败：无法连接到数据库")
        print("=" * 60)
        sys.exit(1)
    
    # 2. 检查数据库
    check_database_exists(engine)
    
    # 3. 检查扩展
    check_extensions(engine)
    
    # 4. 检查表
    has_tables = check_tables(engine)
    
    # 5. 检查迁移版本
    check_alembic_version(engine)
    
    # 总结
    print_section("诊断总结")
    
    if has_tables:
        print("✓ 数据库状态正常")
        print("\n可以启动应用:")
        print("  cd backend/app")
        print("  python main.py")
    else:
        print("⚠ 数据库需要初始化")
        print("\n下一步操作:")
        print("  1. 运行: python init_db.py")
        print("  2. 或者: cd backend && alembic upgrade head")
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()

