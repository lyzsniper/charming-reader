"""
翻译服务
使用 translators 库提供多语言翻译功能
"""
from typing import Optional, List, Dict, Any
from core.logger import LoggerFactory

logger = LoggerFactory.get_service_logger(__name__)

try:
    import translators as ts
    TRANSLATORS_AVAILABLE = True
except ImportError:
    TRANSLATORS_AVAILABLE = False
    logger.warning("translators 库未安装，翻译功能将不可用")


class TranslationService:
    """翻译服务"""
    
    # 支持的翻译服务列表（常用且稳定的）
    SUPPORTED_PROVIDERS = [
        'google',      # Google Translate
        'baidu',       # 百度翻译
        'alibaba',     # 阿里翻译
        'youdao',      # 有道翻译
        'tencent',     # 腾讯翻译
        'deepl',       # DeepL（需要 API key）
        'bing',        # Bing Translator
        'sogou',       # 搜狗翻译
    ]
    
    @staticmethod
    def is_available() -> bool:
        """检查翻译服务是否可用"""
        return TRANSLATORS_AVAILABLE
    
    @staticmethod
    def translate(
        text: str,
        from_language: str = 'auto',
        to_language: str = 'en',
        provider: str = 'google',
        **kwargs
    ) -> Dict[str, Any]:
        """
        翻译文本
        
        Args:
            text: 要翻译的文本
            from_language: 源语言代码（'auto' 表示自动检测）
            to_language: 目标语言代码
            provider: 翻译服务提供商
            **kwargs: 其他参数（如 API keys 等）
        
        Returns:
            包含翻译结果的字典
        """
        if not TRANSLATORS_AVAILABLE:
            raise RuntimeError("translators 库未安装，请先安装: pip install translators")
        
        if provider not in TranslationService.SUPPORTED_PROVIDERS:
            logger.warning(f"不支持的翻译服务: {provider}，使用默认服务: google")
            provider = 'google'
        
        try:
            logger.info(f"开始翻译: provider={provider}, from={from_language}, to={to_language}, text_length={len(text)}")
            logger.debug(f"原文前100字符: {text[:100]}")
            
            # 调用 translators 库进行翻译
            # 根据 translators 库的文档，正确的调用方式是：
            # ts.translate_text(query_text, translator, from_language, to_language, ...)
            # 或者使用关键字参数
            
            # 准备参数
            # 如果 from_language 是 'auto'，某些服务可能不支持，尝试不传或设为 None
            translate_kwargs = {
                'translator': provider,
                'to_language': to_language,
            }
            
            # 处理源语言参数
            if from_language and from_language != 'auto':
                translate_kwargs['from_language'] = from_language
            
            # 合并额外的 kwargs
            translate_kwargs.update(kwargs)
            
            # 调用 translators 库进行翻译
            # 根据 translators 库的常见用法，使用位置参数和关键字参数组合
            translated_text = None
            
            # 方式1: 使用 query_text 关键字参数（最常用）
            try:
                if from_language and from_language != 'auto':
                    translated_text = ts.translate_text(
                        query_text=text,
                        translator=provider,
                        from_language=from_language,
                        to_language=to_language,
                        **kwargs
                    )
                else:
                    # 如果 from_language 是 'auto' 或 None，不传该参数让服务自动检测
                    translated_text = ts.translate_text(
                        query_text=text,
                        translator=provider,
                        to_language=to_language,
                        **kwargs
                    )
            except (TypeError, Exception) as e1:
                logger.warning(f"方式1失败 ({type(e1).__name__}: {str(e1)[:100]})，尝试方式2")
                try:
                    # 方式2: 第一个位置参数是文本
                    if from_language and from_language != 'auto':
                        translated_text = ts.translate_text(
                            text,
                            translator=provider,
                            from_language=from_language,
                            to_language=to_language,
                            **kwargs
                        )
                    else:
                        translated_text = ts.translate_text(
                            text,
                            translator=provider,
                            to_language=to_language,
                            **kwargs
                        )
                except Exception as e2:
                    logger.error(f"方式2也失败: {type(e2).__name__}: {str(e2)[:100]}")
                    raise e2
            
            # 验证翻译结果
            if not translated_text:
                raise ValueError("翻译结果为空")
            
            # 检查翻译结果是否与原文相同（可能是翻译失败）
            if translated_text.strip() == text.strip() and len(text.strip()) > 5:
                logger.warning(f"翻译结果与原文相同，可能翻译失败: provider={provider}, from={from_language}, to={to_language}")
                # 如果源语言是 'auto'，尝试明确指定源语言
                if from_language == 'auto':
                    # 尝试检测语言或使用常见语言
                    logger.info("尝试使用明确的语言代码重新翻译...")
                    # 简单检测：如果包含中文字符，可能是中文
                    import re
                    if re.search(r'[\u4e00-\u9fff]', text):
                        try:
                            translate_kwargs['from_language'] = 'zh'
                            translated_text = ts.translate_text(query_text=text, **translate_kwargs)
                        except:
                            pass
                    # 如果主要是英文，尝试 en
                    elif re.search(r'^[a-zA-Z\s\.,!?;:\'"]+$', text[:100]):
                        try:
                            translate_kwargs['from_language'] = 'en'
                            translated_text = ts.translate_text(query_text=text, **translate_kwargs)
                        except:
                            pass
            
            logger.info(f"翻译成功: provider={provider}, result_length={len(translated_text)}")
            logger.debug(f"译文前100字符: {translated_text[:100]}")
            
            return {
                "original_text": text,
                "translated_text": translated_text,
                "from_language": from_language,
                "to_language": to_language,
                "provider": provider,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"翻译失败: provider={provider}, error={type(e).__name__}: {str(e)}", exc_info=True)
            return {
                "original_text": text,
                "translated_text": None,
                "from_language": from_language,
                "to_language": to_language,
                "provider": provider,
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def batch_translate(
        texts: List[str],
        from_language: str = 'auto',
        to_language: str = 'en',
        provider: str = 'google',
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        批量翻译文本
        
        Args:
            texts: 要翻译的文本列表
            from_language: 源语言代码
            to_language: 目标语言代码
            provider: 翻译服务提供商
            **kwargs: 其他参数
        
        Returns:
            翻译结果列表
        """
        results = []
        for text in texts:
            result = TranslationService.translate(
                text=text,
                from_language=from_language,
                to_language=to_language,
                provider=provider,
                **kwargs
            )
            results.append(result)
        return results
    
    @staticmethod
    def get_supported_languages(provider: str = 'google') -> List[str]:
        """
        获取支持的语言列表
        
        Args:
            provider: 翻译服务提供商
        
        Returns:
            支持的语言代码列表
        """
        if not TRANSLATORS_AVAILABLE:
            return []
        
        try:
            # translators 库可能没有直接的 get_languages 方法
            # 这里返回常用语言列表作为参考
            # 实际支持的语言取决于具体的翻译服务提供商
            common_languages = [
                'en', 'zh', 'zh-CN', 'zh-TW', 'ja', 'ko', 'fr', 'de', 'es', 'ru',
                'it', 'pt', 'ar', 'hi', 'th', 'vi', 'id', 'tr', 'pl', 'nl'
            ]
            return common_languages
        except Exception as e:
            logger.warning(f"获取支持语言失败: provider={provider}, error={str(e)}")
            return []
    
    @staticmethod
    def detect_language(text: str, provider: str = 'google') -> Optional[str]:
        """
        检测文本语言
        
        注意：translators 库可能不直接支持语言检测
        这里提供一个基础实现，实际使用时可能需要使用其他语言检测库
        
        Args:
            text: 要检测的文本
            provider: 翻译服务提供商（某些服务可能支持语言检测）
        
        Returns:
            检测到的语言代码，如果检测失败返回 None
        """
        if not TRANSLATORS_AVAILABLE:
            return None
        
        try:
            # 尝试使用 translators 库的语言检测功能（如果可用）
            # 注意：不是所有翻译服务都支持语言检测
            if hasattr(ts, 'detect_language'):
                detected = ts.detect_language(query_text=text, translator=provider)
                return detected
            else:
                # 如果 translators 库没有 detect_language 方法
                # 可以尝试使用 langdetect 或其他语言检测库
                # 这里返回 None，表示不支持
                logger.warning(f"translators 库不支持 detect_language 方法，provider={provider}")
                return None
        except Exception as e:
            logger.warning(f"语言检测失败: provider={provider}, error={str(e)}")
            return None
