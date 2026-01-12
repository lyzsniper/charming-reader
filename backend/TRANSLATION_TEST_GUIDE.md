# 翻译功能测试指南

## 1. 测试翻译服务

### 运行测试脚本

```bash
# 在项目根目录运行
python backend/test_translation_service.py
```

### 测试内容

测试脚本包含以下测试用例：

1. **服务可用性测试** - 检查 translators 库是否已安装
2. **单文本翻译测试** - 测试基本翻译功能
3. **批量翻译测试** - 测试批量翻译多个文本
4. **语言检测测试** - 测试语言自动检测（如果支持）
5. **支持的提供商测试** - 列出所有支持的翻译服务
6. **错误处理测试** - 测试错误情况的处理

### 预期结果

如果所有测试通过，应该看到：
```
测试结果汇总
============================================================
✓ 通过: 服务可用性
✓ 通过: 单文本翻译
✓ 通过: 批量翻译
✓ 通过: 语言检测
✓ 通过: 支持的提供商
✓ 通过: 错误处理

总计: 6/6 通过
```

## 2. 测试 API 端点

### 翻译文本 API

```bash
curl -X POST "http://localhost:18000/translate" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "from_language": "auto",
    "to_language": "zh",
    "provider": "google"
  }'
```

### 翻译文档 API

```bash
curl -X POST "http://localhost:18000/translate/document" \
  -F "file=@/path/to/document.pdf" \
  -F "from_language=auto" \
  -F "to_language=en" \
  -F "provider=google"
```

## 3. 前端功能测试

### 测试步骤

1. **启动前端和后端服务**
   ```bash
   # 后端
   cd backend
   uvicorn app.main:app --reload --port 18000
   
   # 前端
   cd frontend
   npm run dev
   ```

2. **上传文档**
   - 在首页或对话界面上传一个 PDF 文件

3. **打开文件预览**
   - 在右侧 Context Panel 中查看上传的 PDF

4. **使用翻译功能**
   - 点击 PDF View 标签页中的"翻译"按钮
   - 选择源语言和目标语言
   - 点击"开始翻译"
   - 等待翻译完成

5. **查看翻译结果**
   - 翻译完成后，会自动切换到"翻译结果"标签页
   - 可以查看翻译后的 Markdown 格式文档
   - 点击"下载"按钮可以下载翻译后的文档

### 功能特性

- ✅ 支持多种文档格式（PDF、DOCX、TXT 等）
- ✅ 自动语言检测
- ✅ 批量翻译（文档分块翻译）
- ✅ 翻译结果预览（Markdown 格式）
- ✅ 下载翻译后的文档
- ✅ 错误处理和加载状态显示

## 4. 常见问题

### Q: 翻译服务不可用

**A:** 确保已安装 translators 库：
```bash
pip install translators==5.7.0
```

### Q: 翻译速度慢

**A:** 
- 大文档会被分块翻译，需要一定时间
- 可以尝试使用不同的翻译服务提供商
- 检查网络连接

### Q: 翻译结果不准确

**A:**
- 尝试使用不同的翻译服务提供商（google、baidu、alibaba 等）
- 确保源语言选择正确
- 某些专业术语可能需要人工校对

### Q: 文档翻译失败

**A:**
- 检查文档格式是否支持
- 确保文档内容不为空
- 查看后端日志获取详细错误信息

## 5. 支持的语言

常用语言代码：
- `en`: 英语
- `zh` 或 `zh-CN`: 简体中文
- `zh-TW`: 繁体中文
- `ja`: 日语
- `ko`: 韩语
- `fr`: 法语
- `de`: 德语
- `es`: 西班牙语
- `auto`: 自动检测

## 6. 支持的翻译服务提供商

- **google**: Google Translate（默认，推荐）
- **baidu**: 百度翻译
- **alibaba**: 阿里翻译
- **youdao**: 有道翻译
- **tencent**: 腾讯翻译
- **deepl**: DeepL（需要 API key）
- **bing**: Bing Translator
- **sogou**: 搜狗翻译
