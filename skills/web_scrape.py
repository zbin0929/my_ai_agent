# -*- coding: utf-8 -*-
"""
网页抓取技能
============

抓取指定 URL 的网页内容，提取正文和元信息。
支持直接 httpx 抓取（轻量）和 Playwright 抓取（JS 渲染）两种模式。
"""

import os
import sys
import re
import ipaddress
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

import httpx

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 20000
REQUEST_TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# SSRF防护：禁止访问的IP范围
BLOCKED_IP_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),      # 本地回环
    ipaddress.ip_network("10.0.0.0/8"),       # 私有网络A类
    ipaddress.ip_network("172.16.0.0/12"),    # 私有网络B类
    ipaddress.ip_network("192.168.0.0/16"),   # 私有网络C类
    ipaddress.ip_network("169.254.0.0/16"),   # 链路本地
    ipaddress.ip_network("0.0.0.0/8"),       # 当前网络
    ipaddress.ip_network("::1/128"),          # IPv6回环
    ipaddress.ip_network("fc00::/7"),        # IPv6私有网络
    ipaddress.ip_network("fe80::/10"),        # IPv6链路本地
]

# SSRF防护：禁止访问的端口
BLOCKED_PORTS = {22, 23, 25, 53, 110, 143, 445, 3306, 3389, 5432, 6379, 9200, 9300}


def _is_private_ip(ip_str: str) -> bool:
    """检查IP是否为私有/内网IP，防止SSRF攻击"""
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in BLOCKED_IP_RANGES:
            if ip in network:
                return True
        return False
    except ValueError:
        return False


def _is_blocked_port(port: int) -> bool:
    """检查端口是否被禁止访问"""
    return port in BLOCKED_PORTS


def _validate_url(url: str) -> tuple[bool, str]:
    """
    验证URL是否安全，防止SSRF攻击
    返回: (is_safe, error_message)
    """
    try:
        parsed = urlparse(url)
        
        # 只允许http和https协议
        if parsed.scheme not in ("http", "https"):
            return False, f"不支持的协议: {parsed.scheme}"
        
        if not parsed.hostname:
            return False, "URL缺少主机名"
        
        # 检查是否为IP地址直接访问
        hostname = parsed.hostname
        try:
            ip = ipaddress.ip_address(hostname)
            # 是IP地址，检查是否在禁止范围内
            if _is_private_ip(hostname):
                return False, "禁止访问内网IP地址"
        except ValueError:
            # 不是IP地址，是域名
            # 检查常见内网域名模式
            blocked_patterns = [
                r"^localhost$",
                r"^127\.\d+\.\d+\.\d+$",
                r"^0\.\d+\.\d+\.\d+$",
                r"^10\.\d+\.\d+\.\d+$",
                r"^192\.168\.\d+\.\d+$",
                r"^172\.(1[6-9]|2\d|3[01])\.\d+\.\d+$",
                r".*\.internal$",
                r".*\.local$",
                r".*\.localhost$",
            ]
            for pattern in blocked_patterns:
                if re.match(pattern, hostname, re.IGNORECASE):
                    return False, "禁止访问内网地址"
        
        # 检查端口
        port = parsed.port
        if port is None:
            port = 443 if parsed.scheme == "https" else 80
        if _is_blocked_port(port):
            return False, f"禁止访问端口: {port}"
        
        return True, ""
    except Exception as e:
        return False, f"URL验证失败: {e}"


def extract_urls(text: str):
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(pattern, text)


def clean_html(html: str) -> str:
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<header[^>]*>.*?</header>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=re.DOTALL | re.IGNORECASE)

    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<p[^>]*>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'</p>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<h[1-6][^>]*>', '\n## ', html, flags=re.IGNORECASE)
    html = re.sub(r'</h[1-6]>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<li[^>]*>', '\n- ', html, flags=re.IGNORECASE)
    html = re.sub(r'<[^>]+>', '', html)
    html = re.sub(r'&nbsp;', ' ', html)
    html = re.sub(r'&amp;', '&', html)
    html = re.sub(r'&lt;', '<', html)
    html = re.sub(r'&gt;', '>', html)
    html = re.sub(r'&quot;', '"', html)
    html = re.sub(r'&#\d+;', '', html)
    html = re.sub(r'\n{3,}', '\n\n', html)
    html = re.sub(r'[ \t]+', ' ', html)

    lines = [line.strip() for line in html.split('\n')]
    return '\n'.join(line for line in lines if line)


def extract_title(html: str) -> str:
    match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    if match:
        title = match.group(1).strip()
        title = re.sub(r'<[^>]+>', '', title)
        return title[:200]
    return ""


def fetch_with_httpx(url: str) -> Dict[str, Any]:
    # SSRF安全检查
    is_safe, error_msg = _validate_url(url)
    if not is_safe:
        return {
            "success": False,
            "message": f"URL安全检查失败: {error_msg}",
        }
    
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = httpx.get(url, headers=headers, timeout=REQUEST_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return {
                "success": False,
                "message": f"不是网页内容（Content-Type: {content_type}）",
            }

        html = resp.text
        title = extract_title(html)
        content = clean_html(html)

        return {
            "success": True,
            "url": str(resp.url),
            "title": title,
            "content": content[:MAX_CONTENT_LENGTH],
            "content_length": len(content),
            "status_code": resp.status_code,
        }
    except httpx.HTTPStatusError as e:
        return {"success": False, "message": f"HTTP 错误 ({e.response.status_code})"}
    except httpx.TimeoutException:
        return {"success": False, "message": "请求超时"}
    except Exception as e:
        return {"success": False, "message": f"请求失败: {e}"}


def fetch_with_playwright(url: str) -> Dict[str, Any]:
    # SSRF安全检查
    is_safe, error_msg = _validate_url(url)
    if not is_safe:
        return {
            "success": False,
            "message": f"URL安全检查失败: {error_msg}",
        }
    
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "success": False,
            "message": "Playwright 未安装。轻量抓取请直接使用 httpx 模式。",
        }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(REQUEST_TIMEOUT * 1000)
            page.goto(url, wait_until="domcontentloaded")

            title = page.title()
            content = page.inner_text("body")

            browser.close()

            return {
                "success": True,
                "url": url,
                "title": title,
                "content": content[:MAX_CONTENT_LENGTH],
                "content_length": len(content),
            }
    except Exception as e:
        return {"success": False, "message": f"Playwright 抓取失败: {e}"}


def fetch_url(url: str, use_js: bool = False) -> Dict[str, Any]:
    if use_js:
        result = fetch_with_playwright(url)
        if result["success"]:
            return result
        logger.info(f"Playwright 失败，降级到 httpx: {result.get('message')}")

    return fetch_with_httpx(url)


@register_skill(
    skill_id="web_scrape",
    name="网页抓取",
    description="抓取指定网页内容，提取正文和元信息",
    triggers=["抓取", "爬取", "抓网页", "读取网页", "获取网页", "看看网页", "网页内容",
              "访问网页", "打开网页", "fetch", "爬虫", "抓取网页", "抓取内容", "抓取一下"],
    icon="web",
    examples=[
        "帮我抓取一下这个网页的内容 https://example.com",
        "读取这个网页 https://news.example.com/article/123",
        "访问一下 https://github.com 看看内容",
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "scrape_webpage",
            "description": "抓取指定URL的网页内容。当用户提供URL要求抓取、读取网页内容时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要抓取的网页URL",
                    },
                },
                "required": ["url"],
            },
        },
    },
)
def handle_web_scrape(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    urls = extract_urls(user_input)

    if not urls:
        return {
            "success": False,
            "message": "请提供要抓取的网页 URL。比如：「帮我抓取一下 https://example.com 的内容」",
        }

    url = urls[0]

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return {"success": False, "message": f"URL 格式不正确: {url}"}

    use_js = any(kw in user_input for kw in ["JS", "javascript", "渲染", "动态", "playwright"])

    result = fetch_url(url, use_js=use_js)

    if not result["success"]:
        return {"success": False, "message": f"❌ {result['message']}"}

    question = user_input
    for trigger in ["抓取网页", "爬取", "抓网页", "读取网页", "获取网页", "看看网页",
                     "网页内容", "访问网页", "打开网页", "抓取内容", "爬虫", "帮我",
                     "一下", "这个", "内容", "看看", url, "fetch"]:
        question = question.replace(trigger, "").strip()

    if question and len(question) > 3:
        try:
            from core.agents import get_agent_manager
            from core.model_router import build_llm_for_agent
            from api.deps import DATA_DIR
            manager = get_agent_manager(DATA_DIR)
            agent_config = manager.get_default_agent()
            llm = build_llm_for_agent(agent_config)

            content_preview = result["content"][:12000]
            response = llm.call(messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一个网页内容分析助手。根据用户提供的网页内容回答问题。"
                        "用中文回复，使用 Markdown 格式。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"网页标题：{result['title']}\n"
                        f"网页URL：{result['url']}\n\n"
                        f"网页内容：\n---\n{content_preview}\n---\n\n"
                        f"用户问题：{question}"
                    ),
                },
            ])

            msg = (
                f"🌐 **网页抓取结果**\n\n"
                f"**标题：** {result['title']}\n"
                f"**URL：** {result['url']}\n"
                f"**内容长度：** {result['content_length']} 字符\n\n"
                f"---\n\n{response}"
            )
            return {"success": True, "message": msg}

        except Exception as e:
            logger.warning(f"网页内容 AI 分析失败: {e}")

    content_preview = result["content"][:5000]
    msg = (
        f"🌐 **网页抓取结果**\n\n"
        f"**标题：** {result['title']}\n"
        f"**URL：** {result['url']}\n"
        f"**内容长度：** {result['content_length']} 字符\n\n"
        f"---\n\n{content_preview}\n\n"
        f"{'...(内容过长，已截断)' if result['content_length'] > 5000 else ''}"
    )
    return {"success": True, "message": msg}
