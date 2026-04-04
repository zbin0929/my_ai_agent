# -*- coding: utf-8 -*-
"""
LLM 工厂模块
============

功能说明：
    负责创建和管理大语言模型（LLM）实例
    支持多个 LLM 提供商，包括：
    - 智谱 AI (ZhipuAI)
    - OpenAI
    - DeepSeek
    - 阿里云百炼 (DashScope)
    - 其他兼容 OpenAI API 的提供商
    
    特性：
    - 统一的 LLM 创建接口
    - 支持联网搜索（智谱原生支持）
    - 自动从环境变量获取 API Key
    - LLM 实例缓存，避免重复创建

使用示例：
    from core.llm_factory import LLMFactory
    
    factory = LLMFactory(config)
    llm = factory.create()
    llm = factory.create({"provider": "zhipu", "model": "glm-4-flash"})

作者：AI Agent Team
版本：1.0.0
"""

import os
import logging
from typing import Any, Dict, List, Optional

from crewai.llm import LLM

logger = logging.getLogger(__name__)


class LLMFactoryError(Exception):
    """LLM 工厂错误异常类"""
    pass


class LLMFactory:
    """
    LLM 工厂类
    
    负责根据配置创建 LLM 实例，支持多提供商和联网搜索
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化 LLM 工厂
        
        参数：
            config (dict): 完整的系统配置字典
        """
        self.config = config
        
        self.providers: Dict[str, Dict] = {}
        for provider in config.get("llm_providers", []):
            self.providers[provider["id"]] = provider
        
        self.default_llm = config.get("default_llm", {
            "provider": "zhipu",
            "model": "glm-4-flash",
            "temperature": 0.7
        })
        
        self._cache: Dict[str, LLM] = {}
        
        logger.info(f"LLM 工厂初始化完成，已注册 {len(self.providers)} 个提供商")
    
    def create(self, llm_config: Optional[Dict[str, Any]] = None) -> LLM:
        """
        创建 LLM 实例
        
        参数：
            llm_config (dict, optional): LLM 配置，如果为 None 则使用默认配置
        
        返回：
            LLM: CrewAI LLM 实例
        """
        if llm_config is None:
            llm_config = self.default_llm.copy()
        else:
            merged_config = self.default_llm.copy()
            merged_config.update(llm_config)
            llm_config = merged_config
        
        cache_key = self._get_cache_key(llm_config)
        if cache_key in self._cache:
            logger.debug(f"从缓存获取 LLM 实例: {cache_key}")
            return self._cache[cache_key]
        
        provider_id = llm_config.get("provider")
        model_id = llm_config.get("model")
        
        provider = self.providers.get(provider_id)
        if not provider:
            raise LLMFactoryError(f"未知的 LLM 提供商: {provider_id}")
        
        api_key = self._get_api_key(provider)
        base_url = provider.get("base_url")
        
        llm_params = {
            "model": model_id,
            "api_key": api_key,
            "temperature": llm_config.get("temperature", 0.7),
        }
        
        if base_url:
            llm_params["base_url"] = base_url
        
        if provider.get("type") == "zhipu" and llm_config.get("enable_search"):
            search_config = self._build_search_config(llm_config)
            llm_params["tools"] = [search_config]
            logger.info(f"已启用智谱联网搜索，引擎: {llm_config.get('search_engine', 'search_std')}")
        
        try:
            llm = LLM(**llm_params)
            self._cache[cache_key] = llm
            logger.info(f"成功创建 LLM 实例: {provider_id}/{model_id}")
            return llm
        except Exception as e:
            raise LLMFactoryError(f"创建 LLM 失败: {e}")
    
    def _get_api_key(self, provider: Dict) -> str:
        """
        获取提供商的 API Key
        
        参数：
            provider (dict): 提供商配置
        
        返回：
            str: API Key
        """
        env_key = provider.get("env_key")
        if not env_key:
            raise LLMFactoryError(f"提供商 {provider.get('id')} 未配置 env_key")
        
        api_key = os.environ.get(env_key)
        if not api_key:
            raise LLMFactoryError(
                f"API Key 未设置: 请设置环境变量 {env_key}\n"
                f"示例: export {env_key}=your_api_key_here"
            )
        
        return api_key
    
    def _build_search_config(self, llm_config: Dict) -> Dict:
        """
        构建智谱联网搜索配置
        
        参数：
            llm_config (dict): LLM 配置
        
        返回：
            dict: 搜索工具配置
        """
        search_engine = llm_config.get("search_engine", "search_std")
        
        return {
            "type": "web_search",
            "web_search": {
                "enable": True,
                "search_engine": search_engine,
                "search_result": True,
                "count": 5,
                "content_size": "medium"
            }
        }
    
    def _get_cache_key(self, llm_config: Dict) -> str:
        """
        生成配置的缓存键
        
        参数：
            llm_config (dict): LLM 配置
        
        返回：
            str: 缓存键
        """
        key_parts = [
            llm_config.get("provider", ""),
            llm_config.get("model", ""),
            str(llm_config.get("temperature", "")),
            str(llm_config.get("enable_search", "")),
            llm_config.get("search_engine", "")
        ]
        return "|".join(key_parts)
    
    def list_providers(self) -> List[Dict]:
        """
        获取所有提供商列表
        
        返回：
            list: 提供商配置列表
        """
        return list(self.providers.values())
    
    def get_provider(self, provider_id: str) -> Optional[Dict]:
        """
        获取指定提供商配置
        
        参数：
            provider_id (str): 提供商 ID
        
        返回：
            dict: 提供商配置，如果不存在则返回 None
        """
        return self.providers.get(provider_id)
    
    def list_models(self, provider_id: str) -> List[Dict]:
        """
        获取指定提供商的模型列表
        
        参数：
            provider_id (str): 提供商 ID
        
        返回：
            list: 模型配置列表
        """
        provider = self.providers.get(provider_id)
        if not provider:
            return []
        return provider.get("models", [])
    
    def test_connection(self, llm_config: Optional[Dict] = None) -> Dict[str, Any]:
        """
        测试 LLM 连接
        
        参数：
            llm_config (dict, optional): LLM 配置
        
        返回：
            dict: 测试结果，包含 success 和 message 字段
        """
        try:
            llm = self.create(llm_config)
            response = llm.call("你好，请回复'连接成功'")
            
            return {
                "success": True,
                "message": "连接成功",
                "response": str(response)[:100]
            }
        except Exception as e:
            # 隐藏原始错误信息，返回友好提示
            error_str = str(e).lower()
            if any(kw in error_str for kw in ["429", "quota", "余额", "rate_limit"]):
                friendly = "模型服务调用频率超限或余额不足"
            elif any(kw in error_str for kw in ["401", "403", "unauthorized", "invalid_api_key"]):
                friendly = "API Key 认证失败"
            elif any(kw in error_str for kw in ["timeout", "connection"]):
                friendly = "网络连接超时"
            else:
                friendly = "连接失败"
            return {
                "success": False,
                "message": friendly
            }
    
    def clear_cache(self) -> None:
        """清除 LLM 实例缓存"""
        self._cache.clear()
        logger.info("LLM 实例缓存已清除")
