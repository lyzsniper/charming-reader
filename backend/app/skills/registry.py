"""
Skill Registry - 管理技能的元数据和状态
"""

from typing import Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

class SkillStatus(Enum):
    """技能状态"""
    AVAILABLE = "available"  # 可用但未加载
    LOADED = "loaded"        # 已加载元数据
    ACTIVE = "active"        # 已激活（完整内容已加载）
    ERROR = "error"          # 加载错误

@dataclass
class Skill:
    """技能对象"""
    name: str
    description: str
    triggers: List[str]
    version: str
    file_path: str
    status: SkillStatus = SkillStatus.AVAILABLE
    content: Optional[str] = None
    activated_at: Optional[datetime] = None
    activation_count: int = 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "triggers": self.triggers,
            "version": self.version,
            "status": self.status.value,
            "has_content": self.content is not None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "activation_count": self.activation_count
        }

class SkillRegistry:
    """
    技能注册表
    维护所有技能的元数据和状态
    """
    
    def __init__(self):
        """初始化注册表"""
        self._skills: Dict[str, Skill] = {}
        self._trigger_index: Dict[str, Set[str]] = {}  # trigger -> skill_names
        self._active_skills: Set[str] = set()
    
    def register_skill(self, name: str, description: str, triggers: List[str],
                      version: str, file_path: str) -> Skill:
        """
        注册一个技能
        
        Args:
            name: 技能名称
            description: 技能描述
            triggers: 触发关键词列表
            version: 版本号
            file_path: 技能文件路径
        
        Returns:
            Skill 对象
        """
        skill = Skill(
            name=name,
            description=description,
            triggers=triggers,
            version=version,
            file_path=file_path,
            status=SkillStatus.LOADED
        )
        
        self._skills[name] = skill
        
        # 建立触发词索引
        for trigger in triggers:
            trigger_lower = trigger.lower()
            if trigger_lower not in self._trigger_index:
                self._trigger_index[trigger_lower] = set()
            self._trigger_index[trigger_lower].add(name)
        
        return skill
    
    def get_skill(self, name: str) -> Optional[Skill]:
        """
        获取指定技能
        
        Args:
            name: 技能名称
        
        Returns:
            Skill 对象或 None
        """
        return self._skills.get(name)
    
    def get_all_skills(self) -> List[Skill]:
        """
        获取所有技能
        
        Returns:
            技能列表
        """
        return list(self._skills.values())
    
    def get_active_skills(self) -> List[Skill]:
        """
        获取所有激活的技能
        
        Returns:
            激活的技能列表
        """
        return [self._skills[name] for name in self._active_skills 
                if name in self._skills]
    
    def activate_skill(self, name: str, content: str) -> bool:
        """
        激活一个技能（加载完整内容）
        
        Args:
            name: 技能名称
            content: 技能完整内容
        
        Returns:
            是否成功激活
        """
        if name not in self._skills:
            return False
        
        skill = self._skills[name]
        skill.content = content
        skill.status = SkillStatus.ACTIVE
        skill.activated_at = datetime.now()
        skill.activation_count += 1
        
        self._active_skills.add(name)
        
        return True
    
    def deactivate_skill(self, name: str) -> bool:
        """
        停用一个技能（清除内容，保留元数据）
        
        Args:
            name: 技能名称
        
        Returns:
            是否成功停用
        """
        if name not in self._skills:
            return False
        
        skill = self._skills[name]
        skill.content = None
        skill.status = SkillStatus.LOADED
        skill.activated_at = None
        
        if name in self._active_skills:
            self._active_skills.remove(name)
        
        return True
    
    def deactivate_all_skills(self):
        """停用所有技能"""
        for name in list(self._active_skills):
            self.deactivate_skill(name)
    
    def is_active(self, name: str) -> bool:
        """
        检查技能是否已激活
        
        Args:
            name: 技能名称
        
        Returns:
            是否已激活
        """
        return name in self._active_skills
    
    def find_skills_by_trigger(self, text: str) -> List[Skill]:
        """
        根据文本查找匹配的技能（通过触发词）
        
        Args:
            text: 输入文本（如用户查询）
        
        Returns:
            匹配的技能列表
        """
        text_lower = text.lower()
        matched_skills = set()
        
        for trigger, skill_names in self._trigger_index.items():
            if trigger in text_lower:
                matched_skills.update(skill_names)
        
        return [self._skills[name] for name in matched_skills 
                if name in self._skills]
    
    def find_skills_by_query(self, query: str, threshold: float = 0.3) -> List[Skill]:
        """
        根据查询内容查找相关技能（简单的关键词匹配）
        
        Args:
            query: 查询字符串
            threshold: 匹配阈值
        
        Returns:
            相关技能列表（按相关性排序）
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_skills = []
        
        for skill in self._skills.values():
            score = 0.0
            
            # 检查描述匹配
            desc_words = set(skill.description.lower().split())
            common_words = query_words & desc_words
            if desc_words:
                score += len(common_words) / len(desc_words) * 0.5
            
            # 检查触发词匹配
            for trigger in skill.triggers:
                if trigger.lower() in query_lower:
                    score += 0.5
            
            # 检查名称匹配
            if skill.name.lower() in query_lower:
                score += 0.3
            
            if score >= threshold:
                scored_skills.append((skill, score))
        
        # 按得分降序排序
        scored_skills.sort(key=lambda x: x[1], reverse=True)
        
        return [skill for skill, score in scored_skills]
    
    def get_statistics(self) -> Dict:
        """
        获取注册表统计信息
        
        Returns:
            统计信息字典
        """
        total_skills = len(self._skills)
        active_skills = len(self._active_skills)
        
        status_counts = {}
        for skill in self._skills.values():
            status = skill.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total_triggers = sum(len(skill.triggers) for skill in self._skills.values())
        
        # 最常使用的技能
        most_used = sorted(
            self._skills.values(),
            key=lambda s: s.activation_count,
            reverse=True
        )[:5]
        
        return {
            "total_skills": total_skills,
            "active_skills": active_skills,
            "status_distribution": status_counts,
            "total_triggers": total_triggers,
            "unique_triggers": len(self._trigger_index),
            "most_used_skills": [
                {"name": s.name, "activation_count": s.activation_count}
                for s in most_used
            ]
        }
    
    def unregister_skill(self, name: str) -> bool:
        """
        注销一个技能
        
        Args:
            name: 技能名称
        
        Returns:
            是否成功注销
        """
        if name not in self._skills:
            return False
        
        skill = self._skills[name]
        
        # 移除触发词索引
        for trigger in skill.triggers:
            trigger_lower = trigger.lower()
            if trigger_lower in self._trigger_index:
                self._trigger_index[trigger_lower].discard(name)
                if not self._trigger_index[trigger_lower]:
                    del self._trigger_index[trigger_lower]
        
        # 移除激活状态
        if name in self._active_skills:
            self._active_skills.remove(name)
        
        # 移除技能
        del self._skills[name]
        
        return True
    
    def clear(self):
        """清空注册表"""
        self._skills.clear()
        self._trigger_index.clear()
        self._active_skills.clear()
    
    def export_metadata(self) -> Dict:
        """
        导出所有技能的元数据
        
        Returns:
            元数据字典
        """
        return {
            "skills": [skill.to_dict() for skill in self._skills.values()],
            "statistics": self.get_statistics()
        }

