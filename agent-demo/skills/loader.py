"""
Skill Loader - 扫描和加载技能文件
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from dataclasses import dataclass

@dataclass
class SkillMetadata:
    """技能元数据"""
    name: str
    description: str
    triggers: List[str]
    version: str
    file_path: str
    
class SkillLoader:
    """
    技能加载器
    负责扫描技能目录，解析 SKILL.md 文件，提取元数据
    """
    
    def __init__(self, skills_dir: str = ".claude/skills"):
        """
        初始化加载器
        
        Args:
            skills_dir: 技能目录路径
        """
        self.skills_dir = Path(skills_dir)
        self._metadata_cache: Dict[str, SkillMetadata] = {}
        self._content_cache: Dict[str, str] = {}
    
    def scan_skills(self) -> List[SkillMetadata]:
        """
        扫描技能目录，加载所有技能的元数据
        
        Returns:
            技能元数据列表
        """
        skills = []
        
        if not self.skills_dir.exists():
            print(f"Skills directory not found: {self.skills_dir}")
            return skills
        
        # 遍历技能目录
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                
                if skill_file.exists():
                    try:
                        metadata = self._parse_skill_metadata(skill_file)
                        if metadata:
                            skills.append(metadata)
                            # 缓存元数据
                            self._metadata_cache[metadata.name] = metadata
                    except Exception as e:
                        print(f"Error loading skill from {skill_file}: {e}")
        
        return skills
    
    def _parse_skill_metadata(self, skill_file: Path) -> Optional[SkillMetadata]:
        """
        解析技能文件的元数据（YAML frontmatter）
        
        Args:
            skill_file: SKILL.md 文件路径
        
        Returns:
            SkillMetadata 对象
        """
        with open(skill_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取 YAML frontmatter
        # 格式: ---\n[yaml content]\n---
        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.search(frontmatter_pattern, content, re.DOTALL)
        
        if not match:
            print(f"No frontmatter found in {skill_file}")
            return None
        
        yaml_content = match.group(1)
        
        try:
            metadata_dict = yaml.safe_load(yaml_content)
            
            # 验证必需字段
            required_fields = ['name', 'description', 'triggers', 'version']
            for field in required_fields:
                if field not in metadata_dict:
                    print(f"Missing required field '{field}' in {skill_file}")
                    return None
            
            return SkillMetadata(
                name=metadata_dict['name'],
                description=metadata_dict['description'],
                triggers=metadata_dict['triggers'],
                version=metadata_dict['version'],
                file_path=str(skill_file)
            )
        except yaml.YAMLError as e:
            print(f"Error parsing YAML in {skill_file}: {e}")
            return None
    
    def load_skill_content(self, skill_name: str) -> Optional[str]:
        """
        加载技能的完整内容（懒加载）
        
        Args:
            skill_name: 技能名称
        
        Returns:
            技能的完整 markdown 内容
        """
        # 检查缓存
        if skill_name in self._content_cache:
            return self._content_cache[skill_name]
        
        # 从元数据获取文件路径
        if skill_name not in self._metadata_cache:
            print(f"Skill '{skill_name}' not found in metadata cache")
            return None
        
        metadata = self._metadata_cache[skill_name]
        
        try:
            with open(metadata.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 移除 frontmatter，只保留主体内容
            frontmatter_pattern = r'^---\s*\n.*?\n---\s*\n'
            content_body = re.sub(frontmatter_pattern, '', content, count=1, flags=re.DOTALL)
            
            # 缓存内容
            self._content_cache[skill_name] = content_body
            
            return content_body
        except Exception as e:
            print(f"Error loading content for skill '{skill_name}': {e}")
            return None
    
    def get_skill_statistics(self) -> Dict:
        """
        获取技能统计信息
        
        Returns:
            统计信息字典
        """
        total_skills = len(self._metadata_cache)
        
        # 统计触发词数量
        total_triggers = sum(
            len(meta.triggers) for meta in self._metadata_cache.values()
        )
        
        # 统计已缓存内容的技能
        cached_content = len(self._content_cache)
        
        return {
            "total_skills": total_skills,
            "total_triggers": total_triggers,
            "cached_content": cached_content,
            "skills": list(self._metadata_cache.keys())
        }
    
    def clear_cache(self):
        """清除内容缓存（保留元数据缓存）"""
        self._content_cache.clear()
