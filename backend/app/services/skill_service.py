"""
Skill Service 层
实现Skill的业务逻辑，包括混合模式加载（文件系统+数据库）
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
import os
from pathlib import Path
import yaml

from dao.skill_dao import SkillDAO, SkillResourceDAO
from models.sql import Skill
from core.config import settings


class SkillService:
    """Skill业务服务"""
    
    def __init__(self):
        self.skills_dir = Path(settings.SKILLS_DIR)
    
    async def sync_from_filesystem(self, db: Session) -> Dict[str, Any]:
        """同步文件系统中的Skills到数据库"""
        synced_count = 0
        skipped_count = 0
        error_count = 0
        
        if not self.skills_dir.exists():
            return {
                "synced": 0,
                "skipped": 0,
                "errors": 0,
                "message": f"Skills directory not found: {self.skills_dir}"
            }
        
        # 遍历.claude/skills/目录
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            
            try:
                # 解析SKILL.md文件
                skill_data = self._parse_skill_file(skill_file)
                
                if not skill_data:
                    error_count += 1
                    continue
                
                # 检查数据库中是否已存在
                existing_skill = SkillDAO.get_by_name(db, skill_data["name"])
                
                if existing_skill:
                    # 比较版本，如果文件版本更新则更新数据库
                    if self._compare_versions(skill_data["version"], existing_skill.version) > 0:
                        # 更新数据库记录
                        SkillDAO.update(db, existing_skill.id, {
                            "version": skill_data["version"],
                            "description": skill_data.get("description"),
                            "display_name": skill_data.get("display_name"),
                            "triggers": skill_data.get("triggers", []),
                            "content": skill_data.get("content"),
                            "file_path": str(skill_file),
                            "source_type": "file"
                        })
                        synced_count += 1
                    else:
                        skipped_count += 1
                else:
                    # 创建新记录
                    skill_create_data = {
                        "name": skill_data["name"],
                        "display_name": skill_data.get("display_name", skill_data["name"]),
                        "description": skill_data.get("description", ""),
                        "version": skill_data["version"],
                        "source_type": "file",
                        "file_path": str(skill_file),
                        "content": skill_data.get("content", ""),
                        "category": skill_data.get("category", "general"),
                        "tags": skill_data.get("tags", []),
                        "triggers": skill_data.get("triggers", []),
                        "status": "active",
                        "author": skill_data.get("author", "system")
                    }
                    
                    SkillDAO.create(db, skill_create_data)
                    synced_count += 1
                    
            except Exception as e:
                print(f"Error syncing skill from {skill_file}: {e}")
                error_count += 1
        
        return {
            "synced": synced_count,
            "skipped": skipped_count,
            "errors": error_count,
            "message": f"Synchronized {synced_count} skills, skipped {skipped_count}, errors {error_count}"
        }
    
    def _parse_skill_file(self, skill_file: Path) -> Optional[Dict[str, Any]]:
        """解析SKILL.md文件，提取frontmatter和内容"""
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析YAML frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter_text = parts[1]
                    body_content = parts[2].strip()
                    
                    frontmatter = yaml.safe_load(frontmatter_text)
                    
                    # 必需字段检查
                    if not frontmatter.get('name') or not frontmatter.get('version'):
                        return None
                    
                    return {
                        "name": frontmatter.get('name'),
                        "display_name": frontmatter.get('display_name'),
                        "description": frontmatter.get('description'),
                        "version": frontmatter.get('version'),
                        "triggers": frontmatter.get('triggers', []),
                        "category": frontmatter.get('category', 'general'),
                        "tags": frontmatter.get('tags', []),
                        "author": frontmatter.get('author'),
                        "content": body_content
                    }
            
            return None
            
        except Exception as e:
            print(f"Error parsing skill file {skill_file}: {e}")
            return None
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """比较版本号，返回 1（version1>version2）, 0（相等）, -1（version1<version2）"""
        try:
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            # 补齐长度
            max_len = max(len(v1_parts), len(v2_parts))
            v1_parts.extend([0] * (max_len - len(v1_parts)))
            v2_parts.extend([0] * (max_len - len(v2_parts)))
            
            for v1, v2 in zip(v1_parts, v2_parts):
                if v1 > v2:
                    return 1
                elif v1 < v2:
                    return -1
            
            return 0
        except:
            return 0
    
    async def get_skill_content(self, db: Session, skill_id: UUID) -> Optional[str]:
        """获取Skill内容（支持文件和数据库两种来源）"""
        skill = SkillDAO.get_by_id(db, skill_id)
        if not skill:
            return None
        
        # 如果来源是文件系统，从文件读取
        if skill.source_type == "file" and skill.file_path:
            try:
                with open(skill.file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 移除frontmatter，只返回内容部分
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        return parts[2].strip()
                
                return content
            except Exception as e:
                print(f"Error reading skill file {skill.file_path}: {e}")
                # 如果文件读取失败，返回数据库中的内容
                return skill.content
        
        # 否则从数据库返回
        return skill.content
    
    async def create_skill(self, db: Session, skill_data: Dict[str, Any]) -> Skill:
        """创建新技能（存储到数据库）"""
        # 设置source_type为database
        skill_data["source_type"] = "database"
        skill_data["status"] = skill_data.get("status", "active")
        
        return SkillDAO.create(db, skill_data)
    
    async def update_skill(self, db: Session, skill_id: UUID, updates: Dict[str, Any]) -> Optional[Skill]:
        """更新技能"""
        return SkillDAO.update(db, skill_id, updates)
    
    async def delete_skill(self, db: Session, skill_id: UUID) -> bool:
        """删除技能"""
        return SkillDAO.delete(db, skill_id)
    
    async def search_skills(
        self,
        db: Session,
        query: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Skill]:
        """搜索技能"""
        if query:
            return SkillDAO.search(db, query, category, status, skip, limit)
        else:
            return SkillDAO.list_all(db, category, status, None, skip, limit)
    
    async def get_popular_skills(self, db: Session, limit: int = 10) -> List[Skill]:
        """获取热门技能"""
        return SkillDAO.get_popular_skills(db, limit)
    
    async def get_skill_by_id(self, db: Session, skill_id: UUID) -> Optional[Skill]:
        """根据ID获取技能"""
        return SkillDAO.get_by_id(db, skill_id)
    
    async def get_skill_by_name(self, db: Session, name: str) -> Optional[Skill]:
        """根据名称获取技能"""
        return SkillDAO.get_by_name(db, name)
    
    async def list_skills(
        self,
        db: Session,
        category: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[Skill]:
        """列出所有技能"""
        return SkillDAO.list_all(db, category, status, None, skip, limit)
    
    async def count_skills(
        self,
        db: Session,
        category: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None
    ) -> int:
        """统计技能数量"""
        return SkillDAO.count(db, category, status, query)


# 创建全局单例
skill_service = SkillService()
