import json
import os
from pathlib import Path
import socket
import tempfile
import time
import uuid

import comfy.model_management as mm
import folder_paths

from .prompting import ANALYSIS_INSTRUCTION


def rpc(method, params, interruptible=True):
    endpoint = os.environ.get("DSH_BATON_SOCKET", str(Path.home() / ".dsh-baton" / "host.sock"))
    request_id = uuid.uuid4().hex
    request = {"id": request_id, "method": method, "params": params}
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(0.5)
        try:
            connection.connect(endpoint)
        except (FileNotFoundError, ConnectionRefusedError) as exc:
            raise RuntimeError("请打开已登录的 DeepSeek Harness，并启用 dsh-baton-host 插件后重试。") from exc
        connection.sendall((json.dumps(request, ensure_ascii=False) + "\n").encode())
        buffer = b""
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if interruptible:
                mm.throw_exception_if_processing_interrupted()
            try:
                chunk = connection.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                raise RuntimeError("DSH 本地桥接连接已关闭，请检查 Harness 是否仍在运行。")
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                message = json.loads(line)
                if message.get("id") != request_id:
                    continue
                if message.get("error"):
                    raise RuntimeError("DSH 桥接错误：" + str(message["error"]))
                return message["result"]
        raise RuntimeError("DSH 本地桥接请求超时，请检查 Harness。")


def analyze_dsh(image, identity_image):
    workspace = Path(folder_paths.get_user_directory()) / "two-reference-transfer"
    workspace.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="image-", dir=workspace) as temp:
        image_path = Path(temp) / "reference.png"
        identity_path = Path(temp) / "identity.png"
        image.save(image_path, format="PNG")
        identity_image.save(identity_path, format="PNG")
        task = (
            "这是 ComfyUI 插件的一次图片内容分析。只看图并回答，不修改文件，不编写代码，不运行测试。"
            "必须用实际看图工具分别读取以下两张 PNG；不要根据文件名或元数据猜测。"
            "若不能看图，请只返回 {\"error\":\"vision unavailable\"}。\n"
            + "\nImage 1 (identity): " + str(identity_path)
            + "\nImage 2 (pose, clothing, scene): " + str(image_path) + "\n\n" + ANALYSIS_INSTRUCTION
        )
        started = rpc("send", {"message": task, "cwd": str(workspace), "sender": "comfyui"})
        run_id = started["run_id"]
        completed = False
        deadline = time.monotonic() + 360
        try:
            while time.monotonic() < deadline:
                result = rpc("wait", {"run_id": run_id, "timeout_s": 30})
                if result.get("needs_input"):
                    raise RuntimeError("DSH 需要你在 Harness 中确认或回答；请处理相关设置后重新运行分析。")
                state = result["state"]
                if state == "completed":
                    completed = True
                    return result.get("final_text") or ""
                if state in ("failed", "cancelled", "interrupted"):
                    completed = True
                    raise RuntimeError("DSH 分析未完成：" + str(result.get("error") or state))
            raise RuntimeError("DSH 看图超过 6 分钟，请检查网络后重试。")
        finally:
            if not completed:
                try:
                    rpc("cancel", {"run_id": run_id}, interruptible=False)
                except (OSError, RuntimeError):
                    pass
