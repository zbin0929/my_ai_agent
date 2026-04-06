# -*- coding: utf-8 -*-
"""
知识库技能（简化版 RAG）
========================

支持用户上传文档到知识库，后续对话基于知识库内容回答。
使用文本分片 + 关键词匹配检索（无需向量数据库依赖）。
后续可升级为向量检索（FAISS/ChromaDB + Embedding API）。
"""

import os
import sys
import json
import re
import logging
import threading
from typing import Dict, Any, List, Optional
from collections import Counter

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from skills import register_skill

logger = logging.getLogger(__name__)

KB_DIR = os.path.join(project_root, "data", "knowledge_base")
KB_INDEX_FILE = os.path.join(KB_DIR, "index.json")
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
MAX_CHUNKS_RETURN = 5


def _ensure_kb_dir():
    os.makedirs(KB_DIR, exist_ok=True)


def _load_index() -> Dict[str, Any]:
    _ensure_kb_dir()
    if os.path.exists(KB_INDEX_FILE):
        try:
            with open(KB_INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"documents": [], "chunks": []}


_kb_lock = threading.Lock()


def _save_index(index: Dict[str, Any]):
    _ensure_kb_dir()
    # 持久化时不保存 tokens（搜索时重新计算），避免索引文件膨胀
    save_data = {
        "documents": index["documents"],
        "chunks": [
            {k: v for k, v in c.items() if k != "tokens"}
            for c in index["chunks"]
        ],
    }
    tmp_path = KB_INDEX_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, KB_INDEX_FILE)


def _read_file_content(filepath: str) -> str:
    try:
        from core.file_reader import read_file_content
        return read_file_content(filepath)
    except ImportError:
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return ""


def _split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """将文本按段落和大小分片"""
    paragraphs = re.split(r'\n{2,}', text)
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 1 <= chunk_size:
            current_chunk += ("\n" + para if current_chunk else para)
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # 如果单段超长，按句子切分
            if len(para) > chunk_size:
                sentences = re.split(r'[。！？.!?\n]', para)
                sub_chunk = ""
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    if len(sub_chunk) + len(sent) + 1 <= chunk_size:
                        sub_chunk += ("。" + sent if sub_chunk else sent)
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = sent
                if sub_chunk:
                    current_chunk = sub_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _tokenize(text: str) -> List[str]:
    """简单分词：中文按字，英文按词"""
    tokens = []
    # 英文单词
    tokens.extend(re.findall(r'[a-zA-Z]+', text.lower()))
    # 中文字符（2-gram）
    chinese = re.findall(r'[\u4e00-\u9fff]', text)
    for i in range(len(chinese) - 1):
        tokens.append(chinese[i] + chinese[i + 1])
    tokens.extend(chinese)
    return tokens


def _bm25_score(query_tokens: List[str], doc_tokens: List[str], avg_dl: float, k1: float = 1.5, b: float = 0.75) -> float:
    """BM25 评分"""
    doc_len = len(doc_tokens)
    doc_freq = Counter(doc_tokens)
    score = 0.0
    for token in set(query_tokens):
        if token in doc_freq:
            tf = doc_freq[token]
            idf = 1.0  # 简化：不计算全局 IDF
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / max(avg_dl, 1))
            score += idf * numerator / denominator
    return score


def add_to_knowledge_base(filepath: str, doc_name: str = "") -> Dict[str, Any]:
    """将文档添加到知识库"""
    if not os.path.exists(filepath):
        return {"success": False, "message": f"文件不存在: {filepath}"}

    content = _read_file_content(filepath)
    if not content or len(content.strip()) < 10:
        return {"success": False, "message": "文件内容为空或过短"}

    if not doc_name:
        doc_name = os.path.basename(filepath)

    with _kb_lock:
        index = _load_index()

        # 检查是否已存在
        for doc in index["documents"]:
            if doc["name"] == doc_name:
                # 更新已有文档
                index["chunks"] = [c for c in index["chunks"] if c["doc_name"] != doc_name]
                index["documents"] = [d for d in index["documents"] if d["name"] != doc_name]
                break

        chunks = _split_text(content)

        for i, chunk_text in enumerate(chunks):
            index["chunks"].append({
                "doc_name": doc_name,
                "chunk_id": i,
                "text": chunk_text,
            })

        index["documents"].append({
            "name": doc_name,
            "filepath": filepath,
            "chunk_count": len(chunks),
            "char_count": len(content),
        })

        _save_index(index)
    return {"success": True, "message": f"已添加到知识库: {doc_name}（{len(chunks)} 个分片）", "chunks": len(chunks)}


def search_knowledge_base(query: str, top_k: int = MAX_CHUNKS_RETURN) -> Dict[str, Any]:
    """在知识库中搜索相关内容"""
    index = _load_index()
    if not index["chunks"]:
        return {"success": False, "message": "知识库为空，请先上传文档到知识库"}

    query_tokens = _tokenize(query)
    if not query_tokens:
        return {"success": False, "message": "查询内容过短"}

    # 搜索时实时计算 tokens（不从 JSON 读取，避免索引膨胀）
    chunk_tokens_list = [c.get("tokens") or _tokenize(c["text"]) for c in index["chunks"]]
    avg_dl = sum(len(t) for t in chunk_tokens_list) / len(chunk_tokens_list)
    scored = []
    for chunk, doc_tokens in zip(index["chunks"], chunk_tokens_list):
        score = _bm25_score(query_tokens, doc_tokens, avg_dl)
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_chunks = scored[:top_k]

    if not top_chunks:
        return {"success": False, "message": "未找到相关内容"}

    return {
        "success": True,
        "results": [{"doc_name": c["doc_name"], "text": c["text"], "score": round(s, 3)} for s, c in top_chunks],
    }


def query_knowledge_base(query: str) -> Dict[str, Any]:
    """基于知识库内容回答问题"""
    search_result = search_knowledge_base(query)
    if not search_result["success"]:
        return search_result

    context_parts = []
    sources = set()
    for r in search_result["results"]:
        context_parts.append(f"[来源: {r['doc_name']}]\n{r['text']}")
        sources.add(r["doc_name"])

    context_text = "\n\n---\n\n".join(context_parts)

    try:
        from core.agents import get_agent_manager
        from core.model_router import build_llm_for_agent
        from api.deps import DATA_DIR
        manager = get_agent_manager(DATA_DIR)
        agent_config = manager.get_default_agent()
        llm = build_llm_for_agent(agent_config)

        response = llm.call(messages=[
            {
                "role": "system",
                "content": (
                    "你是一个知识库问答助手。根据以下检索到的文档片段回答用户问题。\n"
                    "要求：\n"
                    "1. 只基于提供的内容回答，不要编造信息\n"
                    "2. 如果内容不足以回答，请明确说明\n"
                    "3. 引用来源文档名称\n"
                    "4. 用 Markdown 格式输出\n\n"
                    f"检索到的文档片段：\n{context_text}"
                ),
            },
            {"role": "user", "content": query},
        ])

        return {
            "success": True,
            "answer": str(response).strip(),
            "sources": list(sources),
        }
    except Exception as e:
        logger.error(f"知识库问答失败: {e}")
        return {"success": False, "message": f"知识库问答失败: {e}"}


def list_knowledge_base() -> Dict[str, Any]:
    """列出知识库中的所有文档"""
    index = _load_index()
    return {
        "success": True,
        "documents": index["documents"],
        "total_chunks": len(index["chunks"]),
    }


@register_skill(
    skill_id="knowledge_base",
    name="知识库",
    description="管理和查询知识库：上传文档到知识库，基于知识库内容回答问题",
    triggers=["知识库", "添加到知识库", "从知识库", "查询知识库", "知识库搜索",
              "上传到知识库", "knowledge base", "RAG"],
    icon="database",
    examples=[
        "把这个文档添加到知识库",
        "从知识库中搜索关于项目架构的信息",
        "知识库里有什么文档？",
    ],
    tool_schema={
        "type": "function",
        "function": {
            "name": "knowledge_base_query",
            "description": "知识库操作：添加文档到知识库、从知识库检索信息回答问题、列出知识库文档。",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "操作类型：query（查询）、add（添加文档）、list（列出文档）",
                        "enum": ["query", "add", "list"],
                    },
                    "prompt": {
                        "type": "string",
                        "description": "查询内容或操作描述",
                    },
                },
                "required": ["action", "prompt"],
            },
        },
    },
)
def handle_knowledge_base(user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
    tool_args = context.get("tool_args", {}) if context else {}
    action = tool_args.get("action", "query")

    if action == "list" or "有什么文档" in user_input or "列出" in user_input:
        result = list_knowledge_base()
        if not result["documents"]:
            return {"success": True, "message": "📚 知识库为空，请上传文档后使用「添加到知识库」。"}
        lines = ["📚 **知识库文档列表**\n"]
        for doc in result["documents"]:
            lines.append(f"- **{doc['name']}** — {doc['chunk_count']} 个分片，{doc['char_count']} 字符")
        lines.append(f"\n共 {len(result['documents'])} 个文档，{result['total_chunks']} 个分片")
        return {"success": True, "message": "\n".join(lines)}

    if action == "add" or "添加到知识库" in user_input or "上传到知识库" in user_input:
        files = []
        if context:
            for key in ("files", "file_paths"):
                if context.get(key):
                    files.extend(context[key])
        if not files:
            return {"success": False, "message": "请先上传文档，然后再说「添加到知识库」"}

        results = []
        for fp in files:
            if os.path.exists(fp):
                r = add_to_knowledge_base(fp)
                results.append(r["message"])
        return {"success": True, "message": "📚 " + "\n".join(results)}

    # 默认：查询
    query = tool_args.get("prompt") or user_input
    for trigger in ["知识库", "从知识库", "查询知识库", "知识库搜索"]:
        query = query.replace(trigger, "").strip()

    if not query:
        return {"success": False, "message": "请提供查询内容"}

    result = query_knowledge_base(query)
    if not result["success"]:
        return {"success": False, "message": f"❌ {result['message']}"}

    sources_str = "、".join(result["sources"])
    msg = (
        f"📚 **知识库回答**\n\n"
        f"{result['answer']}\n\n"
        f"---\n*来源: {sources_str}*"
    )
    return {"success": True, "message": msg}
