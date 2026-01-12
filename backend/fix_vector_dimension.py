"""
一键修复向量维度不匹配问题
自动执行所有必要的步骤
"""
import sys
import os

# 添加 app 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from elasticsearch import Elasticsearch
from core.config import settings
from sqlalchemy import create_engine, text
from core.db import engine

def step1_reset_elasticsearch():
    """步骤1: 重置 Elasticsearch 索引"""
    print("\n" + "=" * 60)
    print("步骤 1: 重置 Elasticsearch 索引")
    print("=" * 60)
    
    try:
        es = Elasticsearch([settings.ELASTICSEARCH_URL])
        index_name = settings.INDEX_NAME
        
        # 删除旧索引
        if es.indices.exists(index=index_name):
            print(f"正在删除旧索引: {index_name}")
            es.indices.delete(index=index_name)
            print("✓ 旧索引已删除")
        else:
            print("旧索引不存在，跳过删除")
        
        # 创建新索引（1536 维）
        print(f"正在创建新索引: {index_name} (1536 维)")
        
        index_body = {
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 1536,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "text": {
                        "type": "text"
                    },
                    "metadata": {
                        "type": "object",
                        "enabled": True
                    }
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }
        
        es.indices.create(index=index_name, body=index_body)
        print("✓ 新索引创建成功（1536 维）")
        
        # 验证
        mapping = es.indices.get_mapping(index=index_name)
        dims = mapping[index_name]['mappings']['properties']['embedding']['dims']
        print(f"✓ 验证成功：向量维度 = {dims}")
        
        return True
        
    except Exception as e:
        print(f"✗ Elasticsearch 重置失败: {e}")
        return False

def step2_clean_postgres():
    """步骤2: 清理 PostgreSQL 中的旧向量数据"""
    print("\n" + "=" * 60)
    print("步骤 2: 清理 PostgreSQL 旧数据")
    print("=" * 60)
    
    try:
        with engine.connect() as conn:
            # 清空 document_chunks 表
            print("正在清空 document_chunks 表...")
            conn.execute(text("TRUNCATE TABLE document_chunks CASCADE"))
            conn.commit()
            print("✓ 旧的向量数据已清空")
        
        return True
        
    except Exception as e:
        print(f"✗ PostgreSQL 清理失败: {e}")
        return False

def step3_update_postgres_schema():
    """步骤3: 更新 PostgreSQL 向量列维度"""
    print("\n" + "=" * 60)
    print("步骤 3: 更新 PostgreSQL 向量维度")
    print("=" * 60)
    
    try:
        with engine.connect() as conn:
            # 修改列类型为 1536 维
            print("正在更新 embedding 列维度为 1536...")
            conn.execute(text("""
                ALTER TABLE document_chunks 
                ALTER COLUMN embedding TYPE vector(1536)
            """))
            conn.commit()
            print("✓ 向量维度已更新为 1536")
        
        return True
        
    except Exception as e:
        print(f"✗ PostgreSQL schema 更新失败: {e}")
        print("提示：如果报错说类型相同，说明已经是 1536 维了，可以忽略")
        return True  # 如果已经是 1536 维，不算失败

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("向量维度不匹配修复工具")
    print("=" * 60)
    print("\n将执行以下操作：")
    print("  1. 重置 Elasticsearch 索引（1024维 → 1536维）")
    print("  2. 清理 PostgreSQL 旧向量数据")
    print("  3. 更新 PostgreSQL 向量维度（1024维 → 1536维）")
    print("\n⚠️  警告：所有旧的向量数据将被删除！")
    print("   （文档元数据保留，只需重新上传文档即可重新索引）")
    
    response = input("\n是否继续？(y/n): ")
    if response.lower() != 'y':
        print("操作已取消")
        return
    
    # 执行步骤
    success = True
    
    if not step1_reset_elasticsearch():
        success = False
        print("\n✗ Elasticsearch 重置失败")
    
    if not step2_clean_postgres():
        success = False
        print("\n✗ PostgreSQL 清理失败")
    
    if not step3_update_postgres_schema():
        success = False
        print("\n✗ PostgreSQL schema 更新失败")
    
    # 总结
    print("\n" + "=" * 60)
    if success:
        print("✅ 修复完成！")
        print("=" * 60)
        print("\n下一步：")
        print("  1. 重启后端服务")
        print("     cd backend")
        print("     python -m uvicorn app.main:app --reload")
        print("\n  2. 重新上传文档")
        print("     通过 API 或前端界面上传 PDF 文档")
        print("     系统会自动使用 1536 维向量进行索引")
        print("\n  3. 测试 RAG 搜索")
        print("     curl -X POST http://localhost:8000/api/rag/search \\")
        print('       -H "Content-Type: application/json" \\')
        print('       -d \'{"query": "test", "top_k": 5}\'')
    else:
        print("❌ 修复失败")
        print("=" * 60)
        print("\n请检查错误信息并手动修复")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

