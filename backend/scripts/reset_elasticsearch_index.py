"""
重置 Elasticsearch 索引
删除旧索引并创建新的 1536 维索引
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from elasticsearch import Elasticsearch
from core.config import settings

def reset_index():
    """删除并重新创建索引"""
    es = Elasticsearch([settings.ELASTICSEARCH_URL])
    
    index_name = settings.INDEX_NAME
    
    # 1. 删除旧索引（如果存在）
    if es.indices.exists(index=index_name):
        print(f"删除旧索引: {index_name}")
        es.indices.delete(index=index_name)
        print("✓ 旧索引已删除")
    
    # 2. 创建新索引（1536 维）
    print(f"创建新索引: {index_name} (1536 维)")
    
    index_body = {
        "mappings": {
            "properties": {
                "embedding": {
                    "type": "dense_vector",
                    "dims": 1536,  # 使用 1536 维（text-embedding-v1/v2/v3）
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
    
    # 3. 验证
    mapping = es.indices.get_mapping(index=index_name)
    dims = mapping[index_name]['mappings']['properties']['embedding']['dims']
    print(f"✓ 验证成功：向量维度 = {dims}")
    
    print("\n" + "=" * 60)
    print("索引重置完成！")
    print("=" * 60)
    print("\n下一步：重新上传并索引所有文档")
    print("  1. 访问 http://localhost:8000/api/documents")
    print("  2. 查看所有文档")
    print("  3. 重新上传需要的文档")

if __name__ == "__main__":
    reset_index()

