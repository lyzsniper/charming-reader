"""
文件存储服务 - MinIO 对象存储
"""
from minio import Minio
from minio.error import S3Error
from typing import BinaryIO, Optional
import uuid
from io import BytesIO
from datetime import timedelta

from core.config import settings
from core.logger import LoggerFactory

logger = LoggerFactory.get_service_logger(__name__)


class MinioStorageService:
    """MinIO 对象存储服务"""
    
    def __init__(self):
        """初始化 MinIO 客户端"""
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket_name = settings.MINIO_BUCKET
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"✓ MinIO 存储桶已创建: {self.bucket_name}")
            else:
                logger.info(f"✓ MinIO 存储桶已存在: {self.bucket_name}")
        except S3Error as e:
            logger.error(f"✗ MinIO 存储桶创建失败: {e}")
            raise
    
    def upload_file(
        self,
        file_data: BinaryIO,
        original_filename: str,
        content_type: str = "application/pdf"
    ) -> tuple[str, int]:
        """
        上传文件到 MinIO
        
        Args:
            file_data: 文件二进制数据流
            original_filename: 原始文件名
            content_type: 文件类型
            
        Returns:
            tuple[str, int]: (object_name, file_size)
        """
        # 生成唯一的对象名称（UUID + 原始扩展名）
        file_extension = original_filename.split('.')[-1] if '.' in original_filename else 'pdf'
        object_name = f"{uuid.uuid4()}.{file_extension}"
        
        try:
            # 如果 file_data 是文件流，需要先读取以获取大小
            if hasattr(file_data, 'read'):
                file_content = file_data.read()
                file_size = len(file_content)
                file_stream = BytesIO(file_content)
            else:
                file_content = file_data
                file_size = len(file_content)
                file_stream = BytesIO(file_content)
            
            # 上传到 MinIO
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_stream,
                length=file_size,
                content_type=content_type
            )
            
            logger.info(f"✓ 文件上传成功: {object_name} ({file_size} bytes)")
            return object_name, file_size
            
        except S3Error as e:
            logger.error(f"✗ 文件上传失败: {e}")
            raise
    
    def get_presigned_url(self, object_name: str, expires: timedelta = timedelta(days=7)) -> str:
        """
        生成文件的预签名下载链接
        
        Args:
            object_name: MinIO 对象名称
            expires: 链接有效期，默认 7 天
            
        Returns:
            str: 预签名 URL
        """
        try:
            url = self.client.get_presigned_url(
                "GET",
                self.bucket_name,
                object_name,
                expires=expires
            )
            return url
        except S3Error as e:
            logger.error(f"✗ 生成预签名链接失败: {e}")
            return ""

    def download_file(self, object_name: str) -> bytes:
        """
        从 MinIO 下载文件
        
        Args:
            object_name: 对象名称
            
        Returns:
            bytes: 文件内容
        """
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            file_data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"✓ 文件下载成功: {object_name}")
            return file_data
            
        except S3Error as e:
            logger.error(f"✗ 文件下载失败: {object_name}, error: {e}")
            raise
    
    def delete_file(self, object_name: str) -> bool:
        """
        从 MinIO 删除文件
        
        Args:
            object_name: 对象名称
            
        Returns:
            bool: 是否删除成功
        """
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"✓ 文件删除成功: {object_name}")
            return True
            
        except S3Error as e:
            logger.error(f"✗ 文件删除失败: {object_name}, error: {e}")
            return False
    
    def get_file_url(self, object_name: str, expires_in: int = 3600) -> str:
        """
        获取文件的预签名 URL（临时访问链接）
        
        Args:
            object_name: 对象名称
            expires_in: 过期时间（秒），默认 1 小时
            
        Returns:
            str: 预签名 URL
        """
        try:
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires_in
            )
            logger.info(f"✓ 生成预签名 URL: {object_name}")
            return url
            
        except S3Error as e:
            logger.error(f"✗ 生成预签名 URL 失败: {object_name}, error: {e}")
            raise
    
    def file_exists(self, object_name: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            object_name: 对象名称
            
        Returns:
            bool: 文件是否存在
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False


# 单例模式
_storage_service: Optional[MinioStorageService] = None

def get_storage_service() -> MinioStorageService:
    """获取存储服务实例（单例）"""
    global _storage_service
    if _storage_service is None:
        _storage_service = MinioStorageService()
    return _storage_service

