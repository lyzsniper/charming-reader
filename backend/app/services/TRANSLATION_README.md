# 翻译服务使用说明

## 概述

翻译服务基于 [translators](https://github.com/UlionTse/translators) 库，提供多语言翻译功能。

## 支持的翻译服务提供商

- **google**: Google Translate（默认，推荐）
- **baidu**: 百度翻译
- **alibaba**: 阿里翻译
- **youdao**: 有道翻译
- **tencent**: 腾讯翻译
- **deepl**: DeepL（需要 API key）
- **bing**: Bing Translator
- **sogou**: 搜狗翻译

## API 端点

### 1. 翻译文本

**POST** `/translate`

**请求体：**
```json
{
  "text": "Hello, world!",
  "from_language": "auto",  // 可选，默认为 "auto"（自动检测）
  "to_language": "zh",      // 必需，目标语言代码
  "provider": "google"       // 可选，默认为 "google"
}
```

**响应：**
```json
{
  "original_text": "Hello, world!",
  "translated_text": "你好，世界！",
  "from_language": "auto",
  "to_language": "zh",
  "provider": "google",
  "success": true,
  "error": null
}
```

### 2. 批量翻译

**POST** `/translate/batch`

**请求体：**
```json
{
  "texts": ["Hello", "World", "Python"],
  "from_language": "auto",
  "to_language": "zh",
  "provider": "google"
}
```

**响应：**
```json
[
  {
    "original_text": "Hello",
    "translated_text": "你好",
    "from_language": "auto",
    "to_language": "zh",
    "provider": "google",
    "success": true
  },
  ...
]
```

### 3. 语言检测

**POST** `/translate/detect`

**请求体：**
```json
{
  "text": "Hello, world!",
  "provider": "google"
}
```

**响应：**
```json
{
  "text": "Hello, world!",
  "detected_language": "en",
  "provider": "google",
  "success": true,
  "error": null
}
```

### 4. 获取支持的翻译服务提供商

**GET** `/translate/providers`

**响应：**
```json
{
  "available": true,
  "providers": ["google", "baidu", "alibaba", "youdao", "tencent", "deepl", "bing", "sogou"],
  "default": "google"
}
```

## 常用语言代码

- `en`: 英语
- `zh` 或 `zh-CN`: 简体中文
- `zh-TW`: 繁体中文
- `ja`: 日语
- `ko`: 韩语
- `fr`: 法语
- `de`: 德语
- `es`: 西班牙语
- `ru`: 俄语
- `auto`: 自动检测

## 使用示例

### Python 代码示例

```python
from services.translation_service import TranslationService

# 单文本翻译
result = TranslationService.translate(
    text="Hello, world!",
    from_language="auto",
    to_language="zh",
    provider="google"
)

print(result["translated_text"])  # 输出: "你好，世界！"

# 批量翻译
results = TranslationService.batch_translate(
    texts=["Hello", "World"],
    from_language="en",
    to_language="zh",
    provider="baidu"
)

# 语言检测
detected = TranslationService.detect_language(
    text="Bonjour le monde",
    provider="google"
)
print(detected)  # 输出: "fr"
```

### cURL 示例

```bash
# 翻译文本
curl -X POST "http://localhost:18000/translate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "from_language": "auto",
    "to_language": "zh",
    "provider": "google"
  }'

# 批量翻译
curl -X POST "http://localhost:18000/translate/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Hello", "World"],
    "to_language": "zh"
  }'

# 语言检测
curl -X POST "http://localhost:18000/translate/detect" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Bonjour le monde"
  }'
```

## 注意事项

1. **网络连接**：翻译服务需要网络连接，某些服务可能在某些地区不可用
2. **频率限制**：某些翻译服务可能有请求频率限制，建议合理使用
3. **自动检测**：使用 `from_language="auto"` 时，翻译服务会自动检测源语言
4. **错误处理**：如果翻译失败，响应中的 `success` 字段为 `false`，`error` 字段包含错误信息

## 故障排除

1. **服务不可用**：确保已安装 `translators` 库：`pip install translators`
2. **网络错误**：检查网络连接和代理设置
3. **HTTP 429 错误**：请求过于频繁，请稍后重试
4. **服务不支持**：某些翻译服务可能在某些地区不可用，尝试更换其他服务提供商
