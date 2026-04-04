# -*- coding: utf-8 -*-
"""
多语言支持 (i18n)
=================

支持中文、英文界面切换
"""

import json
import os
from typing import Dict

_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "zh": {},
    "en": {},
}

_current_lang = "zh"


def load_translations(lang_dir: str = None):
    """加载翻译文件"""
    if lang_dir is None:
        lang_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")
    
    for lang in ["zh", "en"]:
        filepath = os.path.join(lang_dir, f"{lang}.json")
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                _TRANSLATIONS[lang] = json.load(f)


def set_language(lang: str):
    """设置当前语言"""
    global _current_lang
    if lang in _TRANSLATIONS:
        _current_lang = lang


def get_language() -> str:
    """获取当前语言"""
    return _current_lang


def t(text_key: str, **kwargs) -> str:
    """
    翻译 text_key 到当前语言的文本
    
    用法: t("app.title") → "AI 助手" 或 "GymClaw"
    支持变量: t("chat.placeholder", name="小助手") → "跟 小助手 说点什么..."
    """
    text = _TRANSLATIONS.get(_current_lang, {}).get(text_key, text_key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


# 初始化加载
load_translations()
