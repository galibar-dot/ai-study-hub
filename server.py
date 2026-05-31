"""
手机 -> 电脑 -> Claude / GPT 中转服务（带本地持久化）

跑起来后：
- PC 本机访问：http://localhost:8000
- 同 WiFi 手机访问：http://<电脑IP>:8000
- 外网访问：用 Cloudflare Tunnel 把 8000 端口穿出去
聊天历史落盘到 chats/ 目录；图片/PDF 单独存放，懒加载。
"""

import asyncio
import base64
import json
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Tuple

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    StreamEvent,
)

import storage
import dictionary
import vocabulary
import reading

PASSWORD = os.environ.get("APP_PASSWORD", "change-me-please")
PORT = 8000
DEFAULT_MODEL = "claude-opus-4-7"
MAX_PDF_SIZE = 20 * 1024 * 1024

os.environ.setdefault("CLAUDE_AGENT_SDK_SKIP_VERSION_CHECK", "1")

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.yml"
INDEX_HTML = (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")

load_dotenv(BASE_DIR / ".env")
ENV_RELAY_API_KEY = os.environ.get("RELAY_API_KEY", "").strip()
ENV_RELAY_BASE_URL = os.environ.get(
    "RELAY_BASE_URL", "https://api.xinye123.fun/v1"
).strip()


class RelayProvider(BaseModel):
    name: str
    base_url: str
    api_key: str
    models: List[str]
    api_type: str = "responses"  # "responses" 或 "chat_completions"


def _load_relay_config() -> Tuple[Dict[str, RelayProvider], str]:
    if not CONFIG_PATH.exists():
        fallback = RelayProvider(
            name="default",
            base_url=ENV_RELAY_BASE_URL,
            api_key=ENV_RELAY_API_KEY,
            models=["gpt-5.5"],
        )
        return {"default": fallback}, "default"

    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    relay = raw.get("relay") or {}
    providers_raw = relay.get("providers") or {}
    default_provider = str(relay.get("default_provider") or "default").strip() or "default"

    providers: Dict[str, RelayProvider] = {}
    for provider_name, item in providers_raw.items():
        if not isinstance(item, dict):
            continue
        models = item.get("models") or []
        if isinstance(models, str):
            models = [models]
        api_type = str(item.get("api_type") or "responses").strip()
        if api_type not in ("responses", "chat_completions"):
            api_type = "responses"
        providers[provider_name] = RelayProvider(
            name=provider_name,
            base_url=str(item.get("base_url") or "").strip(),
            api_key=str(item.get("api_key") or "").strip(),
            models=[str(model).strip() for model in models if str(model).strip()],
            api_type=api_type,
        )

    if not providers:
        providers["default"] = RelayProvider(
            name="default",
            base_url=ENV_RELAY_BASE_URL,
            api_key=ENV_RELAY_API_KEY,
            models=["gpt-5.5"],
        )
        default_provider = "default"

    if default_provider not in providers:
        default_provider = next(iter(providers.keys()))

    default_item = providers[default_provider]
    if not default_item.base_url:
        default_item.base_url = ENV_RELAY_BASE_URL
    if not default_item.api_key:
        default_item.api_key = ENV_RELAY_API_KEY

    return providers, default_provider


RELAY_PROVIDERS, DEFAULT_RELAY_PROVIDER = _load_relay_config()
RELAY_MODEL_TO_PROVIDER: Dict[str, str] = {}
for provider_name, provider in RELAY_PROVIDERS.items():
    for model_name in provider.models:
        RELAY_MODEL_TO_PROVIDER[model_name] = provider_name
RELAY_MODELS: Set[str] = set(RELAY_MODEL_TO_PROVIDER.keys())


def _provider_for_model(model: str) -> Optional[RelayProvider]:
    provider_name = RELAY_MODEL_TO_PROVIDER.get((model or "").strip())
    if not provider_name:
        return None
    return RELAY_PROVIDERS.get(provider_name)


sessions: Dict[str, ClaudeSDKClient] = {}
session_locks: Dict[str, asyncio.Lock] = {}
relay_sessions: Dict[str, List[Dict[str, Any]]] = {}
relay_locks: Dict[str, asyncio.Lock] = {}
active_gens: Dict[str, asyncio.Task] = {}

relay_clients: Dict[str, AsyncOpenAI] = {}
for provider_name, provider in RELAY_PROVIDERS.items():
    if provider.base_url and provider.api_key:
        relay_clients[provider_name] = AsyncOpenAI(
            api_key=provider.api_key,
            base_url=provider.base_url,
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    pending = [task for task in active_gens.values() if not task.done()]
    if pending:
        try:
            await asyncio.wait_for(asyncio.gather(*pending, return_exceptions=True), timeout=30)
        except asyncio.TimeoutError:
            for task in pending:
                if not task.done():
                    task.cancel()
    for client in list(sessions.values()):
        try:
            await client.__aexit__(None, None, None)
        except Exception:
            pass
    for relay_client in list(relay_clients.values()):
        try:
            await relay_client.close()
        except Exception:
            pass


app = FastAPI(lifespan=lifespan)


class ImagePart(BaseModel):
    data: str
    media_type: str
    thumb_data: str
    width: int
    height: int


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = None
    effort: Optional[str] = None
    thinking: Optional[bool] = None
    images: Optional[List[ImagePart]] = None
    document_ids: Optional[List[str]] = None
    title: Optional[str] = None


class LoginRequest(BaseModel):
    password: str


class ResetRequest(BaseModel):
    session_id: Optional[str] = None


def check_auth(request: Request) -> None:
    token = request.cookies.get("auth")
    if token != PASSWORD:
        raise HTTPException(status_code=401, detail="unauthorized")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML)


@app.post("/api/login")
async def login(body: LoginRequest) -> Response:
    if body.password != PASSWORD:
        return JSONResponse({"ok": False, "error": "密码错误"}, status_code=401)
    resp = JSONResponse({"ok": True})
    resp.set_cookie(
        "auth", PASSWORD, httponly=True, samesite="lax", max_age=30 * 24 * 3600,
    )
    return resp


@app.post("/api/logout")
async def logout() -> Response:
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("auth")
    return resp


@app.get("/api/auth/status")
async def auth_status(request: Request) -> JSONResponse:
    return JSONResponse({"authed": request.cookies.get("auth") == PASSWORD})


@app.get("/api/chats")
async def api_list_chats(request: Request) -> JSONResponse:
    check_auth(request)
    return JSONResponse(await storage.list_chats())


@app.get("/api/chats/{sid}")
async def api_get_chat(sid: str, request: Request) -> JSONResponse:
    check_auth(request)
    chat = await storage.load_chat(sid)
    if chat is None:
        raise HTTPException(status_code=404, detail="chat not found")
    return JSONResponse(chat)


@app.delete("/api/chats/{sid}")
async def api_delete_chat(sid: str, request: Request) -> JSONResponse:
    check_auth(request)
    await storage.delete_chat(sid)
    await _close_session(sid)
    return JSONResponse({"ok": True})


@app.post("/api/upload")
async def api_upload(
    request: Request,
    session_id: str = Form(...),
    file: UploadFile = File(...),
) -> JSONResponse:
    check_auth(request)
    if (file.content_type or "").lower() != "application/pdf":
        raise HTTPException(status_code=400, detail="只支持 PDF")
    await storage.ensure_chat(
        session_id, title="新聊天", model="", effort=None, thinking=None
    )
    data = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data.extend(chunk)
        if len(data) > MAX_PDF_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"PDF 超过 {MAX_PDF_SIZE // (1024*1024)}MB 上限",
            )
    attachment = storage.save_pdf(
        session_id, data=bytes(data), name=file.filename or "upload.pdf"
    )
    return JSONResponse(attachment)


@app.get("/api/files/{sid}/{fid}")
async def api_get_file(sid: str, fid: str, request: Request) -> FileResponse:
    check_auth(request)
    path = storage.file_path(sid, fid)
    if path is None:
        raise HTTPException(status_code=404)
    headers = {"Cache-Control": "private, max-age=31536000, immutable"}
    if fid.startswith("doc_"):
        meta = storage.pdf_meta(sid, fid) or {}
        name = meta.get("name", "document.pdf")
        safe_name = name.replace('"', "")
        headers["Content-Disposition"] = f'inline; filename="{safe_name}"'
        return FileResponse(path, media_type="application/pdf", headers=headers)
    return FileResponse(path, media_type="image/jpeg", headers=headers)


@app.get("/api/files/{sid}/{fid}/thumb")
async def api_get_file_thumb(sid: str, fid: str, request: Request) -> FileResponse:
    check_auth(request)
    if not fid.startswith("img_"):
        raise HTTPException(status_code=404)
    path = storage.file_path(sid, fid, thumb=True)
    if path is None:
        raise HTTPException(status_code=404)
    return FileResponse(
        path,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )


def _derive_title(text: str) -> str:
    title = (text or "").strip().split("\n")[0]
    title = re.sub(r"\s+", " ", title)
    if not title:
        return "新聊天"
    return title[:30] + ("..." if len(title) > 30 else "")


def _b64_strip(value: str) -> str:
    if not value:
        return ""
    if value.startswith("data:"):
        _, _, rest = value.partition(",")
        return rest
    return value


def _save_request_attachments(
    sid: str,
    images: Optional[List[ImagePart]],
    document_ids: Optional[List[str]],
) -> List[Dict[str, Any]]:
    attachments: List[Dict[str, Any]] = []
    if images:
        for image in images:
            try:
                api_bytes = base64.b64decode(_b64_strip(image.data))
                thumb_bytes = base64.b64decode(_b64_strip(image.thumb_data))
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"图片解码失败: {exc}")
            attachments.append(storage.save_image(
                sid,
                api_bytes=api_bytes,
                thumb_bytes=thumb_bytes,
                width=image.width,
                height=image.height,
            ))
    if document_ids:
        for file_id in document_ids:
            meta = storage.pdf_meta(sid, file_id)
            if meta is None:
                raise HTTPException(status_code=400, detail=f"document_id 不存在: {file_id}")
            attachments.append({
                "type": "pdf",
                "file_id": file_id,
                "name": meta.get("name"),
                "size": meta.get("size"),
            })
    return attachments


async def _claude_query_iter(
    text: str, images: Optional[List[ImagePart]]
) -> AsyncIterator[Dict[str, Any]]:
    content: List[Dict[str, Any]] = []
    if images:
        for image in images:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image.media_type,
                    "data": _b64_strip(image.data),
                },
            })
    content.append({"type": "text", "text": text or ""})
    yield {
        "type": "user",
        "message": {"role": "user", "content": content},
        "parent_tool_use_id": None,
    }


def _build_relay_user_item_fresh(
    text: str,
    images: Optional[List[ImagePart]],
    pdf_attachments: List[Dict[str, Any]],
    sid: str,
) -> Dict[str, Any]:
    has_attach = bool(images) or bool(pdf_attachments)
    if not has_attach:
        return {"role": "user", "content": text or ""}
    parts: List[Dict[str, Any]] = []
    if images:
        for image in images:
            parts.append({
                "type": "input_image",
                "image_url": f"data:{image.media_type};base64,{_b64_strip(image.data)}",
            })
    for attachment in pdf_attachments:
        pdf_bytes = storage.read_pdf_bytes(sid, attachment["file_id"])
        if not pdf_bytes:
            continue
        encoded = base64.b64encode(pdf_bytes).decode()
        parts.append({
            "type": "input_file",
            "filename": attachment.get("name", "document.pdf"),
            "file_data": f"data:application/pdf;base64,{encoded}",
        })
    parts.append({"type": "input_text", "text": text or ""})
    return {"role": "user", "content": parts}


def _build_relay_history_from_disk(sid: str, chat: dict) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = []
    for message in chat.get("messages") or []:
        role = message.get("role")
        text = message.get("content") or ""
        attachments = message.get("attachments") or []
        if role == "assistant":
            history.append({"role": "assistant", "content": text})
            continue
        if not attachments:
            history.append({"role": "user", "content": text})
            continue
        parts: List[Dict[str, Any]] = []
        for attachment in attachments:
            if attachment.get("type") == "image":
                image_bytes = storage.read_image_bytes(sid, attachment["file_id"])
                if not image_bytes:
                    continue
                encoded = base64.b64encode(image_bytes).decode()
                parts.append({
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{encoded}",
                })
            elif attachment.get("type") == "pdf":
                pdf_bytes = storage.read_pdf_bytes(sid, attachment["file_id"])
                if not pdf_bytes:
                    continue
                encoded = base64.b64encode(pdf_bytes).decode()
                parts.append({
                    "type": "input_file",
                    "filename": attachment.get("name", "document.pdf"),
                    "file_data": f"data:application/pdf;base64,{encoded}",
                })
        parts.append({"type": "input_text", "text": text})
        history.append({"role": "user", "content": parts})
    return history


async def _ensure_relay_history(sid: str) -> List[Dict[str, Any]]:
    if sid in relay_sessions:
        return relay_sessions[sid]
    chat = await storage.load_chat(sid)
    if chat is None:
        history: List[Dict[str, Any]] = []
    else:
        history = _build_relay_history_from_disk(sid, chat)
    relay_sessions[sid] = history
    relay_locks.setdefault(sid, asyncio.Lock())
    return history


async def _get_or_create_client(
    session_id: str,
    model: str,
    effort: Optional[str] = None,
    thinking_on: Optional[bool] = None,
) -> ClaudeSDKClient:
    if session_id in sessions:
        return sessions[session_id]
    options_kwargs = dict(
        model=model,
        tools=[],
        permission_mode="default",
        include_partial_messages=True,
    )
    if thinking_on is False:
        options_kwargs["thinking"] = {"type": "disabled"}
    else:
        valid_effort = effort if effort in ("low", "medium", "high", "xhigh", "max") else "high"
        options_kwargs["effort"] = valid_effort
    options = ClaudeAgentOptions(**options_kwargs)
    client = ClaudeSDKClient(options=options)
    await client.__aenter__()
    sessions[session_id] = client
    session_locks[session_id] = asyncio.Lock()
    return client


async def _close_session(session_id: str) -> None:
    client = sessions.pop(session_id, None)
    session_locks.pop(session_id, None)
    if client is not None:
        try:
            await client.__aexit__(None, None, None)
        except Exception:
            pass
    relay_sessions.pop(session_id, None)
    relay_locks.pop(session_id, None)


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request) -> StreamingResponse:
    check_auth(request)
    started_at = time.perf_counter()
    session_id = req.session_id or str(uuid.uuid4())
    model = (req.model or DEFAULT_MODEL).strip()

    if req.document_ids and model not in RELAY_MODELS:
        raise HTTPException(
            status_code=400,
            detail=f"PDF 上传仅支持 relay 模型（{sorted(RELAY_MODELS)}）；当前模型：{model}",
        )

    title = (req.title or _derive_title(req.message)).strip() or "新聊天"
    await storage.ensure_chat(
        session_id,
        title=title,
        model=model,
        effort=req.effort,
        thinking=req.thinking,
    )

    attachments = _save_request_attachments(session_id, req.images, req.document_ids)

    user_message: Dict[str, Any] = {
        "role": "user",
        "content": req.message or "",
        "ts": int(time.time() * 1000),
    }
    if attachments:
        user_message["attachments"] = attachments
    await storage.append_message(session_id, user_message, title_if_new=title)

    if model in RELAY_MODELS:
        return await _chat_relay(req, session_id, model, attachments, started_at)
    return await _chat_claude(req, session_id, model, started_at)


class GenState:
    def __init__(self) -> None:
        self.queue: asyncio.Queue = asyncio.Queue()
        self.full_text: str = ""
        self.finished: bool = False


async def _stream_from_state(session_id: str, state: GenState) -> AsyncIterator[str]:
    yield f'data: {{"type":"session","session_id":"{session_id}"}}\n\n'
    while True:
        item = await state.queue.get()
        if item is None:
            yield 'data: {"type":"done"}\n\n'
            return
        kind, payload = item
        if kind == "text":
            yield _sse_text(payload)
        elif kind == "error":
            yield _sse_error(payload)
            return


async def _cancel_existing_gen(sid: str) -> None:
    old_task = active_gens.pop(sid, None)
    if old_task and not old_task.done():
        old_task.cancel()
        try:
            await old_task
        except (asyncio.CancelledError, Exception):
            pass


async def _gen_claude(
    session_id: str,
    client: ClaudeSDKClient,
    lock: asyncio.Lock,
    message: str,
    images: Optional[List[ImagePart]],
    state: GenState,
    t_req: float,
    t_after_client: float,
) -> None:
    acc = ""
    interrupted = False
    try:
        async with lock:
            if images:
                await client.query(_claude_query_iter(message, images))
            else:
                await client.query(message)
            async for msg in client.receive_response():
                if isinstance(msg, StreamEvent):
                    event = msg.event
                    if event.get("type") == "content_block_delta":
                        delta = event.get("delta") or {}
                        if delta.get("type") == "text_delta":
                            chunk = delta.get("text", "")
                            if chunk:
                                acc += chunk
                                state.full_text = acc
                                state.queue.put_nowait(("text", chunk))
                elif isinstance(msg, ResultMessage):
                    break
    except asyncio.CancelledError:
        interrupted = True
        try:
            asyncio.create_task(client.interrupt())
        except Exception:
            pass
        raise
    except Exception as exc:
        state.queue.put_nowait(("error", f"{type(exc).__name__}: {exc}"))
    finally:
        if acc:
            await _persist_assistant(session_id, acc, interrupted)
        state.queue.put_nowait(None)
        state.finished = True
        active_gens.pop(session_id, None)


async def _chat_claude(
    req: ChatRequest, session_id: str, model: str, t_req: float
) -> StreamingResponse:
    client = await _get_or_create_client(
        session_id, model=model, effort=req.effort, thinking_on=req.thinking
    )
    t_after_client = time.perf_counter()
    lock = session_locks[session_id]
    await _cancel_existing_gen(session_id)
    state = GenState()
    task = asyncio.create_task(
        _gen_claude(
            session_id,
            client,
            lock,
            req.message,
            req.images,
            state,
            t_req,
            t_after_client,
        )
    )
    active_gens[session_id] = task
    return StreamingResponse(
        _stream_from_state(session_id, state),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _gen_relay(
    session_id: str,
    model: str,
    message: str,
    images: Optional[List[ImagePart]],
    attachments: List[Dict[str, Any]],
    state: GenState,
    t_req: float,
) -> None:
    provider = _provider_for_model(model)
    if provider is None:
        state.queue.put_nowait(("error", f"未找到模型 {model} 对应的 relay provider，请检查 config.yml"))
        state.queue.put_nowait(None)
        state.finished = True
        active_gens.pop(session_id, None)
        return

    relay_client = relay_clients.get(provider.name)
    if relay_client is None:
        state.queue.put_nowait(("error", f"provider {provider.name} 未配置可用的 base_url/api_key，请检查 config.yml"))
        state.queue.put_nowait(None)
        state.finished = True
        active_gens.pop(session_id, None)
        return

    history = await _ensure_relay_history(session_id)
    lock = relay_locks[session_id]

    pdf_attachments = [item for item in attachments if item.get("type") == "pdf"]
    user_item = _build_relay_user_item_fresh(message, images, pdf_attachments, session_id)
    history.append(user_item)

    acc = ""
    interrupted = False
    api_type = provider.api_type

    try:
        async with lock:
            if api_type == "chat_completions":
                # 转换 history 格式为 chat completions 格式
                chat_messages = _convert_to_chat_completions_format(history)
                response = await relay_client.chat.completions.create(
                    model=model,
                    messages=chat_messages,
                    stream=True,
                )
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        acc += text
                        state.full_text = acc
                        state.queue.put_nowait(("text", text))
            else:
                # responses API (OpenAI 新版)
                response = await relay_client.responses.create(
                    model=model,
                    input=history,
                    stream=True,
                )
                async for event in response:
                    event_type = getattr(event, "type", None)
                    if event_type == "response.output_text.delta":
                        chunk = getattr(event, "delta", "") or ""
                        if not chunk:
                            continue
                        acc += chunk
                        state.full_text = acc
                        state.queue.put_nowait(("text", chunk))
                    elif event_type in ("response.failed", "response.error", "error"):
                        error_obj = getattr(event, "error", None) or getattr(event, "response", None)
                        raise RuntimeError(str(error_obj) if error_obj else f"relay event: {event_type}")

            history.append({"role": "assistant", "content": acc})
    except asyncio.CancelledError:
        interrupted = True
        if acc:
            history.append({"role": "assistant", "content": acc})
        elif history and history[-1].get("role") == "user":
            history.pop()
        raise
    except Exception as exc:
        state.queue.put_nowait(("error", f"{type(exc).__name__}: {exc}"))
        if history and history[-1].get("role") == "user":
            history.pop()
    finally:
        if acc:
            await _persist_assistant(session_id, acc, interrupted)
        state.queue.put_nowait(None)
        state.finished = True
        active_gens.pop(session_id, None)


def _convert_to_chat_completions_format(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将 responses API 格式的 history 转换为 chat completions 格式"""
    messages = []
    for item in history:
        role = item.get("role", "user")
        content = item.get("content", "")

        # 如果 content 是列表（包含图片等），转换为 chat completions 格式
        if isinstance(content, list):
            new_content = []
            for part in content:
                part_type = part.get("type", "")
                if part_type == "input_text":
                    new_content.append({"type": "text", "text": part.get("text", "")})
                elif part_type == "input_image":
                    new_content.append({
                        "type": "image_url",
                        "image_url": {"url": part.get("image_url", "")}
                    })
                elif part_type == "input_file":
                    # PDF 文件转为文本提示（chat completions 不直接支持 PDF）
                    new_content.append({
                        "type": "text",
                        "text": f"[附件: {part.get('filename', 'document.pdf')}]"
                    })
            messages.append({"role": role, "content": new_content})
        else:
            messages.append({"role": role, "content": content})

    return messages


async def _chat_relay(
    req: ChatRequest,
    session_id: str,
    model: str,
    attachments: List[Dict[str, Any]],
    t_req: float,
) -> StreamingResponse:
    await _cancel_existing_gen(session_id)
    state = GenState()
    task = asyncio.create_task(
        _gen_relay(session_id, model, req.message, req.images, attachments, state, t_req)
    )
    active_gens[session_id] = task
    return StreamingResponse(
        _stream_from_state(session_id, state),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse_text(chunk: str) -> str:
    import json as json_module
    return f"data: {json_module.dumps({'type': 'text', 'text': chunk}, ensure_ascii=False)}\n\n"


def _sse_error(msg: str) -> str:
    import json as json_module
    return f"data: {json_module.dumps({'type': 'error', 'error': msg}, ensure_ascii=False)}\n\n"


async def _persist_assistant(sid: str, text: str, interrupted: bool) -> None:
    if not text:
        return
    message: Dict[str, Any] = {
        "role": "assistant",
        "content": text,
        "ts": int(time.time() * 1000),
    }
    if interrupted:
        message["interrupted"] = True
    await storage.append_message(sid, message)


@app.post("/api/reset")
async def reset(req: ResetRequest, request: Request) -> JSONResponse:
    check_auth(request)
    if req.session_id:
        await _close_session(req.session_id)
    return JSONResponse({"ok": True})


@app.get("/api/models")
async def get_available_models(request: Request) -> JSONResponse:
    """返回所有可用模型列表"""
    check_auth(request)

    models = []

    # Claude models (via Claude Agent SDK)
    claude_models = [
        {"id": "claude-opus-4-7", "name": "Opus 4.7", "short": "Opus 4.7", "desc": "最强大的 Claude 模型", "category": "claude"},
        {"id": "claude-sonnet-4-6", "name": "Sonnet 4.6", "short": "Sonnet 4.6", "desc": "平衡性能与速度", "category": "claude"},
        {"id": "claude-haiku-4-5", "name": "Haiku 4.5", "short": "Haiku 4.5", "desc": "快速响应", "category": "claude"},
    ]
    models.extend(claude_models)

    # Relay API 模型（从 config.yml 读取）
    for provider_name, provider in RELAY_PROVIDERS.items():
        for model_id in provider.models:
            models.append({
                "id": model_id,
                "name": model_id,
                "short": model_id,
                "desc": f"来自 {provider_name}",
                "provider": provider_name,
                "category": "api",
                "supports_pdf": True
            })

    return JSONResponse({"models": models})


@app.get("/api/config/providers")
async def get_providers(request: Request) -> JSONResponse:
    """返回所有 API 提供商配置（密钥脱敏）"""
    check_auth(request)

    providers_list = []
    for provider_name, provider in RELAY_PROVIDERS.items():
        masked_key = ""
        if provider.api_key:
            if len(provider.api_key) > 8:
                masked_key = provider.api_key[:4] + "•" * 20 + provider.api_key[-4:]
            else:
                masked_key = "•" * len(provider.api_key)

        providers_list.append({
            "name": provider_name,
            "base_url": provider.base_url,
            "api_key_masked": masked_key,
            "models": provider.models,
            "api_type": provider.api_type,
        })

    return JSONResponse({"providers": providers_list})


class ProviderRequest(BaseModel):
    name: str
    base_url: str
    api_key: str
    model: str
    api_type: str = "responses"  # "responses" 或 "chat_completions"


@app.post("/api/config/providers")
async def save_provider(req: ProviderRequest, request: Request) -> JSONResponse:
    """保存/更新提供商配置，写入 config.yml"""
    check_auth(request)

    name = req.name.strip()
    base_url = req.base_url.strip()
    api_key = req.api_key.strip()
    model = req.model.strip()
    api_type = req.api_type.strip()
    if api_type not in ("responses", "chat_completions"):
        api_type = "responses"

    if not name or not base_url or not model:
        return JSONResponse({"ok": False, "error": "提供商名称、API 地址和模型名称必须填写"}, status_code=400)

    # 读取现有配置
    if CONFIG_PATH.exists():
        config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    else:
        config = {}

    if "relay" not in config:
        config["relay"] = {}
    if "providers" not in config["relay"]:
        config["relay"]["providers"] = {}

    # 检查是否已存在该提供商
    if name in config["relay"]["providers"]:
        # 更新现有提供商：保留原有模型，添加新模型（如果不存在）
        existing = config["relay"]["providers"][name]
        existing_models = existing.get("models", [])
        if isinstance(existing_models, str):
            existing_models = [existing_models]

        # 添加新模型（去重）
        if model not in existing_models:
            existing_models.append(model)

        # 如果 API 密钥为空，使用原有密钥
        if not api_key:
            api_key = existing.get("api_key", "")

        if not api_key:
            return JSONResponse({"ok": False, "error": "API 密钥不能为空"}, status_code=400)

        config["relay"]["providers"][name] = {
            "base_url": base_url,
            "api_key": api_key,
            "models": existing_models,
            "api_type": api_type
        }
    else:
        # 新建提供商，必须提供 API 密钥
        if not api_key:
            return JSONResponse({"ok": False, "error": "新建提供商时 API 密钥不能为空"}, status_code=400)

        config["relay"]["providers"][name] = {
            "base_url": base_url,
            "api_key": api_key,
            "models": [model],
            "api_type": api_type
        }

    # 如果是第一个提供商，设为默认
    if not config["relay"].get("default_provider"):
        config["relay"]["default_provider"] = name

    # 写入文件
    CONFIG_PATH.write_text(yaml.dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    # 重新加载配置
    global RELAY_PROVIDERS, DEFAULT_RELAY_PROVIDER, RELAY_MODEL_TO_PROVIDER, RELAY_MODELS, relay_clients
    RELAY_PROVIDERS, DEFAULT_RELAY_PROVIDER = _load_relay_config()

    # 重建模型映射
    RELAY_MODEL_TO_PROVIDER.clear()
    for provider_name, provider in RELAY_PROVIDERS.items():
        for model_name in provider.models:
            RELAY_MODEL_TO_PROVIDER[model_name] = provider_name
    RELAY_MODELS = set(RELAY_MODEL_TO_PROVIDER.keys())

    # 重建 relay_clients
    relay_clients.clear()
    for provider_name, provider in RELAY_PROVIDERS.items():
        if provider.base_url and provider.api_key:
            relay_clients[provider_name] = AsyncOpenAI(
                api_key=provider.api_key,
                base_url=provider.base_url,
            )

    return JSONResponse({"ok": True})


@app.delete("/api/config/providers/{name}")
async def delete_provider(name: str, request: Request) -> JSONResponse:
    """删除提供商"""
    check_auth(request)

    if not CONFIG_PATH.exists():
        return JSONResponse({"ok": False, "error": "配置文件不存在"}, status_code=404)

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}

    if "relay" not in config or "providers" not in config["relay"]:
        return JSONResponse({"ok": False, "error": "提供商不存在"}, status_code=404)

    if name not in config["relay"]["providers"]:
        return JSONResponse({"ok": False, "error": "提供商不存在"}, status_code=404)

    # 删除提供商
    del config["relay"]["providers"][name]

    # 如果删除的是默认提供商，更新默认值
    if config["relay"].get("default_provider") == name:
        if config["relay"]["providers"]:
            config["relay"]["default_provider"] = next(iter(config["relay"]["providers"].keys()))
        else:
            config["relay"]["default_provider"] = ""

    # 写入文件
    CONFIG_PATH.write_text(yaml.dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    # 重新加载配置
    global RELAY_PROVIDERS, DEFAULT_RELAY_PROVIDER, RELAY_MODEL_TO_PROVIDER, RELAY_MODELS, relay_clients
    RELAY_PROVIDERS, DEFAULT_RELAY_PROVIDER = _load_relay_config()

    RELAY_MODEL_TO_PROVIDER.clear()
    for provider_name, provider in RELAY_PROVIDERS.items():
        for model_name in provider.models:
            RELAY_MODEL_TO_PROVIDER[model_name] = provider_name
    RELAY_MODELS = set(RELAY_MODEL_TO_PROVIDER.keys())

    # 关闭并移除对应的 client
    if name in relay_clients:
        try:
            await relay_clients[name].close()
        except Exception:
            pass
        del relay_clients[name]

    return JSONResponse({"ok": True})


@app.delete("/api/config/providers/{name}/models/{model}")
async def delete_provider_model(name: str, model: str, request: Request) -> JSONResponse:
    """删除提供商的某个模型"""
    check_auth(request)

    if not CONFIG_PATH.exists():
        return JSONResponse({"ok": False, "error": "配置文件不存在"}, status_code=404)

    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}

    if "relay" not in config or "providers" not in config["relay"]:
        return JSONResponse({"ok": False, "error": "提供商不存在"}, status_code=404)

    if name not in config["relay"]["providers"]:
        return JSONResponse({"ok": False, "error": "提供商不存在"}, status_code=404)

    provider = config["relay"]["providers"][name]
    models = provider.get("models", [])
    if isinstance(models, str):
        models = [models]

    if model not in models:
        return JSONResponse({"ok": False, "error": "模型不存在"}, status_code=404)

    # 删除模型
    models.remove(model)

    # 如果没有模型了，删除整个提供商
    if not models:
        del config["relay"]["providers"][name]
        if config["relay"].get("default_provider") == name:
            if config["relay"]["providers"]:
                config["relay"]["default_provider"] = next(iter(config["relay"]["providers"].keys()))
            else:
                config["relay"]["default_provider"] = ""
    else:
        # 更新模型列表
        provider["models"] = models

    # 写入文件
    CONFIG_PATH.write_text(yaml.dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")

    # 重新加载配置
    global RELAY_PROVIDERS, DEFAULT_RELAY_PROVIDER, RELAY_MODEL_TO_PROVIDER, RELAY_MODELS, relay_clients
    RELAY_PROVIDERS, DEFAULT_RELAY_PROVIDER = _load_relay_config()

    RELAY_MODEL_TO_PROVIDER.clear()
    for provider_name, provider in RELAY_PROVIDERS.items():
        for model_name in provider.models:
            RELAY_MODEL_TO_PROVIDER[model_name] = provider_name
    RELAY_MODELS = set(RELAY_MODEL_TO_PROVIDER.keys())

    # 如果提供商被删除，关闭 client
    if not models and name in relay_clients:
        try:
            await relay_clients[name].close()
        except Exception:
            pass
        del relay_clients[name]

    return JSONResponse({"ok": True})


class TestProviderRequest(BaseModel):
    base_url: str
    api_key: str
    model: str
    api_type: str = "responses"


@app.post("/api/config/test")
async def test_provider(req: TestProviderRequest, request: Request) -> JSONResponse:
    """测试 API 连接是否有效"""
    check_auth(request)

    try:
        test_client = AsyncOpenAI(
            api_key=req.api_key.strip(),
            base_url=req.base_url.strip(),
        )

        api_type = req.api_type.strip()
        if api_type not in ("responses", "chat_completions"):
            api_type = "responses"

        # 根据 api_type 选择不同的接口
        if api_type == "chat_completions":
            response = await test_client.chat.completions.create(
                model=req.model.strip(),
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=10,
            )
        else:
            response = await test_client.responses.create(
                model=req.model.strip(),
                input=[{"role": "user", "content": "hi"}],
                stream=False,
            )

        await test_client.close()

        return JSONResponse({"ok": True, "message": "连接成功"})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"连接失败: {str(exc)}"}, status_code=400)


# ============== 英语学习功能 API ==============

@app.get("/api/dictionary/{word}")
async def lookup_word_api(word: str, request: Request) -> JSONResponse:
    """查询单词释义"""
    check_auth(request)

    try:
        result = dictionary.lookup_word(word)

        if result is None:
            return JSONResponse({"ok": False, "error": "未找到该单词"}, status_code=404)

        return JSONResponse({"ok": True, "data": result})

    except FileNotFoundError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=503)
    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"查询失败: {str(exc)}"}, status_code=500)


class VocabRequest(BaseModel):
    word: str
    phonetic: str = ""
    translation: str = ""


@app.get("/api/vocabulary")
async def get_vocabulary_api(request: Request) -> JSONResponse:
    """获取生词本"""
    check_auth(request)

    try:
        vocab_db = vocabulary.get_vocabulary_db()
        words = vocab_db.get_all_words()
        stats = vocab_db.get_stats()

        return JSONResponse({
            "ok": True,
            "words": words,
            "stats": stats
        })

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"获取生词本失败: {str(exc)}"}, status_code=500)


@app.post("/api/vocabulary")
async def add_word_to_vocabulary_api(req: VocabRequest, request: Request) -> JSONResponse:
    """添加单词到生词本"""
    check_auth(request)

    try:
        vocab_db = vocabulary.get_vocabulary_db()

        # 检查是否已存在
        if vocab_db.is_word_in_vocab(req.word):
            return JSONResponse({"ok": False, "error": "该单词已在生词本中"}, status_code=400)

        success = vocab_db.add_word(req.word, req.phonetic, req.translation)

        if success:
            return JSONResponse({"ok": True, "message": "添加成功"})
        else:
            return JSONResponse({"ok": False, "error": "添加失败"}, status_code=500)

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"添加失败: {str(exc)}"}, status_code=500)


@app.delete("/api/vocabulary/{word}")
async def remove_word_from_vocabulary_api(word: str, request: Request) -> JSONResponse:
    """从生词本删除单词"""
    check_auth(request)

    try:
        vocab_db = vocabulary.get_vocabulary_db()
        success = vocab_db.remove_word(word)

        if success:
            return JSONResponse({"ok": True, "message": "删除成功"})
        else:
            return JSONResponse({"ok": False, "error": "单词不存在"}, status_code=404)

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"删除失败: {str(exc)}"}, status_code=500)


@app.post("/api/vocabulary/{word}/review")
async def review_word_api(word: str, request: Request) -> JSONResponse:
    """标记单词为已复习"""
    check_auth(request)

    try:
        vocab_db = vocabulary.get_vocabulary_db()
        success = vocab_db.update_review(word)

        if success:
            return JSONResponse({"ok": True, "message": "复习记录已更新"})
        else:
            return JSONResponse({"ok": False, "error": "单词不存在"}, status_code=404)

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"更新失败: {str(exc)}"}, status_code=500)


@app.get("/api/vocabulary/check/{word}")
async def check_word_in_vocabulary_api(word: str, request: Request) -> JSONResponse:
    """检查单词是否在生词本中"""
    check_auth(request)

    try:
        vocab_db = vocabulary.get_vocabulary_db()
        exists = vocab_db.is_word_in_vocab(word)

        return JSONResponse({"ok": True, "exists": exists})

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"检查失败: {str(exc)}"}, status_code=500)


# ============== 英语阅读专项 API ==============

@app.get("/api/reading/articles")
async def get_articles_api(request: Request, difficulty: Optional[str] = None) -> JSONResponse:
    """获取文章列表"""
    check_auth(request)

    try:
        reading_db = reading.get_reading_db()
        articles = reading_db.get_articles(difficulty)

        return JSONResponse({"ok": True, "articles": articles})

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"获取文章列表失败: {str(exc)}"}, status_code=500)


@app.get("/api/reading/articles/{article_id}")
async def get_article_api(article_id: int, request: Request) -> JSONResponse:
    """获取文章详情"""
    check_auth(request)

    try:
        reading_db = reading.get_reading_db()
        article = reading_db.get_article(article_id)

        if article is None:
            return JSONResponse({"ok": False, "error": "文章不存在"}, status_code=404)

        return JSONResponse({"ok": True, "article": article})

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"获取文章失败: {str(exc)}"}, status_code=500)


@app.get("/api/reading/articles/{article_id}/questions")
async def get_questions_api(article_id: int, request: Request) -> JSONResponse:
    """获取文章的题目"""
    check_auth(request)

    try:
        reading_db = reading.get_reading_db()
        questions = reading_db.get_questions(article_id)

        return JSONResponse({"ok": True, "questions": questions})

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"获取题目失败: {str(exc)}"}, status_code=500)


class StartReadingRequest(BaseModel):
    article_id: int


@app.post("/api/reading/start")
async def start_reading_api(req: StartReadingRequest, request: Request) -> JSONResponse:
    """开始阅读（创建答题记录）"""
    check_auth(request)

    try:
        reading_db = reading.get_reading_db()
        record_id = reading_db.create_record(req.article_id)

        if record_id == 0:
            return JSONResponse({"ok": False, "error": "创建记录失败"}, status_code=500)

        return JSONResponse({"ok": True, "record_id": record_id})

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"开始阅读失败: {str(exc)}"}, status_code=500)


class SubmitAnswersRequest(BaseModel):
    record_id: int
    answers: Dict[str, str]


@app.post("/api/reading/submit")
async def submit_answers_api(req: SubmitAnswersRequest, request: Request) -> JSONResponse:
    """提交答案"""
    check_auth(request)

    try:
        reading_db = reading.get_reading_db()
        result = reading_db.submit_answers(req.record_id, req.answers)

        if not result.get("ok"):
            return JSONResponse(result, status_code=400)

        return JSONResponse(result)

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"提交答案失败: {str(exc)}"}, status_code=500)


@app.get("/api/reading/stats")
async def get_reading_stats_api(request: Request) -> JSONResponse:
    """获取阅读统计"""
    check_auth(request)

    try:
        reading_db = reading.get_reading_db()
        stats = reading_db.get_stats()

        return JSONResponse({"ok": True, "stats": stats})

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"获取统计失败: {str(exc)}"}, status_code=500)


@app.get("/api/reading/records")
async def get_reading_records_api(request: Request, limit: int = 20) -> JSONResponse:
    """获取答题记录"""
    check_auth(request)

    try:
        reading_db = reading.get_reading_db()
        records = reading_db.get_records(limit)

        return JSONResponse({"ok": True, "records": records})

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"获取记录失败: {str(exc)}"}, status_code=500)


class GenerateArticleRequest(BaseModel):
    model: str
    topic: str
    count: int = 1


@app.post("/api/reading/generate")
async def generate_article_api(req: GenerateArticleRequest, request: Request) -> StreamingResponse:
    """AI 生成阅读文章（流式返回）"""
    check_auth(request)

    async def generate_stream():
        try:
            # 生成提示词
            prompt = f"""You are an expert in creating CET-6 (College English Test Band 6) reading comprehension materials. Generate a high-quality article with questions that match the exact difficulty and style of real CET-6 exams.

ARTICLE REQUIREMENTS:
- Length: 400-500 words (strictly enforce this)
- Academic and formal tone
- Clear structure: Introduction → Body (evidence/research/analysis) → Conclusion
- Use CET-6 level vocabulary (avoid overly simple or overly complex words)
- Include complex sentence structures, subordinate clauses, and passive voice
- Present balanced perspectives or research findings
- Use transition words: however, moreover, furthermore, nevertheless, consequently
- Include specific examples, statistics, or expert opinions

TOPIC: {req.topic}

QUESTION REQUIREMENTS:
Generate exactly 5 multiple-choice questions following this pattern:

Question 1: Main idea / Author's purpose
Question 2: Specific detail
Question 3: Inference / Implication
Question 4: Vocabulary in context / Reference
Question 5: Attitude / Tone

Each question must have:
- 4 options (A, B, C, D)
- Only ONE correct answer
- Distractors that are plausible but clearly wrong

OUTPUT FORMAT (JSON):
{{
  "title": "Article Title",
  "content": "Full article text...",
  "difficulty": "intermediate",
  "questions": [
    {{
      "question": "Question text?",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "answer": "A",
      "explanation": "Why this is correct..."
    }}
  ]
}}

Generate {req.count} article(s). Return as JSON array if count > 1."""

            # 判断是 Claude 还是 API 模型
            if req.model.startswith("claude-"):
                # 使用 Claude SDK
                sid = "generate_" + str(int(time.time()))
                if sid not in sessions:
                    sessions[sid] = ClaudeSDKClient(
                        ClaudeAgentOptions(model=req.model, thinking={"type": "disabled"})
                    )
                    session_locks[sid] = asyncio.Lock()

                async with session_locks[sid]:
                    full_text = ""
                    async for event in sessions[sid].send_message(prompt):
                        if isinstance(event, StreamEvent):
                            if event.type == "text":
                                chunk = event.text or ""
                                full_text += chunk
                                yield f"data: {json.dumps({'type': 'text', 'text': chunk})}\n\n"
                        elif isinstance(event, ResultMessage):
                            if event.text:
                                full_text = event.text

                    # 解析生成的 JSON
                    try:
                        # 提取 JSON（可能被包裹在 ```json ``` 中）
                        json_text = full_text
                        if "```json" in json_text:
                            json_text = json_text.split("```json")[1].split("```")[0].strip()
                        elif "```" in json_text:
                            json_text = json_text.split("```")[1].split("```")[0].strip()

                        articles_data = json.loads(json_text)
                        if not isinstance(articles_data, list):
                            articles_data = [articles_data]

                        # 保存到数据库
                        reading_db = reading.get_reading_db()
                        saved_articles = []
                        for article_data in articles_data:
                            article_id = reading_db.add_article(
                                title=article_data.get("title", "Untitled"),
                                content=article_data.get("content", ""),
                                difficulty=article_data.get("difficulty", "intermediate"),
                                questions=article_data.get("questions", [])
                            )
                            saved_articles.append({"id": article_id, "title": article_data.get("title")})

                        yield f"data: {json.dumps({'type': 'done', 'articles': saved_articles})}\n\n"

                    except json.JSONDecodeError as e:
                        yield f"data: {json.dumps({'type': 'error', 'error': f'JSON解析失败: {str(e)}'})}\n\n"

            else:
                # 使用 API 模型
                provider = _provider_for_model(req.model)
                if not provider:
                    yield f"data: {json.dumps({'type': 'error', 'error': '未找到对应的 API 提供商'})}\n\n"
                    return

                client = relay_clients.get(provider.name)
                if not client:
                    yield f"data: {json.dumps({'type': 'error', 'error': 'API 客户端未初始化'})}\n\n"
                    return

                full_text = ""
                if provider.api_type == "responses":
                    # Responses API
                    stream = await client.chat.completions.create(
                        model=req.model,
                        messages=[{"role": "user", "content": prompt}],
                        stream=True,
                    )
                    async for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            text = chunk.choices[0].delta.content
                            full_text += text
                            yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"
                else:
                    # Chat Completions API
                    stream = await client.chat.completions.create(
                        model=req.model,
                        messages=[{"role": "user", "content": prompt}],
                        stream=True,
                    )
                    async for chunk in stream:
                        if chunk.choices and chunk.choices[0].delta.content:
                            text = chunk.choices[0].delta.content
                            full_text += text
                            yield f"data: {json.dumps({'type': 'text', 'text': text})}\n\n"

                # 解析并保存
                try:
                    json_text = full_text
                    if "```json" in json_text:
                        json_text = json_text.split("```json")[1].split("```")[0].strip()
                    elif "```" in json_text:
                        json_text = json_text.split("```")[1].split("```")[0].strip()

                    articles_data = json.loads(json_text)
                    if not isinstance(articles_data, list):
                        articles_data = [articles_data]

                    reading_db = reading.get_reading_db()
                    saved_articles = []
                    for article_data in articles_data:
                        article_id = reading_db.add_article(
                            title=article_data.get("title", "Untitled"),
                            content=article_data.get("content", ""),
                            difficulty=article_data.get("difficulty", "intermediate"),
                            questions=article_data.get("questions", [])
                        )
                        saved_articles.append({"id": article_id, "title": article_data.get("title")})

                    yield f"data: {json.dumps({'type': 'done', 'articles': saved_articles})}\n\n"

                except json.JSONDecodeError as e:
                    yield f"data: {json.dumps({'type': 'error', 'error': f'JSON解析失败: {str(e)}'})}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


@app.delete("/api/reading/articles/{article_id}")
async def delete_article_api(article_id: int, request: Request) -> JSONResponse:
    """删除文章"""
    check_auth(request)

    try:
        reading_db = reading.get_reading_db()
        success = reading_db.delete_article(article_id)

        if not success:
            return JSONResponse({"ok": False, "error": "文章不存在或删除失败"}, status_code=404)

        return JSONResponse({"ok": True})

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"删除文章失败: {str(exc)}"}, status_code=500)


class UpdateArticleRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    difficulty: Optional[str] = None


@app.put("/api/reading/articles/{article_id}")
async def update_article_api(article_id: int, req: UpdateArticleRequest, request: Request) -> JSONResponse:
    """更新文章"""
    check_auth(request)

    try:
        reading_db = reading.get_reading_db()
        success = reading_db.update_article(
            article_id=article_id,
            title=req.title,
            content=req.content,
            difficulty=req.difficulty
        )

        if not success:
            return JSONResponse({"ok": False, "error": "文章不存在或更新失败"}, status_code=404)

        return JSONResponse({"ok": True})

    except Exception as exc:
        return JSONResponse({"ok": False, "error": f"更新文章失败: {str(exc)}"}, status_code=500)


# ============== 管理 API ==============

@app.get("/api/health")
async def health_check() -> JSONResponse:
    """健康检查接口（无需认证）"""
    return JSONResponse({"ok": True, "status": "running", "timestamp": int(time.time())})


@app.post("/api/admin/restart")
async def restart_server(request: Request) -> JSONResponse:
    """重启服务器"""
    check_auth(request)

    import sys
    import subprocess

    try:
        # 在后台重启服务器
        python = sys.executable
        script = sys.argv[0]

        # 延迟1秒后重启
        if os.name == 'nt':  # Windows
            subprocess.Popen(
                f'timeout /t 1 /nobreak > nul && "{python}" "{script}"',
                shell=True,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:  # Linux/Mac
            subprocess.Popen(
                f'sleep 1 && "{python}" "{script}"',
                shell=True,
                start_new_session=True
            )

        # 返回成功后退出当前进程
        asyncio.create_task(_shutdown_after_delay())

        return JSONResponse({"ok": True, "message": "服务器将在1秒后重启"})

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.post("/api/admin/stop")
async def stop_server(request: Request) -> JSONResponse:
    """停止服务器"""
    check_auth(request)

    try:
        # 延迟1秒后停止
        asyncio.create_task(_shutdown_after_delay())
        return JSONResponse({"ok": True, "message": "服务器将在1秒后停止"})

    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


async def _shutdown_after_delay():
    """延迟关闭服务器"""
    await asyncio.sleep(1)
    os._exit(0)


if __name__ == "__main__":
    import uvicorn

    print(f"启动中... 本机访问 http://localhost:{PORT}")
    print(f"管理面板：http://localhost:{PORT}/admin.html")
    print(f"登录密码：{PASSWORD}")
    print(f"默认模型：{DEFAULT_MODEL}（走 Claude CLI 登录态）")
    print(f"聊天落盘目录：{storage.CHATS_DIR}")
    if RELAY_MODELS:
        print(f"relay 可用模型：{sorted(RELAY_MODELS)}")
        for provider_name, provider in RELAY_PROVIDERS.items():
            masked_key = provider.api_key[:6] + "..." if provider.api_key else "<empty>"
            print(f"  - {provider_name}: {provider.base_url} models={provider.models} key={masked_key}")
    else:
        print("relay 未配置任何模型；切到非 Claude 模型会报错")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
