"""
学术论文图表信息提取脚本
提取图表标题、描述和相关数值信息
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class FigureType(Enum):
    """图表类型"""
    LINE_CHART = "line_chart"  # 折线图
    BAR_CHART = "bar_chart"    # 柱状图
    SCATTER = "scatter"        # 散点图
    HEATMAP = "heatmap"        # 热图
    DIAGRAM = "diagram"        # 示意图
    ARCHITECTURE = "architecture"  # 架构图
    UNKNOWN = "unknown"

@dataclass
class Figure:
    """图表数据结构"""
    number: int
    caption: str
    figure_type: FigureType
    description: List[str]  # 论文中对图表的描述
    extracted_values: Dict[str, any]  # 提取的数值信息
    source_location: str  # 在论文中的位置
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "figure_number": self.number,
            "caption": self.caption,
            "type": self.figure_type.value,
            "description": self.description,
            "extracted_values": self.extracted_values,
            "location": self.source_location
        }

class FigureExtractor:
    """图表提取器"""
    
    # 图表类型识别关键词
    TYPE_KEYWORDS = {
        FigureType.LINE_CHART: ['curve', 'trend', 'over time', 'progress', 'learning curve'],
        FigureType.BAR_CHART: ['comparison', 'bar', 'performance', 'results'],
        FigureType.SCATTER: ['scatter', 'distribution', 'correlation'],
        FigureType.HEATMAP: ['heatmap', 'heat map', 'attention', 'matrix'],
        FigureType.DIAGRAM: ['diagram', 'illustration', 'workflow', 'pipeline'],
        FigureType.ARCHITECTURE: ['architecture', 'model structure', 'framework', 'network']
    }
    
    def __init__(self):
        pass
    
    def extract_figure_caption(self, text: str, figure_number: int) -> Optional[str]:
        """
        提取图表标题
        
        Args:
            text: 论文文本
            figure_number: 图表编号
        
        Returns:
            图表标题
        """
        # 匹配模式: "Figure X:" 或 "Fig. X:" 或 "Figure X."
        patterns = [
            rf'Figure\s+{figure_number}[:.]?\s*(.+?)(?:\n|$)',
            rf'Fig\.\s+{figure_number}[:.]?\s*(.+?)(?:\n|$)',
            rf'FIG\.\s+{figure_number}[:.]?\s*(.+?)(?:\n|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                caption = match.group(1).strip()
                # 移除尾部标点
                caption = re.sub(r'[.!?]+$', '', caption)
                return caption
        
        return None
    
    def classify_figure_type(self, caption: str, description: str = "") -> FigureType:
        """
        根据标题和描述推断图表类型
        
        Args:
            caption: 图表标题
            description: 图表描述
        
        Returns:
            图表类型
        """
        combined_text = (caption + " " + description).lower()
        
        scores = {}
        for fig_type, keywords in self.TYPE_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in combined_text)
            scores[fig_type] = score
        
        # 找到得分最高的类型
        if scores:
            best_type = max(scores.items(), key=lambda x: x[1])
            if best_type[1] > 0:
                return best_type[0]
        
        return FigureType.UNKNOWN
    
    def find_figure_descriptions(self, text: str, figure_number: int, 
                                 context_window: int = 500) -> List[str]:
        """
        查找论文中对指定图表的描述和引用
        
        Args:
            text: 论文文本
            figure_number: 图表编号
            context_window: 上下文窗口大小（字符数）
        
        Returns:
            描述列表
        """
        descriptions = []
        
        # 匹配引用模式
        patterns = [
            rf'(?:Figure|Fig\.|FIG\.)\s+{figure_number}',
            rf'see\s+(?:Figure|Fig\.)\s+{figure_number}',
            rf'shown\s+in\s+(?:Figure|Fig\.)\s+{figure_number}',
            rf'as\s+(?:illustrated|depicted|shown)\s+in\s+(?:Figure|Fig\.)\s+{figure_number}'
        ]
        
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # 提取前后文
                start = max(0, match.start() - context_window)
                end = min(len(text), match.end() + context_window)
                context = text[start:end]
                
                # 提取包含引用的完整句子
                sentences = self._extract_sentences(context, match.start() - start)
                descriptions.extend(sentences)
        
        # 去重
        descriptions = list(set(descriptions))
        return descriptions
    
    def _extract_sentences(self, text: str, ref_position: int) -> List[str]:
        """从文本中提取包含引用位置的句子"""
        # 简单的句子分割（基于句号）
        sentences = []
        current_pos = 0
        
        for sentence in re.split(r'[.!?]+', text):
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_start = current_pos
            sentence_end = current_pos + len(sentence)
            
            # 检查引用是否在这个句子中
            if sentence_start <= ref_position <= sentence_end:
                sentences.append(sentence)
            
            current_pos = sentence_end + 1
        
        return sentences
    
    def extract_values_from_description(self, descriptions: List[str]) -> Dict[str, any]:
        """
        从描述中提取数值信息
        
        Args:
            descriptions: 描述列表
        
        Returns:
            提取的数值信息字典
        """
        extracted = {}
        
        # 性能指标模式
        metric_patterns = {
            'accuracy': r'accuracy\s+(?:of|:)?\s*(\d+(?:\.\d+)?)%?',
            'f1_score': r'F1[-\s]?score\s+(?:of|:)?\s*(\d+(?:\.\d+)?)',
            'loss': r'loss\s+(?:of|:)?\s*(\d+(?:\.\d+)?)',
            'improvement': r'improve(?:ment|s)?\s+(?:of|by)?\s*(\d+(?:\.\d+)?)%?'
        }
        
        for desc in descriptions:
            desc_lower = desc.lower()
            for metric_name, pattern in metric_patterns.items():
                matches = re.findall(pattern, desc_lower)
                if matches:
                    # 如果找到多个值，存储为列表
                    if metric_name not in extracted:
                        extracted[metric_name] = []
                    extracted[metric_name].extend([float(m) for m in matches])
        
        # 清理：如果只有一个值，存储为单个数值而非列表
        for key in extracted:
            if len(extracted[key]) == 1:
                extracted[key] = extracted[key][0]
        
        return extracted
    
    def extract_figure(self, text: str, figure_number: int) -> Optional[Figure]:
        """
        提取完整的图表信息
        
        Args:
            text: 论文文本
            figure_number: 图表编号
        
        Returns:
            Figure对象
        """
        # 提取标题
        caption = self.extract_figure_caption(text, figure_number)
        if not caption:
            return None
        
        # 查找描述
        descriptions = self.find_figure_descriptions(text, figure_number)
        
        # 分类图表类型
        desc_text = " ".join(descriptions)
        figure_type = self.classify_figure_type(caption, desc_text)
        
        # 提取数值
        extracted_values = self.extract_values_from_description(descriptions)
        
        return Figure(
            number=figure_number,
            caption=caption,
            figure_type=figure_type,
            description=descriptions,
            extracted_values=extracted_values,
            source_location=f"Figure {figure_number}"
        )
    
    def extract_all_figures(self, text: str, max_figures: int = 20) -> List[Figure]:
        """
        提取论文中的所有图表
        
        Args:
            text: 论文文本
            max_figures: 最多提取的图表数量
        
        Returns:
            Figure对象列表
        """
        figures = []
        
        for i in range(1, max_figures + 1):
            figure = self.extract_figure(text, i)
            if figure:
                figures.append(figure)
            else:
                # 如果连续3个图表不存在，停止搜索
                if i > 3 and all(f.number != i-j for f in figures for j in range(1, 4)):
                    break
        
        return figures
    
    def generate_figure_summary(self, figure: Figure) -> str:
        """
        生成图表摘要
        
        Args:
            figure: Figure对象
        
        Returns:
            摘要文本
        """
        lines = []
        lines.append(f"## Figure {figure.number}: {figure.caption}")
        lines.append(f"\n**类型**: {figure.figure_type.value}")
        
        if figure.description:
            lines.append(f"\n**描述**:")
            for i, desc in enumerate(figure.description[:3], 1):  # 最多显示3条
                lines.append(f"{i}. {desc}")
        
        if figure.extracted_values:
            lines.append(f"\n**提取的数值**:")
            for key, value in figure.extracted_values.items():
                if isinstance(value, list):
                    lines.append(f"- {key}: {', '.join(map(str, value))}")
                else:
                    lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)

def analyze_figure_trends(figures: List[Figure]) -> Dict[str, any]:
    """
    分析多个图表的趋势
    
    Args:
        figures: Figure对象列表
    
    Returns:
        趋势分析结果
    """
    analysis = {
        "total_figures": len(figures),
        "types": {},
        "metrics_mentioned": set()
    }
    
    for figure in figures:
        # 统计图表类型
        fig_type = figure.figure_type.value
        analysis["types"][fig_type] = analysis["types"].get(fig_type, 0) + 1
        
        # 收集提到的指标
        analysis["metrics_mentioned"].update(figure.extracted_values.keys())
    
    analysis["metrics_mentioned"] = list(analysis["metrics_mentioned"])
    
    return analysis

# 使用示例
if __name__ == "__main__":
    # 示例论文文本
    sample_text = """
Figure 1: Training and validation accuracy over epochs. The model achieves 
94.2% accuracy on the validation set after 10 epochs.

As shown in Figure 1, the training process converges smoothly. The validation 
accuracy improves by 15% compared to the baseline. Figure 1 illustrates the 
learning curve of our proposed model.

Figure 2: Model architecture. Our model consists of 12 transformer layers 
with multi-head attention.

The architecture shown in Figure 2 uses residual connections and layer 
normalization.
"""
    
    extractor = FigureExtractor()
    
    # 提取所有图表
    figures = extractor.extract_all_figures(sample_text)
    
    print(f"找到 {len(figures)} 个图表\n")
    
    for figure in figures:
        print(extractor.generate_figure_summary(figure))
        print("\n" + "="*60 + "\n")
    
    # 趋势分析
    analysis = analyze_figure_trends(figures)
    print("图表分析:")
    print(f"总计: {analysis['total_figures']} 个图表")
    print(f"类型分布: {analysis['types']}")
    print(f"提到的指标: {analysis['metrics_mentioned']}")

