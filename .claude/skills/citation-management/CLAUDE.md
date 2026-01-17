# Citation Management Skill - 引文管理技能

[根目录](../../../CLAUDE.md) > [.claude/skills](../CLAUDE.md) > **citation-management**

## 技能职责

Citation Management Skill 是 PaperAgent 的引文格式化和管理技能，能够自动识别、提取和格式化学术文献的引用信息。该技能支持多种主流引用格式（APA、Chicago、IEEE等），帮助用户快速生成规范的参考文献列表。

## 技能元数据

```yaml
---
name: citation-management
description: 自动识别、提取和格式化学术文献引用，支持多种引用格式
triggers:
  - citation management
  - 引文管理
  - reference formatting
  - 参考文献格式化
  - bibliography
  - 文献目录
  - apa format
  - apa格式
  - ieee citation
  - ieee引文
version: 1.0.0
---
```

## 核心能力

### 1. 引文识别与提取

**自动识别引文**
- 从文本中自动检测引文标记
- 识别不同的引文格式（数字编码、作者年份等）
- 提取引文的核心信息（作者、年份、标题等）

**引文解析**
- 解析复杂的引文结构
- 处理多作者、机构作者情况
- 识别期刊名称、会议名称、出版社信息

**信息标准化**
- 统一作者姓名格式
- 标准化期刊名称缩写
- 规范化日期格式

### 2. 多格式支持

**APA 格式 (第7版)**
```text
期刊文章：
Author, A. A. (Year). Title of article. Title of Periodical, volume(issue), pages. https://doi.org/xxxxx

书籍：
Author, A. A. (Year). Title of work. Publisher Name.

网页：
Author, A. A. (Year, Month Day). Title of page. Site Name. URL
```

**Chicago 格式 (第17版)**
```text
注释-书目格式：
Author First Name Last Name, "Article Title," Journal Title Volume, no. Issue (Year): Page.

作者-日期格式：
Author Last Name, First Name. Year. "Article Title." Journal Volume, no. Issue.
```

**IEEE 格式**
```text
期刊文章：
[1] J. K. Author, "Title of paper," Abbrev. Title of Journal, vol. x, no. x, pp. xxx-xxx, Abbrev. Month, year.

会议论文：
[2] J. K. Author, "Title of paper," in Proc. [Abbrev. Conf. Name], Location, year, pp. xxx-xxx.
```

### 3. 引文生成与管理

**批量处理**
- 同时处理多个引文
- 保持引文编号连续性
- 自动生成参考文献列表

**交叉引用**
- 自动生成文内引用标记
- 维护引用和参考文献的对应关系
- 支持脚注和尾注格式

**格式转换**
- 在不同引用格式之间转换
- 保留引文核心信息
- 确保转换后的格式正确

### 4. 引文质量检查

**信息验证**
- 检查必需字段是否完整
- 验证DOI和URL的有效性
- 检查作者姓名拼写

**格式一致性**
- 确保所有引文格式统一
- 检查标点符号使用
- 验证斜体、粗体等格式标记

**常见错误检测**
- 检测缺失的页码信息
- 识别日期格式错误
- 发现缩写不一致问题

## 输出格式

### 引文格式示例

**APA 格式输出**
```text
Journal Articles:
Smith, J. D., & Johnson, M. L. (2023). The impact of artificial intelligence on research productivity. Journal of Scientific Computing, 45(3), 123-145. https://doi.org/10.1234/jsc.2023.1234

Books:
Williams, R. T. (2022). Advanced research methodologies: A comprehensive guide. Academic Press.

Conference Papers:
Chen, L., & Wang, H. (2024). Novel approaches to literature review automation. In Proceedings of the International Conference on Research Methods (pp. 78-92). IEEE.
```

**Chicago 格式输出**
```text
Author-Date Format:
Smith, John D., and Mary L. Johnson. 2023. "The Impact of Artificial Intelligence on Research Productivity." Journal of Scientific Computing 45 (3): 123-45.

Notes-Bibliography Format:
Smith, John D., and Mary L. Johnson. "The Impact of Artificial Intelligence on Research Productivity." Journal of Scientific Computing 45, no. 3 (2023): 123-45.
```

**IEEE 格式输出**
```text
[1] J. D. Smith and M. L. Johnson, "The impact of artificial intelligence on research productivity," Journal of Scientific Computing, vol. 45, no. 3, pp. 123-145, 2023.

[2] L. Chen and H. Wang, "Novel approaches to literature review automation," in Proc. Int. Conf. Res. Methods, 2024, pp. 78-92.
```

### 参考文献列表
```text
## 参考文献

### APA 格式
Smith, J. D., & Johnson, M. L. (2023). The impact of artificial intelligence on research productivity. Journal of Scientific Computing, 45(3), 123-145. https://doi.org/10.1234/jsc.2023.1234

Williams, R. T. (2022). Advanced research methodologies: A comprehensive guide. Academic Press.

Chen, L., & Wang, H. (2024). Novel approaches to literature review automation. In Proceedings of the International Conference on Research Methods (pp. 78-92). IEEE.

### Chicago 格式
Smith, John D., and Mary L. Johnson. 2023. "The Impact of Artificial Intelligence on Research Productivity." Journal of Scientific Computing 45 (3): 123-45.

Williams, Robert T. 2022. Advanced Research Methodologies: A Comprehensive Guide. Academic Press.

Chen, Li, and Hong Wang. 2024. "Novel Approaches to Literature Review Automation." In Proceedings of the International Conference on Research Methods, 78-92.

### IEEE 格式
[1] J. D. Smith and M. L. Johnson, "The impact of artificial intelligence on research productivity," Journal of Scientific Computing, vol. 45, no. 3, pp. 123-145, 2023.

[2] R. T. Williams, "Advanced research methodologies: A comprehensive guide," Academic Press, 2022.

[3] L. Chen and H. Wang, "Novel approaches to literature review automation," in Proc. Int. Conf. Res. Methods, 2024, pp. 78-92.
```

## 使用指南

### 何时使用此技能
- 需要格式化参考文献列表
- 转换引文格式
- 批量处理大量引文
- 检查引文格式一致性

### 如何使用此技能
1. 提供需要格式化的引文文本
2. 指定目标格式（APA、Chicago、IEEE等）
3. 选择输出方式（文内引用、参考文献列表）
4. 检查生成的格式是否正确
5. 必要时进行手动调整

### 注意事项
- 不同格式对作者姓名的处理方式不同
- 期刊名称缩写需要遵循特定规范
- 网络资源的引用格式有特殊要求
- 注意DOI和URL的格式规范

## 参考资源

### 相关文件
- `references/apa-format.md` - APA格式详细规范
- `references/chicago-format.md` - Chicago格式详细规范
- `references/ieee-format.md` - IEEE格式详细规范

### 技能协作
- **paper-analysis**: 提取论文的引用信息
- **literature-review**: 生成综述的参考文献
- **data-extraction**: 从PDF中提取引用信息

## 常见问题 (FAQ)

### Q: 如何处理中文文献的引用？
A: 中文文献引用需要注意：
- 中文作者姓名保持原文格式
- 中文期刊名称使用全称
- 可以同时提供中英文版本
- 根据目标期刊要求选择格式

### Q: 引文编号如何自动生成？
A: 系统采用以下策略：
- 按照引文在文本中出现的顺序编号
- 支持重新排序后的自动更新
- 处理重复引用和多重引用
- 维护编号的连续性

### Q: 如何处理电子资源的引用？
A: 电子资源引用的特殊要求：
- 必须包含访问日期
- 提供稳定的URL或DOI
- 区分在线期刊、数据库、网站等类型
- 注意版本和更新信息

### Q: 引文格式不一致怎么办？
A: 解决方案：
1. 使用格式检查功能识别不一致
2. 统一应用目标格式规范
3. 手动调整特殊情况
4. 使用批量处理功能确保一致性

## 变更记录 (Changelog)

### 2026-01-17
- ✅ 完成技能级文档初始化
- ✅ 添加导航面包屑
- ✅ 更新技能功能说明
- ✅ 完善使用指南

---

*本文档由 Claude AI 助手自动生成，最后更新时间：2026-01-17 16:02:32*