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
        # 将相对路径转换为绝对路径
        skills_dir_path = Path(skills_dir)
        if not skills_dir_path.is_absolute():
            # 如果是相对路径，从项目根目录开始
            # loader.py在 backend/app/skills/loader.py
            # 项目根目录在 backend/ 的上一级
            current_file = Path(__file__)  # backend/app/skills/loader.py
            project_root = current_file.parent.parent.parent.parent  # 从loader.py到项目根目录
            skills_dir_path = project_root / skills_dir
        
        self.skills_dir = skills_dir_path
        self._metadata_cache: Dict[str, SkillMetadata] = {}
        self._content_cache: Dict[str, str] = {}
        
        print(f"[SkillLoader] Initialized: skills_dir={skills_dir}, absolute_path={self.skills_dir.resolve()}")
    
    def scan_skills(self) -> List[SkillMetadata]:
        """
        扫描技能目录，加载所有技能的元数据
        
        Returns:
            技能元数据列表
        """
        skills = []
        
        # self.skills_dir 已经是绝对路径（在__init__中处理）
        skills_dir_path = self.skills_dir
        
        # 使用英文日志避免编码问题
        print(f"[scan_skills] Skills directory: {skills_dir_path} (absolute: {skills_dir_path.resolve()})")
        print(f"[scan_skills] Directory exists: {skills_dir_path.exists()}")
        
        if not skills_dir_path.exists():
            print(f"[scan_skills] WARNING: Skills directory not found: {skills_dir_path}")
            return skills
        
        # 遍历技能目录
        skill_dirs = list(skills_dir_path.iterdir())
        print(f"[scan_skills] Found {len(skill_dirs)} subdirectories/files")
        
        for skill_dir in skill_dirs:
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                print(f"[scan_skills] Checking skill directory: {skill_dir.name}, SKILL.md exists: {skill_file.exists()}")
                
                if skill_file.exists():
                    try:
                        print(f"[scan_skills] Parsing: {skill_file}")
                        metadata = self._parse_skill_metadata(skill_file)
                        if metadata:
                            skills.append(metadata)
                            # 缓存元数据
                            self._metadata_cache[metadata.name] = metadata
                            print(f"[scan_skills] Successfully loaded skill: {metadata.name}")
                        else:
                            print(f"[scan_skills] Failed to parse: {skill_file} (returned None)")
                    except Exception as e:
                        print(f"[scan_skills] Error loading skill from {skill_file}: {type(e).__name__}: {e}")
                        import traceback
                        traceback.print_exc()
        
        print(f"[scan_skills] Total loaded: {len(skills)} skills")
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
            
            # 调试：打印加载的skill信息
            skill_name = metadata_dict['name']
            triggers = metadata_dict.get('triggers', [])
            # 避免编码问题，只打印基本信息
            print(f"Loaded skill: {skill_name}, triggers count: {len(triggers)}")
            
            return SkillMetadata(
                name=metadata_dict['name'],
                description=metadata_dict['description'],
                triggers=metadata_dict['triggers'],
                version=metadata_dict['version'],
                file_path=str(skill_file)
            )
        except yaml.YAMLError as e:
            print(f"Error parsing YAML in {skill_file}: {e}")
            print(f"YAML content: {yaml_content[:200]}...")
            return None
        except Exception as e:
            print(f"Unexpected error parsing skill {skill_file}: {e}")
            import traceback
            traceback.print_exc()
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
    
    def load_skill_resource(self, skill_name: str, resource_path: str) -> Optional[str]:
        """
        加载技能的资源文件（如 references/, scripts/ 下的文件）
        
        Args:
            skill_name: 技能名称
            resource_path: 相对于技能目录的资源路径
        
        Returns:
            资源文件内容
        """
        if skill_name not in self._metadata_cache:
            return None
        
        metadata = self._metadata_cache[skill_name]
        skill_dir = Path(metadata.file_path).parent
        resource_file = skill_dir / resource_path
        
        if not resource_file.exists():
            print(f"Resource not found: {resource_file}")
            return None
        
        try:
            with open(resource_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading resource '{resource_path}' for skill '{skill_name}': {e}")
            return None
    
    def validate_skill(self, skill_name: str) -> bool:
        """
        验证技能的完整性
        
        Args:
            skill_name: 技能名称
        
        Returns:
            是否通过验证
        """
        if skill_name not in self._metadata_cache:
            return False
        
        metadata = self._metadata_cache[skill_name]
        
        # 检查文件存在
        if not Path(metadata.file_path).exists():
            return False
        
        # 检查内容可加载
        content = self.load_skill_content(skill_name)
        if not content:
            return False
        
        # 检查内容不为空
        if len(content.strip()) < 100:  # 至少100字符
            return False
        
        return True
    
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
    
    def reload_skill(self, skill_name: str) -> bool:
        """
        重新加载指定技能
        
        Args:
            skill_name: 技能名称
        
        Returns:
            是否成功重新加载
        """
        if skill_name in self._content_cache:
            del self._content_cache[skill_name]
        
        if skill_name in self._metadata_cache:
            metadata = self._metadata_cache[skill_name]
            skill_file = Path(metadata.file_path)
            
            if skill_file.exists():
                new_metadata = self._parse_skill_metadata(skill_file)
                if new_metadata:
                    self._metadata_cache[skill_name] = new_metadata
                    return True
        
        return False

