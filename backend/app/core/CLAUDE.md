# Core - 核心模块

[根目录](../../../CLAUDE.md) > [backend](../../CLAUDE.md) > [app](../CLAUDE.md) > **core**

## 模块职责

Core 模块是 PaperAgent 的基础支撑模块，提供配置管理、数据库连接、日志记录、异常处理等核心功能。该模块采用模块化设计，确保系统的稳定性和可维护性。

## 入口与启动

### 主要入口文件
- `config.py` - 应用配置管理
- `db.py` - 数据库连接和会话管理
- `logger.py` - 日志配置和管理
- `exceptions.py` - 自定义异常处理

### 初始化流程
```python
# 应用启动时自动加载
from core.config import settings
from core.db import get_db, test_db_connection
from core.logger import get_logger
from core.exceptions import global_exception_handler
```

## 对外接口

### 配置管理接口
```python
from core.config import settings

# 获取配置
database_url = settings.DATABASE_URL
api_key = settings.OPENAI_API_KEY
embedding_model = settings.EMBEDDING_MODEL

# 技能系统配置
skills_dir = settings.SKILLS_DIR
auto_activation = settings.SKILLS_AUTO_ACTIVATION
max_concurrent = settings.SKILLS_MAX_CONCURRENT
```

### 数据库接口
```python
from core.db import get_db, test_db_connection, check_tables_exist

# 获取数据库会话
db_session = next(get_db())

# 测试连接
success, message = test_db_connection()

# 检查表是否存在
has_tables, tables = check_tables_exist()
```

### 日志接口
```python
from core.logger import get_logger

# 获取日志器
logger = get_logger(__name__)

# 使用日志
logger.info("应用启动")
logger.error("数据库连接失败", exc_info=True)
logger.debug("调试信息")
```

### 异常处理接口
```python
from core.exceptions import BaseAPIException, global_exception_handler

# 自定义异常
raise BaseAPIException("操作失败", detail={"code": "INVALID_INPUT"})

# 全局异常处理器
app.add_exception_handler(BaseAPIException, global_exception_handler)
```

## 关键依赖与配置

### 配置类定义
```python
class Settings(BaseSettings):
    # 数据库配置
    DATABASE_URL: str = "postgresql://user:pass@localhost:5432/paperagent"

    # Elasticsearch配置
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    INDEX_NAME: str = "paper_index"

    # MinIO对象存储
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "paperagent"
    MINIO_SECRET_KEY: str = "paperagent123"
    MINIO_BUCKET: str = "paperagent-files"

    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    QWEN_API_KEY: Optional[str] = "sk-xxx"
    GLM_API_KEY: Optional[str] = "sk-xxx"

    # 模型配置
    DEFAULT_LLM_MODEL: str = "qwen-flash-2025-07-28"
    EMBEDDING_MODEL: str = "text-embedding-v4"

    # 技能配置
    SKILLS_DIR: str = ".claude/skills"
    SKILLS_AUTO_ACTIVATION: bool = True
    SKILLS_MAX_CONCURRENT: int = 3

    # GitHub MCP配置
    GITHUB_MCP_URL: str = "https://api.githubcopilot.com/mcp/"
    GITHUB_MCP_TOKEN: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"
```

### 数据库配置
```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    poolclass=StaticPool,
    pool_pre_ping=True,
    pool_recycle=300,
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()
```

### 日志配置
```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """配置日志系统"""
    # 创建日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 文件处理器
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
```

## 数据模型

### 配置模型
- `Settings` - 应用配置类（继承自BaseSettings）
- 环境变量自动映射
- 类型验证和默认值

### 数据库模型基类
- `Base` - SQLAlchemy基类
- 提供通用字段和方法
- 支持UUID主键

### 异常类层次
```
BaseException
└── BaseAPIException
    ├── ValidationError
    ├── NotFoundError
    ├── UnauthorizedError
    └── InternalServerError
```

## 测试与质量

### 配置测试
- 环境变量测试
- 配置验证测试
- 默认值测试

### 数据库测试
- 连接池测试
- 会话管理测试
- 迁移测试

### 日志测试
- 日志级别测试
- 格式化测试
- 文件输出测试

## 常见问题 (FAQ)

### Q: 如何添加新的配置项？
A:
1. 在 `Settings` 类中添加新的字段
2. 添加类型注解
3. 提供合适的默认值
4. 在 `Config` 类中配置环境变量文件

### Q: 数据库连接失败怎么办？
A: 检查以下项目：
1. 数据库服务是否运行
2. 连接字符串是否正确
3. 用户权限是否足够
4. 网络连接是否正常
5. 使用 `test_db_connection()` 进行诊断

### Q: 如何调整日志级别？
A: 通过环境变量 `LOG_LEVEL` 控制：
```python
# 在 .env 文件中
LOG_LEVEL=DEBUG

# 或者在代码中
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

### Q: 自定义异常如何使用？
A:
```python
from core.exceptions import BaseAPIException

# 抛出自定义异常
raise BaseAPIException(
    message="操作失败",
    detail={"code": "INVALID_INPUT", "field": "email"},
    status_code=400
)

# 在API路由中处理
try:
    # 业务逻辑
except ValueError as e:
    raise BaseAPIException("输入验证失败", detail=str(e))
```

## 相关文件清单

### 核心文件
- `config.py` - 配置管理
- `db.py` - 数据库连接
- `logger.py` - 日志系统
- `exceptions.py` - 异常处理
- `config_validator.py` - 配置验证

### 工具文件
- `utils/` - 工具函数
  - `retry.py` - 重试机制

### 配置示例
- `../../.env.example` - 环境变量示例

## 变更记录 (Changelog)

### 2026-01-17
- ✅ 完成模块级文档初始化
- ✅ 添加导航面包屑
- ✅ 更新核心模块接口文档
- ✅ 完善配置说明

---

*本文档由 Claude AI 助手自动生成，最后更新时间：2026-01-17 16:02:32*