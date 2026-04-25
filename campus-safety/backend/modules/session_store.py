"""会话状态持久化 - 保存摄像头接入状态，重启后自动恢复"""
import json
import os
import threading

SESSION_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "session.json")
_lock = threading.Lock()


def _load():
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"cameras": {}}


def _save(data):
    os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_camera_source(camera_id, source):
    """保存摄像头视频源"""
    with _lock:
        data = _load()
        data["cameras"][camera_id] = str(source)
        _save(data)


def remove_camera_source(camera_id):
    """移除摄像头视频源"""
    with _lock:
        data = _load()
        data["cameras"].pop(camera_id, None)
        _save(data)


def get_all_camera_sources():
    """获取所有已保存的摄像头视频源"""
    with _lock:
        data = _load()
        return dict(data.get("cameras", {}))
