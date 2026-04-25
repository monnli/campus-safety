"""检测参数动态配置 - 运行时修改，立即生效"""
import json
import os
import threading

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "detection_config.json")
_lock = threading.Lock()

_config = {
    "confidence": 0.5,
    "frameSkip": 3,
    "cooldown": 30,
    "preSeconds": 5,
    "postSeconds": 5,
    "dangerClasses": ["fighting", "falling", "intrusion"],
}


def load():
    global _config
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                _config.update(json.load(f))
        except Exception:
            pass
    return dict(_config)


def save(new_config):
    global _config
    with _lock:
        _config.update(new_config)
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(_config, f, ensure_ascii=False, indent=2)


def get(key, default=None):
    with _lock:
        return _config.get(key, default)


# 启动时加载
load()
