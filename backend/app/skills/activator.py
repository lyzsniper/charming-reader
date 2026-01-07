"""
Skill Activator - 智能技能激活和管理
"""

from typing import List, Optional, Dict, Callable
from .loader import SkillLoader
from .registry import SkillRegistry, Skill, SkillStatus

class SkillActivator:
    """
    技能激活器
    负责根据用户输入智能匹配和激活技能
    """
    
    def __init__(self, loader: SkillLoader, registry: SkillRegistry,
                 max_concurrent_skills: int = 3):
        """
        初始化激活器
        
        Args:
            loader: 技能加载器
            registry: 技能注册表
            max_concurrent_skills: 最大同时激活的技能数量
        """
        self.loader = loader
        self.registry = registry
        self.max_concurrent_skills = max_concurrent_skills
        
        # 激活策略
        self.activation_strategy: str = "auto"  # auto, manual, all
        
        # 回调函数
        self._on_skill_activated: Optional[Callable[[Skill], None]] = None
        self._on_skill_deactivated: Optional[Callable[[str], None]] = None
    
    def set_activation_callback(self, callback: Callable[[Skill], None]):
        """设置技能激活回调"""
        self._on_skill_activated = callback
    
    def set_deactivation_callback(self, callback: Callable[[str], None]):
        """设置技能停用回调"""
        self._on_skill_deactivated = callback
    
    def auto_activate_for_query(self, query: str, max_skills: int = 2) -> List[Skill]:
        """
        根据查询自动激活相关技能
        
        Args:
            query: 用户查询
            max_skills: 最多激活的技能数量
        
        Returns:
            激活的技能列表
        """
        # 查找匹配的技能
        matched_skills = self.registry.find_skills_by_query(query)
        
        activated_skills = []
        
        for skill in matched_skills[:max_skills]:
            if self._can_activate_more():
                success = self.activate_skill(skill.name)
                if success:
                    activated_skills.append(skill)
        
        return activated_skills
    
    def activate_skill(self, skill_name: str) -> bool:
        """
        激活指定技能
        
        Args:
            skill_name: 技能名称
        
        Returns:
            是否成功激活
        """
        # 检查技能是否已注册
        skill = self.registry.get_skill(skill_name)
        if not skill:
            print(f"Skill '{skill_name}' not found in registry")
            return False
        
        # 检查是否已激活
        if self.registry.is_active(skill_name):
            print(f"Skill '{skill_name}' is already active")
            return True
        
        # 检查是否达到最大并发数
        if not self._can_activate_more():
            # 尝试停用最旧的技能
            self._deactivate_oldest()
        
        # 加载技能内容
        content = self.loader.load_skill_content(skill_name)
        if not content:
            skill.status = SkillStatus.ERROR
            print(f"Failed to load content for skill '{skill_name}'")
            return False
        
        # 激活技能
        success = self.registry.activate_skill(skill_name, content)
        
        if success and self._on_skill_activated:
            self._on_skill_activated(skill)
        
        return success
    
    def activate_multiple(self, skill_names: List[str]) -> Dict[str, bool]:
        """
        激活多个技能
        
        Args:
            skill_names: 技能名称列表
        
        Returns:
            激活结果字典 {skill_name: success}
        """
        results = {}
        
        for name in skill_names:
            results[name] = self.activate_skill(name)
        
        return results
    
    def deactivate_skill(self, skill_name: str) -> bool:
        """
        停用指定技能
        
        Args:
            skill_name: 技能名称
        
        Returns:
            是否成功停用
        """
        success = self.registry.deactivate_skill(skill_name)
        
        if success and self._on_skill_deactivated:
            self._on_skill_deactivated(skill_name)
        
        return success
    
    def deactivate_all(self):
        """停用所有技能"""
        active_skills = self.registry.get_active_skills()
        for skill in active_skills:
            self.deactivate_skill(skill.name)
    
    def suggest_skills_for_query(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        为查询推荐技能（不自动激活）
        
        Args:
            query: 用户查询
            top_k: 推荐数量
        
        Returns:
            推荐技能信息列表
        """
        matched_skills = self.registry.find_skills_by_query(query)
        
        suggestions = []
        for skill in matched_skills[:top_k]:
            suggestions.append({
                "name": skill.name,
                "description": skill.description,
                "is_active": self.registry.is_active(skill.name),
                "relevance": "high"  # 简化版本，实际可以计算相关性分数
            })
        
        return suggestions
    
    def get_active_skills_content(self) -> List[Dict[str, str]]:
        """
        获取所有激活技能的内容
        
        Returns:
            技能内容列表 [{"name": ..., "content": ...}]
        """
        active_skills = self.registry.get_active_skills()
        
        contents = []
        for skill in active_skills:
            if skill.content:
                contents.append({
                    "name": skill.name,
                    "content": skill.content
                })
        
        return contents
    
    def merge_active_skills_for_prompt(self, separator: str = "\n\n---\n\n") -> str:
        """
        合并所有激活技能的内容，用于添加到 Agent prompt
        
        Args:
            separator: 技能之间的分隔符
        
        Returns:
            合并后的内容字符串
        """
        contents = self.get_active_skills_content()
        
        if not contents:
            return ""
        
        skill_sections = []
        for item in contents:
            section = f"## Skill: {item['name']}\n\n{item['content']}"
            skill_sections.append(section)
        
        merged = separator.join(skill_sections)
        
        # 添加标题
        header = f"# Active Skills ({len(contents)})\n\nYou have access to the following specialized skills. Use them when appropriate.\n\n"
        
        return header + merged
    
    def _can_activate_more(self) -> bool:
        """检查是否可以激活更多技能"""
        active_count = len(self.registry.get_active_skills())
        return active_count < self.max_concurrent_skills
    
    def _deactivate_oldest(self):
        """停用最早激活的技能"""
        active_skills = self.registry.get_active_skills()
        
        if not active_skills:
            return
        
        # 找到最早激活的技能
        oldest_skill = min(
            active_skills,
            key=lambda s: s.activated_at if s.activated_at else datetime.min
        )
        
        self.deactivate_skill(oldest_skill.name)
        print(f"Auto-deactivated oldest skill: {oldest_skill.name}")
    
    def get_activation_summary(self) -> Dict:
        """
        获取激活状态摘要
        
        Returns:
            摘要信息字典
        """
        active_skills = self.registry.get_active_skills()
        
        return {
            "active_count": len(active_skills),
            "max_concurrent": self.max_concurrent_skills,
            "can_activate_more": self._can_activate_more(),
            "active_skills": [
                {
                    "name": skill.name,
                    "description": skill.description,
                    "activated_at": skill.activated_at.isoformat() if skill.activated_at else None,
                    "activation_count": skill.activation_count
                }
                for skill in active_skills
            ]
        }
    
    def smart_deactivate(self, new_query: str):
        """
        智能停用：根据新查询，停用不再相关的技能
        
        Args:
            new_query: 新的用户查询
        """
        active_skills = self.registry.get_active_skills()
        relevant_skills = set(
            skill.name for skill in self.registry.find_skills_by_query(new_query)
        )
        
        for skill in active_skills:
            if skill.name not in relevant_skills:
                self.deactivate_skill(skill.name)
                print(f"Smart-deactivated skill: {skill.name} (no longer relevant)")

# 导入 datetime 用于 _deactivate_oldest
from datetime import datetime

