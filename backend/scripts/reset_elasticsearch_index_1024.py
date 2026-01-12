"""
重置 Elasticsearch 索引为 1024 维
适配 text-embedding-v4 默认维度
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from elasticsearch import Elasticsearch
from core.config import settings

def reset_index():
    """删除并重新创建索引（1024 维）"""
    es = Elasticsearch([settings.ELASTICSEARCH_URL])
    
    index_name = settings.INDEX_NAME
    
    # 1. 删除旧索引（如果存在）
    if es.indices.exists(index=index_name):
        print(f"删除旧索引: {index_name}")
        es.indices.delete(index=index_name)
        print("✓ 旧索引已删除")
    
    # 2. 创建新索引（1024 维）
    print(f"创建新索引: {index_name} (1024 维)")
    
    index_body = {
        "mappings": {
            "properties": {
                "embedding": {
                    "type": "dense_vector",
                    "dims": 1024,  # text-embedding-v4 默认维度
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
    print("✓ 新索引创建成功（1024 维）")
    
    # 3. 验证
    mapping = es.indices.get_mapping(index=index_name)
    dims = mapping[index_name]['mappings']['properties']['embedding']['dims']
    print(f"✓ 验证成功：向量维度 = {dims}")
    
    print("\n" + "=" * 60)
    print("索引重置完成！")
    print("=" * 60)
    print("\n配置：text-embedding-v4 (1024 维)")
    print("\n下一步：")
    print("  1. 运行数据库迁移")
    print("     cd backend")
    print("     alembic upgrade head")
    print("\n  2. 重启服务")
    print("     python -m uvicorn app.main:app --reload")
    print("\n  3. 重新上传文档")

if __name__ == "__main__":
    reset_index()

