"""
学术论文表格解析脚本
支持 Markdown 表格和文本描述表格的解析
"""

import re
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

class DataType(Enum):
    """数据类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    PERCENTAGE = "percentage"
    TIME = "time"
    BOOLEAN = "boolean"
    NA = "not_available"

@dataclass
class Cell:
    """表格单元格"""
    value: Any
    data_type: DataType
    original_text: str
    
@dataclass
class Table:
    """表格数据结构"""
    caption: Optional[str]
    headers: List[str]
    rows: List[List[Cell]]
    source: str  # 来源位置
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "caption": self.caption,
            "headers": self.headers,
            "rows": [
                [{"value": cell.value, "type": cell.data_type.value} 
                 for cell in row]
                for row in self.rows
            ]
        }
    
    def to_markdown(self) -> str:
        """转换为 Markdown 表格"""
        lines = []
        if self.caption:
            lines.append(f"**{self.caption}**\n")
        
        # 表头
        lines.append("| " + " | ".join(self.headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(self.headers)) + " |")
        
        # 数据行
        for row in self.rows:
            row_str = "| " + " | ".join([str(cell.value) for cell in row]) + " |"
            lines.append(row_str)
        
        return "\n".join(lines)

class TableParser:
    """表格解析器"""
    
    # 数值模式
    PERCENTAGE_PATTERN = r'^(\d+(?:\.\d+)?)%$'
    FLOAT_PATTERN = r'^(\d+\.\d+)$'
    INTEGER_PATTERN = r'^(\d+(?:,\d{3})*)$'
    SCIENTIFIC_PATTERN = r'^(\d+(?:\.\d+)?)[eE]([+-]?\d+)$'
    TIME_PATTERN = r'^(\d+(?:\.\d+)?)\s*(s|ms|h|min|hour|second|minute)s?$'
    
    # 缺失值标记
    NA_MARKERS = ['-', 'N/A', 'n/a', 'NA', 'null', '—', '–']
    
    def __init__(self):
        pass
    
    def parse_markdown_table(self, text: str, caption: Optional[str] = None) -> Optional[Table]:
        """
        解析 Markdown 格式的表格
        
        Example:
            | Model | Accuracy | F1 |
            |-------|----------|-----|
            | BERT  | 92.3%    | 0.915 |
        """
        lines = text.strip().split('\n')
        
        # 过滤空行
        lines = [line.strip() for line in lines if line.strip()]
        
        if len(lines) < 2:
            return None
        
        # 解析表头
        header_line = lines[0]
        headers = self._parse_row(header_line)
        
        # 跳过分隔线（第二行）
        # 解析数据行
        rows = []
        for line in lines[2:]:
            row_values = self._parse_row(line)
            if len(row_values) == len(headers):
                cells = [self._parse_cell(val) for val in row_values]
                rows.append(cells)
        
        return Table(
            caption=caption,
            headers=headers,
            rows=rows,
            source="markdown"
        )
    
    def parse_text_table(self, text: str, caption: Optional[str] = None) -> Optional[Table]:
        """
        解析文本描述的表格
        
        Example:
            Model X: 92.3% accuracy
            Model Y: 89.1% accuracy
            Model Z: 94.2% accuracy
        """
        lines = text.strip().split('\n')
        lines = [line.strip() for line in lines if line.strip()]
        
        if len(lines) < 2:
            return None
        
        # 尝试识别模式
        # 模式1: "Key: Value" 格式
        pattern1 = r'^(.+?):\s*(.+)$'
        
        headers = None
        rows = []
        
        for line in lines:
            match = re.match(pattern1, line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                
                if headers is None:
                    # 推断表头
                    headers = ["Item", "Value"]
                
                cells = [
                    Cell(key, DataType.STRING, key),
                    self._parse_cell(value)
                ]
                rows.append(cells)
        
        if headers and rows:
            return Table(
                caption=caption,
                headers=headers,
                rows=rows,
                source="text"
            )
        
        return None
    
    def _parse_row(self, line: str) -> List[str]:
        """解析表格行，提取单元格内容"""
        # 移除首尾的 |
        line = line.strip()
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]
        
        # 分割单元格
        cells = [cell.strip() for cell in line.split('|')]
        return cells
    
    def _parse_cell(self, text: str) -> Cell:
        """解析单元格内容，识别数据类型"""
        text = text.strip()
        
        # 检查缺失值
        if text in self.NA_MARKERS:
            return Cell(None, DataType.NA, text)
        
        # 检查百分比
        match = re.match(self.PERCENTAGE_PATTERN, text)
        if match:
            value = float(match.group(1))
            return Cell(value, DataType.PERCENTAGE, text)
        
        # 检查科学计数法
        match = re.match(self.SCIENTIFIC_PATTERN, text)
        if match:
            base = float(match.group(1))
            exp = int(match.group(2))
            value = base * (10 ** exp)
            return Cell(value, DataType.FLOAT, text)
        
        # 检查时间
        match = re.match(self.TIME_PATTERN, text, re.IGNORECASE)
        if match:
            value = float(match.group(1))
            unit = match.group(2).lower()
            # 统一转换为秒
            if unit in ['h', 'hour']:
                value *= 3600
            elif unit in ['min', 'minute']:
                value *= 60
            elif unit == 'ms':
                value /= 1000
            return Cell(value, DataType.TIME, text)
        
        # 检查浮点数
        match = re.match(self.FLOAT_PATTERN, text)
        if match:
            value = float(match.group(1))
            return Cell(value, DataType.FLOAT, text)
        
        # 检查整数（可能包含千位分隔符）
        match = re.match(self.INTEGER_PATTERN, text)
        if match:
            value_str = match.group(1).replace(',', '')
            value = int(value_str)
            return Cell(value, DataType.INTEGER, text)
        
        # 检查布尔值
        if text.lower() in ['true', 'yes', '✓', '√']:
            return Cell(True, DataType.BOOLEAN, text)
        if text.lower() in ['false', 'no', '✗', '×']:
            return Cell(False, DataType.BOOLEAN, text)
        
        # 默认为字符串
        return Cell(text, DataType.STRING, text)
    
    def find_best_result(self, table: Table, metric_column: str) -> Optional[Dict]:
        """
        在表格中找到指定指标的最佳结果
        
        Args:
            table: 表格对象
            metric_column: 指标列名（如 "Accuracy"）
        
        Returns:
            包含最佳结果的字典，包括行索引、值和模型名
        """
        try:
            col_index = table.headers.index(metric_column)
        except ValueError:
            return None
        
        best_value = None
        best_row_index = None
        
        for i, row in enumerate(table.rows):
            cell = row[col_index]
            if cell.data_type in [DataType.FLOAT, DataType.PERCENTAGE, DataType.INTEGER]:
                if best_value is None or cell.value > best_value:
                    best_value = cell.value
                    best_row_index = i
        
        if best_row_index is not None:
            # 假设第一列是模型名
            model_name = table.rows[best_row_index][0].value
            return {
                "row_index": best_row_index,
                "model": model_name,
                "value": best_value,
                "column": metric_column
            }
        
        return None
    
    def compare_rows(self, table: Table, row1_index: int, row2_index: int, 
                     metric_column: str) -> Optional[Dict]:
        """比较两行的指标"""
        try:
            col_index = table.headers.index(metric_column)
        except ValueError:
            return None
        
        cell1 = table.rows[row1_index][col_index]
        cell2 = table.rows[row2_index][col_index]
        
        if cell1.data_type == cell2.data_type and \
           cell1.data_type in [DataType.FLOAT, DataType.PERCENTAGE, DataType.INTEGER]:
            difference = cell1.value - cell2.value
            percentage_diff = (difference / cell2.value) * 100 if cell2.value != 0 else None
            
            return {
                "row1": row1_index,
                "row2": row2_index,
                "value1": cell1.value,
                "value2": cell2.value,
                "difference": difference,
                "percentage_difference": percentage_diff,
                "better": "row1" if difference > 0 else "row2" if difference < 0 else "equal"
            }
        
        return None

def extract_table_caption(text: str, table_number: int) -> Optional[str]:
    """
    从论文文本中提取表格标题
    
    Args:
        text: 论文文本
        table_number: 表格编号
    
    Returns:
        表格标题（如有）
    """
    # 匹配模式: "Table X: Caption" 或 "Table X. Caption"
    pattern = rf'Table\s+{table_number}[:.]?\s*(.+?)(?:\n|$)'
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        caption = match.group(1).strip()
        # 移除可能的尾部标点
        caption = re.sub(r'[.!?]+$', '', caption)
        return caption
    
    return None

# 使用示例
if __name__ == "__main__":
    # 示例1: 解析 Markdown 表格
    markdown_text = """
| Model      | Accuracy | F1-Score |
|------------|----------|----------|
| BERT-base  | 92.3%    | 0.915    |
| GPT-2      | 89.1%    | 0.883    |
| RoBERTa    | 94.2%    | 0.937    |
"""
    
    parser = TableParser()
    table = parser.parse_markdown_table(markdown_text, caption="Performance Comparison")
    
    if table:
        print("解析成功！")
        print(f"表头: {table.headers}")
        print(f"行数: {len(table.rows)}")
        print("\nMarkdown输出:")
        print(table.to_markdown())
        
        # 查找最佳结果
        best = parser.find_best_result(table, "Accuracy")
        if best:
            print(f"\n最佳结果: {best['model']} with {best['value']}% accuracy")
        
        # 比较两个模型
        comparison = parser.compare_rows(table, 0, 2, "Accuracy")
        if comparison:
            print(f"\nBERT vs RoBERTa: {comparison['difference']:.1f} pp difference")
    
    # 示例2: 解析文本表格
    text_table = """
BERT-base: 92.3% accuracy
GPT-2: 89.1% accuracy
RoBERTa: 94.2% accuracy
"""
    
    table2 = parser.parse_text_table(text_table, caption="Text Format Results")
    if table2:
        print("\n\n文本表格解析:")
        print(table2.to_markdown())

