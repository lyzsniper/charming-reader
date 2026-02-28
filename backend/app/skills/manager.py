"""
Skills Manager - 统一的技能管理接口
整合 Loader, Registry, Activator 提供高层 API
支持混合模式：从文件系统和数据库加载Skills
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from .loader import SkillLoader
from .registry import SkillRegistry, Skill
from .activator import SkillActivator
from core.config import settings

class SkillsManager:
    """
    技能管理器（单例模式）
    提供统一的技能管理接口
    """
    
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
        self.loader = SkillLoader(skills_dir=settings.SKILLS_DIR)
        self.registry = SkillRegistry()
        self.activator = SkillActivator(
            loader=self.loader,
            registry=self.registry,
            max_concurrent_skills=settings.SKILLS_MAX_CONCURRENT
        )
        
        # 加载所有技能
        self._load_all_skills()
        
        self._initialized = True
    
    def _load_all_skills(self, db: Optional[Session] = None):
        """
        加载所有技能的元数据到注册表
        混合模式：先加载文件系统Skills，再加载数据库Skills
        """
        print(f"[SkillsManager] Starting to load skills from: {self.loader.skills_dir}")
        
        # 1. 从文件系统加载
        skills_metadata = self.loader.scan_skills()
        print(f"[SkillsManager] Scanned {len(skills_metadata)} skills from filesystem")
        
        for metadata in skills_metadata:
            self.registry.register_skill(
                name=metadata.name,
                description=metadata.description,
                triggers=metadata.triggers,
                version=metadata.version,
                file_path=metadata.file_path
            )
            print(f"[SkillsManager] Registered skill: {metadata.name} ({len(metadata.triggers)} triggers)")
        
        # 2. 从数据库加载（如果提供了db session）
        if db:
            try:
                from dao.skill_dao import SkillDAO
                db_skills = SkillDAO.list_all(db, status='active')
                print(f"[SkillsManager] Found {len(db_skills)} skills in database")
                
                for db_skill in db_skills:
                    # 检查是否已从文件系统加载（文件系统优先级更高）
                    existing_skill = self.registry.get_skill(db_skill.name)
                    if existing_skill and existing_skill.file_path:
                        print(f"[SkillsManager] Skipping database skill {db_skill.name} (filesystem version exists)")
                        continue
                    
                    # 注册数据库中的技能
                    self.registry.register_skill(
                        name=db_skill.name,
                        description=db_skill.description or "",
                        triggers=db_skill.triggers or [],
                        version=db_skill.version,
                        file_path=None  # 标记为数据库来源
                    )
                    print(f"[SkillsManager] Registered database skill: {db_skill.name}")
            except Exception as e:
                print(f"[SkillsManager] Error loading skills from database: {e}")
        
        total_skills = len(self.registry.get_all_skills())
        print(f"[SkillsManager] Total loaded and registered: {total_skills} skills")
        
        # 验证GitHub skill是否加载
        github_skill = self.registry.get_skill("github-integration")
        if github_skill:
            print(f"[SkillsManager] GitHub skill found: {github_skill.name}, triggers: {len(github_skill.triggers)}")
        else:
            print(f"[SkillsManager] WARNING: GitHub skill NOT found in registry!")
    
    def list_all_skills(self) -> List[Dict]:
        """
        列出所有可用技能
        
        Returns:
            技能信息列表
        """
        skills = self.registry.get_all_skills()
        return [skill.to_dict() for skill in skills]
    
    def get_skill_info(self, skill_name: str) -> Optional[Dict]:
        """
        获取指定技能的详细信息
        
        Args:
            skill_name: 技能名称
        
        Returns:
            技能信息字典
        """
        skill = self.registry.get_skill(skill_name)
        if skill:
            return skill.to_dict()
        return None
    
    def activate_skill(self, skill_name: str) -> bool:
        """
        激活指定技能
        
        Args:
            skill_name: 技能名称
        
        Returns:
            是否成功激活
        """
        return self.activator.activate_skill(skill_name)
    
    def deactivate_skill(self, skill_name: str) -> bool:
        """
        停用指定技能
        
        Args:
            skill_name: 技能名称
        
        Returns:
            是否成功停用
        """
        return self.activator.deactivate_skill(skill_name)
    
    def get_active_skills(self) -> List[Dict]:
        """
        获取所有激活的技能
        
        Returns:
            激活技能列表
        """
        skills = self.registry.get_active_skills()
        return [skill.to_dict() for skill in skills]
    
    def auto_activate_for_query(self, query: str, max_skills: int = 2) -> List[Dict]:
        """
        根据查询自动激活相关技能
        
        Args:
            query: 用户查询
            max_skills: 最多激活的技能数量
        
        Returns:
            激活的技能列表
        """
        if not settings.SKILLS_AUTO_ACTIVATION:
            return []
        
        activated_skills = self.activator.auto_activate_for_query(query, max_skills)
        return [skill.to_dict() for skill in activated_skills]
    
    def suggest_skills(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        为查询推荐技能
        
        Args:
            query: 用户查询
            top_k: 推荐数量
        
        Returns:
            推荐技能列表
        """
        return self.activator.suggest_skills_for_query(query, top_k)
    
    def get_skills_prompt_extension(self) -> str:
        """
        获取技能的 prompt 扩展内容（用于添加到 Agent instruction）
        
        Returns:
            合并的技能内容
        """
        return self.activator.merge_active_skills_for_prompt()
    
    def get_statistics(self) -> Dict:
        """
        获取技能系统统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "loader": self.loader.get_skill_statistics(),
            "registry": self.registry.get_statistics(),
            "activator": self.activator.get_activation_summary()
        }
    
    def reload_skills(self, db: Optional[Session] = None):
        """
        重新加载所有技能
        
        Args:
            db: 数据库会话（可选）
        """
        # 清空注册表
        self.registry.clear()
        
        # 清空加载器缓存
        self.loader.clear_cache()
        
        # 重新加载
        self._load_all_skills(db)
    
    async def sync_with_database(self, db: Session) -> Dict:
        """
        与数据库同步Skills
        
        Args:
            db: 数据库会话
        
        Returns:
            同步结果统计
        """
        from services.skill_service import skill_service
        result = await skill_service.sync_from_filesystem(db)
        
        # 重新加载技能
        self.reload_skills(db)
        
        return result
    
    async def activate_skill_with_logging(
        self,
        skill_name: str,
        db: Optional[Session] = None,
        session_id: Optional[str] = None,
        query_text: Optional[str] = None
    ) -> bool:
        """
        激活技能并记录到数据库
        
        Args:
            skill_name: 技能名称
            db: 数据库会话
            session_id: 会话ID
            query_text: 查询文本
        
        Returns:
            是否成功激活
        """
        # 激活技能
        success = self.activator.activate_skill(skill_name)
        
        # 如果激活成功且提供了数据库会话，记录日志
        if success and db and session_id:
            try:
                from services.runtime_monitor_service import runtime_monitor_service
                from dao.skill_dao import SkillDAO
                
                # 获取技能ID
                db_skill = SkillDAO.get_by_name(db, skill_name)
                if db_skill:
                    await runtime_monitor_service.record_skill_activation(
                        db=db,
                        skill_id=db_skill.id,
                        session_id=session_id,
                        activation_reason="manual",
                        query_text=query_text
                    )
            except Exception as e:
                print(f"[SkillsManager] Error logging skill activation: {e}")
        
        return success
    
    def reset(self):
        """重置技能系统（停用所有技能）"""
        self.activator.deactivate_all()

# 全局技能管理器实例
skills_manager = SkillsManager()

