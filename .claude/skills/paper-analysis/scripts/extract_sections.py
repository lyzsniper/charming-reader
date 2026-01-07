"""
学术论文章节提取脚本
使用基于规则的方法识别论文章节结构
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass

@dataclass
class Section:
    """章节数据结构"""
    title: str
    level: int
    start_pos: int
    end_pos: int
    content: str
    section_type: str  # introduction, methods, results, discussion, conclusion

# 章节关键词映射
SECTION_KEYWORDS = {
    'introduction': ['introduction', 'background', 'motivation', 'overview'],
    'related_work': ['related work', 'literature review', 'previous work', 'prior art'],
    'methods': ['method', 'methodology', 'approach', 'design', 'architecture', 
                'materials', 'procedure', 'experimental setup'],
    'results': ['result', 'finding', 'experiment', 'evaluation', 'performance'],
    'discussion': ['discussion', 'analysis', 'interpretation', 'implication'],
    'conclusion': ['conclusion', 'summary', 'future work', 'concluding remarks']
}

def extract_headings(text: str) -> List[Tuple[str, int, int]]:
    """
    提取文本中的标题
    返回: [(标题文本, 层级, 位置)]
    """
    headings = []
    
    # 匹配 Markdown 风格标题 (# Title, ## Title, etc.)
    markdown_pattern = r'^(#{1,6})\s+(.+)$'
    
    # 匹配纯大写标题 (INTRODUCTION)
    uppercase_pattern = r'^([A-Z][A-Z\s]{2,}[A-Z])$'
    
    # 匹配数字编号标题 (1. Introduction, 2.1 Methods)
    numbered_pattern = r'^(\d+\.?(?:\.\d+)*)\s+([A-Z][a-zA-Z\s]+)$'
    
    lines = text.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Markdown 标题
        md_match = re.match(markdown_pattern, line, re.MULTILINE)
        if md_match:
            level = len(md_match.group(1))
            title = md_match.group(2).strip()
            headings.append((title, level, i))
            continue
        
        # 大写标题
        uc_match = re.match(uppercase_pattern, line)
        if uc_match and len(line) > 3:
            title = line.strip()
            headings.append((title, 1, i))
            continue
        
        # 数字编号标题
        num_match = re.match(numbered_pattern, line)
        if num_match:
            number = num_match.group(1)
            title = num_match.group(2).strip()
            level = number.count('.') + 1
            headings.append((title, level, i))
    
    return headings

def classify_section(title: str) -> str:
    """
    根据标题文本分类章节类型
    """
    title_lower = title.lower()
    
    for section_type, keywords in SECTION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in title_lower:
                return section_type
    
    return 'other'

def extract_sections(text: str) -> List[Section]:
    """
    从论文文本中提取结构化章节
    """
    headings = extract_headings(text)
    sections = []
    lines = text.split('\n')
    
    for i, (title, level, line_num) in enumerate(headings):
        # 确定章节内容范围
        start_pos = line_num
        if i < len(headings) - 1:
            end_pos = headings[i + 1][2]
        else:
            end_pos = len(lines)
        
        # 提取章节内容
        content = '\n'.join(lines[start_pos:end_pos])
        
        # 分类章节类型
        section_type = classify_section(title)
        
        section = Section(
            title=title,
            level=level,
            start_pos=start_pos,
            end_pos=end_pos,
            content=content,
            section_type=section_type
        )
        sections.append(section)
    
    return sections

def generate_structure_report(sections: List[Section]) -> Dict:
    """
    生成论文结构报告
    """
    report = {
        'total_sections': len(sections),
        'structure': [],
        'key_sections': {},
        'has_standard_structure': False
    }
    
    # 构建结构树
    for section in sections:
        report['structure'].append({
            'title': section.title,
            'level': section.level,
            'type': section.section_type,
            'length': len(section.content)
        })
        
        # 记录关键章节
        if section.section_type in ['introduction', 'methods', 'results', 'discussion', 'conclusion']:
            report['key_sections'][section.section_type] = {
                'title': section.title,
                'position': section.start_pos,
                'found': True
            }
    
    # 检查是否具有标准 IMRaD 结构
    required_sections = ['introduction', 'methods', 'results']
    report['has_standard_structure'] = all(
        sec in report['key_sections'] for sec in required_sections
    )
    
    return report

def main(paper_text: str) -> Dict:
    """
    主函数：分析论文结构
    
    Args:
        paper_text: 论文全文
    
    Returns:
        结构化的分析结果
    """
    sections = extract_sections(paper_text)
    report = generate_structure_report(sections)
    
    return {
        'sections': sections,
        'report': report
    }

# 使用示例
if __name__ == "__main__":
    sample_text = """
# Deep Learning for Natural Language Processing

## Abstract
This paper presents...

## 1. Introduction
Natural language processing has...

## 2. Related Work
Previous studies have shown...

## 3. Methodology
### 3.1 Model Architecture
We propose a novel architecture...

### 3.2 Training Procedure
The model is trained using...

## 4. Experiments
### 4.1 Datasets
We evaluate on three datasets...

### 4.2 Results
Table 1 shows the performance...

## 5. Discussion
Our results demonstrate...

## 6. Conclusion
In this work, we...
"""
    
    result = main(sample_text)
    print(f"Found {result['report']['total_sections']} sections")
    print(f"Has standard structure: {result['report']['has_standard_structure']}")
    print("\nKey sections:")
    for sec_type, info in result['report']['key_sections'].items():
        print(f"  {sec_type}: {info['title']}")

