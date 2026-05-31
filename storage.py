"""
聊天历史落盘到 PC 本地的 chats/ 目录。

设计要点（详见 plan）：
- 每个会话一个子文件夹：{safe_title}__{short_id}/
- messages.json 是源真相；图片/PDF 二进制放 files/ 子目录
- 写盘走 临时文件 + os.replace（Windows 原子语义）
- 所有 disk op 按 session_id 走同一把 asyncio.Lock，避免并发交错
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).parent
CHATS_DIR = BASE_DIR / "chats"

# 每个 session 一把锁；read/write/delete 都得过它
_disk_locks: Dict[str, asyncio.Lock] = {}


def _lock_for(sid: str) -> asyncio.Lock:
    lock = _disk_locks.get(sid)
    if lock is None:
        lock = asyncio.Lock()
        _disk_locks[sid] = lock
    return lock


# ---------- 文件夹命名 ----------

_ILLEGAL_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def safe_title_part(title: str) -> str:
    s = (title or "").strip()
    s = s.replace("\n", " ").replace("\t", " ").replace("\r", " ")
    s = _ILLEGAL_RE.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    # Windows 静默剥离尾部 . 和空格，先剥掉避免后续路径碰撞
    s = s.rstrip(". ")
    if not s:
        s = "无标题"
    if s.upper() in _RESERVED:
        s = "_" + s
    return s[:30].rstrip(". ") or "无标题"


def safe_folder_name(title: str, sid: str) -> str:
    short = sid.replace("-", "")[:8]
    return f"{safe_title_part(title)}__{short}"


def normalize_title(title: str) -> str:
    """messages.json 里 title 的轻量净化：去换行，最多 60 字符。folder 名净化更严格（safe_title_part）。"""
    s = (title or "").replace("\n", " ").replace("\t", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return "新聊天"
    return s[:60]


# ---------- 文件夹定位 ----------

def _ensure_root() -> None:
    CHATS_DIR.mkdir(parents=True, exist_ok=True)


def chat_folder(sid: str) -> Optional[Path]:
    """已存在的会话文件夹（用 short_id 后缀匹配）。"""
    if not CHATS_DIR.exists():
        return None
    short = sid.replace("-", "")[:8]
    suffix = f"__{short}"
    for child in CHATS_DIR.iterdir():
        if child.is_dir() and child.name.endswith(suffix):
            return child
    return None


def _create_folder(sid: str, title: str) -> Path:
    _ensure_root()
    folder = CHATS_DIR / safe_folder_name(title, sid)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "files").mkdir(exist_ok=True)
    return folder


def _files_dir(folder: Path) -> Path:
    d = folder / "files"
    d.mkdir(exist_ok=True)
    return d


# ---------- messages.json 读写 ----------

def _read_chat(folder: Path) -> Optional[dict]:
    p = folder / "messages.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_chat(folder: Path, chat: dict) -> None:
    p = folder / "messages.json"
    tmp = folder / f".messages.json.tmp.{uuid.uuid4().hex[:8]}"
    tmp.write_text(json.dumps(chat, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)  # 跨平台原子替换


# ---------- 对外 API ----------

async def list_chats() -> List[dict]:
    """会话列表：{id, title, updated_at, msg_count, last_snippet}。按 updated_at 倒序。"""
    if not CHATS_DIR.exists():
        return []
    items: List[dict] = []
    for folder in CHATS_DIR.iterdir():
        if not folder.is_dir():
            continue
        chat = _read_chat(folder)
        if not chat:
            continue
        msgs = chat.get("messages") or []
        last_snip = ""
        for m in reversed(msgs):
            c = (m.get("content") or "").strip()
            if c:
                last_snip = c[:80]
                break
        items.append({
            "id": chat.get("id"),
            "title": chat.get("title") or "新聊天",
            "updated_at": chat.get("updated_at") or 0,
            "msg_count": len(msgs),
            "last_snippet": last_snip,
        })
    items.sort(key=lambda x: x["updated_at"], reverse=True)
    return items


async def load_chat(sid: str) -> Optional[dict]:
    folder = chat_folder(sid)
    if folder is None:
        return None
    async with _lock_for(sid):
        return _read_chat(folder)


async def delete_chat(sid: str) -> bool:
    folder = chat_folder(sid)
    if folder is None:
        return False
    async with _lock_for(sid):
        shutil.rmtree(folder, ignore_errors=True)
    _disk_locks.pop(sid, None)
    return True


async def ensure_chat(
    sid: str,
    *,
    title: str,
    model: str,
    effort: Optional[str],
    thinking: Optional[bool],
) -> dict:
    """如果会话不存在就创建一个空的；返回当前 chat dict（不带 messages 时为空列表）。"""
    folder = chat_folder(sid)
    async with _lock_for(sid):
        if folder is None:
            folder = _create_folder(sid, title)
            now = int(time.time() * 1000)
            chat = {
                "id": sid,
                "title": normalize_title(title),
                "model": model,
                "effort": effort,
                "thinking": thinking,
                "created_at": now,
                "updated_at": now,
                "messages": [],
            }
            _write_chat(folder, chat)
            return chat
        chat = _read_chat(folder) or {}
        return chat


async def append_message(sid: str, msg: dict, *, title_if_new: Optional[str] = None) -> None:
    """追加一条消息到 messages.json 并 bump updated_at。chat 必须已存在（先调 ensure_chat）。"""
    folder = chat_folder(sid)
    if folder is None:
        return
    async with _lock_for(sid):
        chat = _read_chat(folder) or {}
        chat.setdefault("messages", []).append(msg)
        chat["updated_at"] = int(time.time() * 1000)
        if title_if_new and (not chat.get("title") or chat.get("title") == "新聊天"):
            chat["title"] = normalize_title(title_if_new)
        _write_chat(folder, chat)


# ---------- 文件资源（图片 / PDF） ----------

def _file_id(kind: str) -> str:
    return f"{kind}_{uuid.uuid4().hex[:16]}"


def save_image(sid: str, *, api_bytes: bytes, thumb_bytes: bytes,
               width: int, height: int) -> Dict[str, Any]:
    """同步保存一组图片（原图 + 缩略图）。chat 必须已存在。返回 attachment 字典。"""
    folder = chat_folder(sid)
    if folder is None:
        raise RuntimeError(f"chat folder not found for sid={sid}")
    files = _files_dir(folder)
    fid = _file_id("img")
    (files / f"{fid}.jpg").write_bytes(api_bytes)
    (files / f"{fid}.thumb.jpg").write_bytes(thumb_bytes)
    return {
        "type": "image",
        "file_id": fid,
        "width": int(width),
        "height": int(height),
        "size": len(api_bytes),
    }


def save_pdf(sid: str, *, data: bytes, name: str) -> Dict[str, Any]:
    """同步保存 PDF。chat 必须已存在。返回 attachment 字典（同时写 .meta.json）。"""
    folder = chat_folder(sid)
    if folder is None:
        raise RuntimeError(f"chat folder not found for sid={sid}")
    files = _files_dir(folder)
    fid = _file_id("doc")
    (files / f"{fid}.pdf").write_bytes(data)
    meta = {"name": name, "size": len(data), "saved_at": int(time.time() * 1000)}
    (files / f"{fid}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False), encoding="utf-8"
    )
    return {
        "type": "pdf",
        "file_id": fid,
        "name": name,
        "size": len(data),
    }


def file_path(sid: str, file_id: str, *, thumb: bool = False) -> Optional[Path]:
    """返回 file_id 对应的磁盘路径；不存在或越界返回 None。"""
    if not re.fullmatch(r"(img|doc)_[A-Za-z0-9]{8,32}", file_id or ""):
        return None
    folder = chat_folder(sid)
    if folder is None:
        return None
    files = folder / "files"
    if file_id.startswith("img_"):
        target = files / (f"{file_id}.thumb.jpg" if thumb else f"{file_id}.jpg")
    elif file_id.startswith("doc_"):
        if thumb:
            return None
        target = files / f"{file_id}.pdf"
    else:
        return None
    # 防越界：必须仍在 files 目录下
    try:
        target.resolve().relative_to(files.resolve())
    except ValueError:
        return None
    return target if target.exists() else None


def pdf_meta(sid: str, file_id: str) -> Optional[dict]:
    if not file_id.startswith("doc_"):
        return None
    folder = chat_folder(sid)
    if folder is None:
        return None
    p = folder / "files" / f"{file_id}.meta.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_pdf_bytes(sid: str, file_id: str) -> Optional[bytes]:
    p = file_path(sid, file_id)
    if p is None:
        return None
    return p.read_bytes()


def read_image_bytes(sid: str, file_id: str) -> Optional[bytes]:
    """读取原图（API 版本）字节。"""
    p = file_path(sid, file_id)
    if p is None:
        return None
    return p.read_bytes()
