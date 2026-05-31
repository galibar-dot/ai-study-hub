"""服务器管理后端
启动方式: python server_manager.py
默认监听 127.0.0.1:9000
"""

import json
import os
import sys
import time
import subprocess
import psutil
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ----------------------- 配置 -----------------------

HOST = "127.0.0.1"
MANAGER_PORT = 9000
SERVER_PORT = 8000
SERVER_SCRIPT = Path(__file__).resolve().parent / "server.py"
PYTHON_EXE = r"C:\Users\Lenovo\AppData\Local\Python\bin\python.exe"
SERVER_URL = f"http://localhost:{SERVER_PORT}"

# 静态资源
INDEX_HTML_PATH = Path(__file__).resolve().parent / "server_manager.html"

# 服务器进程
server_process = {"proc": None, "pid": None}

# ----------------------- 业务逻辑 -----------------------

def find_server_process():
    """查找正在运行的服务器进程"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                cmdline_str = ' '.join(cmdline).lower()
                if 'python' in cmdline_str and 'server.py' in cmdline_str:
                    # 检查是否监听8000端口
                    try:
                        connections = proc.connections()
                        for conn in connections:
                            if conn.status == 'LISTEN' and conn.laddr.port == SERVER_PORT:
                                return proc
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        print(f"查找进程时出错: {e}")
    return None

def get_server_status():
    """获取服务器状态"""
    proc = find_server_process()
    if proc:
        try:
            return {
                "running": True,
                "pid": proc.pid,
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
                "create_time": proc.create_time(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return {"running": False}
    return {"running": False}

def start_server():
    """启动服务器"""
    global server_process

    # 检查是否已经在运行
    if find_server_process():
        return {"ok": False, "error": "服务器已在运行"}

    try:
        # 启动服务器进程
        if sys.platform == "win32":
            proc = subprocess.Popen(
                [PYTHON_EXE, str(SERVER_SCRIPT)],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                cwd=SERVER_SCRIPT.parent
            )
        else:
            proc = subprocess.Popen(
                [sys.executable, str(SERVER_SCRIPT)],
                start_new_session=True,
                cwd=SERVER_SCRIPT.parent
            )

        server_process["proc"] = proc
        server_process["pid"] = proc.pid

        # 等待服务器启动
        time.sleep(2)

        # 验证服务器是否成功启动
        if find_server_process():
            return {"ok": True, "pid": proc.pid, "message": "服务器启动成功"}
        else:
            return {"ok": False, "error": "服务器启动失败"}

    except Exception as e:
        return {"ok": False, "error": f"启动失败: {str(e)}"}

def stop_server():
    """停止服务器"""
    proc = find_server_process()
    if not proc:
        return {"ok": False, "error": "服务器未运行"}

    try:
        # 尝试优雅关闭
        proc.terminate()

        # 等待最多5秒
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            # 强制关闭
            proc.kill()
            proc.wait(timeout=2)

        return {"ok": True, "message": "服务器已停止"}
    except Exception as e:
        return {"ok": False, "error": f"停止失败: {str(e)}"}

def restart_server():
    """重启服务器"""
    # 先停止
    stop_result = stop_server()
    if not stop_result["ok"] and "未运行" not in stop_result.get("error", ""):
        return stop_result

    # 等待一下
    time.sleep(1)

    # 再启动
    return start_server()

# ----------------------- HTTP 处理 -----------------------

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # 只打印错误
        if args and isinstance(args[1], str) and not args[1].startswith("2"):
            sys.stderr.write(f"{self.address_string()} - {fmt % args}\n")

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_error(404, "Not Found")
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        if path == "/" or path == "/index.html":
            self._send_file(INDEX_HTML_PATH, "text/html; charset=utf-8")
        elif path == "/api/status":
            self._send_json(get_server_status())
        else:
            self.send_error(404)

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path

        try:
            if path == "/api/start":
                self._send_json(start_server())
            elif path == "/api/stop":
                self._send_json(stop_server())
            elif path == "/api/restart":
                self._send_json(restart_server())
            else:
                self._send_json({"ok": False, "error": f"未知 API: {path}"}, 404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send_json({"ok": False, "error": f"{type(e).__name__}: {e}"}, 500)

# ----------------------- 启动 -----------------------

def main():
    server = ThreadingHTTPServer((HOST, MANAGER_PORT), Handler)
    url = f"http://{HOST}:{MANAGER_PORT}/"
    print(f"\n  服务器管理面板已启动")
    print(f"  访问: {url}")
    print(f"  主服务器地址: {SERVER_URL}")
    print(f"  按 Ctrl+C 退出\n")

    # 延迟0.5s打开浏览器
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  关闭中...")
        server.shutdown()

if __name__ == "__main__":
    main()
