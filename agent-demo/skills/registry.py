"""
Skill Registry - 管理技能的元数据和状态
"""
from typing import Dict, List, Optional, Set
from enum import Enum
from dataclasses import dataclass
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
        """注册一个技能"""
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
        """获取指定技能"""
        return self._skills.get(name)
    
    def get_all_skills(self) -> List[Skill]:
        """获取所有技能"""
        return list(self._skills.values())
    
    def get_active_skills(self) -> List[Skill]:
        """获取所有激活的技能"""
        return [self._skills[name] for name in self._active_skills 
                if name in self._skills]
    
    def activate_skill(self, name: str, content: str) -> bool:
        """激活一个技能（加载完整内容）"""
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
        """停用一个技能（清除内容，保留元数据）"""
        if name not in self._skills:
            return False
        
        skill = self._skills[name]
        skill.content = None
        skill.status = SkillStatus.LOADED
        skill.activated_at = None
        
        if name in self._active_skills:
            self._active_skills.remove(name)
        
        return True
    
    def is_active(self, name: str) -> bool:
        """检查技能是否已激活"""
        return name in self._active_skills
    
    def find_skills_by_query(self, query: str, threshold: float = 0.3) -> List[Skill]:
        """根据查询内容查找相关技能"""
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
