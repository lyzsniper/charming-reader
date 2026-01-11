"""
Skill Activator - 智能技能激活和管理
"""
from typing import List, Optional, Dict, Callable
from datetime import datetime
from .loader import SkillLoader
from .registry import SkillRegistry, Skill, SkillStatus

class SkillActivator:
    """技能激活器"""
    
    def __init__(self, loader: SkillLoader, registry: SkillRegistry,
                 max_concurrent_skills: int = 3):
        self.loader = loader
        self.registry = registry
        self.max_concurrent_skills = max_concurrent_skills
    
    def auto_activate_for_query(self, query: str, max_skills: int = 2) -> List[Skill]:
        """根据查询自动激活相关技能"""
        matched_skills = self.registry.find_skills_by_query(query)
        
        activated_skills = []
        for skill in matched_skills[:max_skills]:
            if self._can_activate_more():
                success = self.activate_skill(skill.name)
                if success:
                    activated_skills.append(skill)
        
        return activated_skills
    
    def activate_skill(self, skill_name: str) -> bool:
        """激活指定技能"""
        skill = self.registry.get_skill(skill_name)
        if not skill:
            print(f"Skill '{skill_name}' not found in registry")
            return False
        
        if self.registry.is_active(skill_name):
            return True
        
        if not self._can_activate_more():
            self._deactivate_oldest()
        
        content = self.loader.load_skill_content(skill_name)
        if not content:
            skill.status = SkillStatus.ERROR
            print(f"Failed to load content for skill '{skill_name}'")
            return False
        
        return self.registry.activate_skill(skill_name, content)
    
    def deactivate_skill(self, skill_name: str) -> bool:
        """停用指定技能"""
        return self.registry.deactivate_skill(skill_name)
    
    def merge_active_skills_for_prompt(self, separator: str = "\n\n---\n\n") -> str:
        """合并所有激活技能的内容，用于添加到 Agent prompt"""
        active_skills = self.registry.get_active_skills()
        
        if not active_skills:
            return ""
        
        skill_sections = []
        for skill in active_skills:
            if skill.content:
                section = f"## Skill: {skill.name}\n\n{skill.content}"
                skill_sections.append(section)
        
        merged = separator.join(skill_sections)
        header = f"# Active Skills ({len(skill_sections)})\n\nYou have access to the following specialized skills. Use them when appropriate.\n\n"
        
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
        
        oldest_skill = min(
            active_skills,
            key=lambda s: s.activated_at if s.activated_at else datetime.min
        )
        
        self.deactivate_skill(oldest_skill.name)
        print(f"Auto-deactivated oldest skill: {oldest_skill.name}")
