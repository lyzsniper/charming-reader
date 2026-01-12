"""
Skills Manager - 统一的技能管理接口
"""
from typing import List, Dict
from .loader import SkillLoader
from .registry import SkillRegistry, Skill
from .activator import SkillActivator
import sys
from pathlib import Path

# 添加父目录到路径，以便导入 config
sys.path.insert(0, str(Path(__file__).parent.parent))
import config

class SkillsManager:
    """技能管理器（单例模式）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 初始化组件
        self.loader = SkillLoader(skills_dir=config.settings.SKILLS_DIR)
        self.registry = SkillRegistry()
        self.activator = SkillActivator(
            loader=self.loader,
            registry=self.registry,
            max_concurrent_skills=config.settings.SKILLS_MAX_CONCURRENT
        )
        
        # 加载所有技能
        self._load_all_skills()
        
        self._initialized = True
    
    def _load_all_skills(self):
        """加载所有技能的元数据到注册表"""
        skills_metadata = self.loader.scan_skills()
        
        for metadata in skills_metadata:
            self.registry.register_skill(
                name=metadata.name,
                description=metadata.description,
                triggers=metadata.triggers,
                version=metadata.version,
                file_path=metadata.file_path
            )
        
        print(f"✓ Loaded {len(skills_metadata)} skills")
    
    def list_all_skills(self) -> List[Dict]:
        """列出所有可用技能"""
        skills = self.registry.get_all_skills()
        return [skill.to_dict() for skill in skills]
    
    def activate_skill(self, skill_name: str) -> bool:
        """激活指定技能"""
        return self.activator.activate_skill(skill_name)
    
    def auto_activate_for_query(self, query: str, max_skills: int = 2) -> List[Dict]:
        """根据查询自动激活相关技能"""
        if not config.settings.SKILLS_AUTO_ACTIVATION:
            return []
        
        activated_skills = self.activator.auto_activate_for_query(query, max_skills)
        return [skill.to_dict() for skill in activated_skills]
    
    def get_skills_prompt_extension(self) -> str:
        """获取技能的 prompt 扩展内容（用于添加到 Agent instruction）"""
        return self.activator.merge_active_skills_for_prompt()
    
    def get_active_skills(self) -> List[Dict]:
        """获取所有激活的技能"""
        skills = self.registry.get_active_skills()
        return [skill.to_dict() for skill in skills]

# 全局技能管理器实例
skills_manager = SkillsManager()
