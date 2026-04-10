# -*- coding: utf-8 -*-
import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

MAX_CONTENT_CHARS = 80000

SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".xml", ".yaml", ".yml", ".log",
    ".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".h",
    ".html", ".css", ".sql", ".sh", ".bat",
}


def read_file(path: str) -> Dict[str, Any]:
    filename = os.path.basename(path)
    ext = os.path.splitext(path)[1].lower()

    if not os.path.exists(path):
        return {"success": False, "message": f"文件不存在: {filename}"}

    file_size = os.path.getsize(path)
    if file_size > 10 * 1024 * 1024:
        return {"success": False, "message": f"文件过大: {filename} ({file_size // 1024 // 1024}MB)"}

    try:
        if ext in (".pdf",):
            content = _read_pdf(path)
        elif ext in (".docx", ".doc"):
            content = _read_docx(path)
        elif ext in (".xlsx", ".xls"):
            content = _read_excel(path)
        elif ext in (".csv",):
            content = _read_csv(path)
        elif ext in SUPPORTED_EXTENSIONS or ext in (".toml", ".ini", ".cfg", ".env"):
            content = _read_text(path)
        else:
            content = _read_text(path)

        if len(content) > MAX_CONTENT_CHARS:
            content = content[:MAX_CONTENT_CHARS] + "\n\n... [文件内容过长，已截断]"

        return {"success": True, "filename": filename, "ext": ext, "content": content}
    except Exception as e:
        logger.error(f"读取文件失败: {path} - {e}")
        return {"success": False, "message": f"读取失败: {e}"}


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read(MAX_CONTENT_CHARS)


def _read_csv(path: str) -> str:
    try:
        import pandas as pd
        df = pd.read_csv(path, nrows=200)
        return f"[CSV 数据，{len(df)} 行 x {len(df.columns)} 列]\n列名: {', '.join(df.columns.tolist())}\n\n{df.to_string(max_rows=50)}"
    except ImportError:
        return _read_text(path)


def _read_pdf(path: str) -> str:
    try:
        import fitz
        doc = fitz.open(path)
        text = ""
        for i, page in enumerate(doc):
            text += f"--- 第 {i + 1} 页 ---\n{page.get_text()}\n\n"
            if len(text) > MAX_CONTENT_CHARS:
                break
        doc.close()
        return text or "[PDF 文件无文字内容，可能是扫描件]"
    except ImportError:
        return "[需要安装 PyMuPDF: pip install PyMuPDF]"


def _read_docx(path: str) -> str:
    try:
        from docx import Document
        doc = Document(path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except ImportError:
        return "[需要安装 python-docx: pip install python-docx]"


def _read_excel(path: str) -> str:
    try:
        import pandas as pd
        xls = pd.ExcelFile(path)
        parts = []
        for sheet_name in xls.sheet_names[:5]:
            df = pd.read_excel(xls, sheet_name=sheet_name, nrows=100)
            parts.append(f"=== 工作表: {sheet_name} ({len(df)} 行 x {len(df.columns)} 列) ===\n{df.to_string(max_rows=30)}")
        return "\n\n".join(parts)
    except ImportError:
        return "[需要安装 openpyxl: pip install openpyxl]"
