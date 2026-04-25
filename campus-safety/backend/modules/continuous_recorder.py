"""持续录像模块 - 按时间段对指定摄像头进行持续录制"""
import os
import cv2
import json
import time
import threading
from datetime import datetime, timedelta
from config import Config

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "recording_config.json")

# 默认配置
_DEFAULT_CONFIG = {
    "enabled": False,
    "segment_minutes": 30,
    "schedule_start": "07:30",
    "schedule_end": "18:30",
    "camera_ids": [],
    "retention_days": 7,  # 录像保留天数
}

_recording_config = dict(_DEFAULT_CONFIG)
_active_recorders = {}
_config_lock = threading.Lock()

RECORDINGS_DIR = os.path.join(os.path.dirname(__file__), "..", "static", "recordings")


def _load_config():
    """从文件加载配置"""
    global _recording_config
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                _recording_config.update(saved)
        except Exception as e:
            print(f"[Recorder] 加载配置失败: {e}")


def _save_config():
    """保存配置到文件"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(_recording_config, f, ensure_ascii=False, indent=2)


# 启动时加载配置
_load_config()


def get_config():
    with _config_lock:
        return dict(_recording_config)


def update_config(new_config):
    with _config_lock:
        _recording_config.update(new_config)
        _save_config()
    _apply_config()


def _in_schedule():
    """判断当前时间是否在录像时间段内"""
    now = datetime.now().strftime("%H:%M")
    start = _recording_config["schedule_start"]
    end = _recording_config["schedule_end"]
    return start <= now <= end


def _apply_config():
    """根据配置启停录像线程"""
    from modules.video_manager import video_manager

    enabled = _recording_config["enabled"]
    camera_ids = _recording_config["camera_ids"]

    # 停止不在列表里的录像
    for cid in list(_active_recorders.keys()):
        if not enabled or cid not in camera_ids:
            _active_recorders[cid].stop()
            del _active_recorders[cid]

    if not enabled:
        return

    # 启动新的录像线程
    for cid in camera_ids:
        if cid not in _active_recorders:
            stream = video_manager.streams.get(cid)
            if stream and stream.status != "offline":
                t = RecorderThread(cid, stream)
                t.start()
                _active_recorders[cid] = t


class RecorderThread(threading.Thread):
    def __init__(self, camera_id, stream):
        super().__init__(daemon=True)
        self.camera_id = camera_id
        self.stream = stream
        self.running = True

    def stop(self):
        self.running = False

    def run(self):
        os.makedirs(RECORDINGS_DIR, exist_ok=True)
        print(f"[Recorder] 开始持续录像: {self.stream.camera_name}")

        while self.running:
            # 检查时间段
            if not _in_schedule():
                time.sleep(30)
                continue

            # 检查摄像头是否在线
            if self.stream.status == "offline":
                time.sleep(5)
                continue

            # 开始一段录像
            self._record_segment()

        print(f"[Recorder] 停止持续录像: {self.stream.camera_name}")

    def _record_segment(self):
        segment_seconds = _recording_config["segment_minutes"] * 60
        start_time = datetime.now()
        filename = (
            f"{self.camera_id}_{self.stream.camera_name}_"
            f"{start_time.strftime('%Y%m%d_%H%M%S')}.mp4"
        )
        filepath = os.path.join(RECORDINGS_DIR, filename)
        raw_path = filepath.replace(".mp4", "_raw.mp4")

        writer = None
        frame_count = 0
        fps = 25

        deadline = time.time() + segment_seconds

        while self.running and time.time() < deadline and _in_schedule():
            frame = self.stream.get_current_frame()
            if frame is None:
                time.sleep(0.04)
                continue

            if writer is None:
                h, w = frame.shape[:2]
                writer = cv2.VideoWriter(
                    raw_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
                )

            writer.write(frame)
            frame_count += 1
            time.sleep(1.0 / fps)

        if writer:
            writer.release()

        if frame_count > 0 and os.path.exists(raw_path):
            # ffmpeg 转码为 H.264
            try:
                import subprocess
                result = subprocess.run(
                    [Config.FFMPEG_PATH, "-y", "-i", raw_path,
                     "-vcodec", "libx264", "-pix_fmt", "yuv420p",
                     "-movflags", "+faststart", filepath],
                    capture_output=True, timeout=120
                )
                if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
                    os.remove(raw_path)
                    print(f"[Recorder] 录像段保存: {filename}")
                else:
                    os.rename(raw_path, filepath)
                    print(f"[Recorder] ffmpeg转码失败，使用原始文件: {filename}")
            except Exception as e:
                print(f"[Recorder] 转码异常: {e}")
                if os.path.exists(raw_path):
                    os.rename(raw_path, filepath)
        elif os.path.exists(raw_path):
            os.remove(raw_path)


def get_recordings(camera_id=None, date=None):
    """获取录像文件列表"""
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    files = []
    for f in sorted(os.listdir(RECORDINGS_DIR), reverse=True):
        if not f.endswith(".mp4") or "_raw" in f:
            continue
        if camera_id and not f.startswith(camera_id):
            continue
        if date and date.replace("-", "") not in f:
            continue
        stat = os.stat(os.path.join(RECORDINGS_DIR, f))
        parts = f.replace(".mp4", "").split("_")
        try:
            ts = parts[-2] + "_" + parts[-1]
            dt = datetime.strptime(ts, "%Y%m%d_%H%M%S")
            timestamp = dt.isoformat()
            cam_name = "_".join(parts[1:-2])
        except Exception:
            timestamp = ""
            cam_name = f
        files.append({
            "filename": f,
            "camera_id": parts[0] if parts else "",
            "camera_name": cam_name,
            "timestamp": timestamp,
            "size_mb": round(stat.st_size / 1024 / 1024, 1),
        })
    return files


def _cleanup_expired():
    """清理超过保留天数的录像文件"""
    retention_days = _recording_config.get("retention_days", 7)
    if retention_days <= 0:
        return
    cutoff = datetime.now() - timedelta(days=retention_days)
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    count = 0
    for f in os.listdir(RECORDINGS_DIR):
        if not f.endswith(".mp4") or "_raw" in f:
            continue
        filepath = os.path.join(RECORDINGS_DIR, f)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
                count += 1
        except Exception:
            pass
    if count > 0:
        print(f"[Recorder] 自动清理过期录像 {count} 个（保留{retention_days}天）")


# 后台调度线程：每分钟检查一次时间段，自动启停；每天清理过期录像
def _schedule_watcher():
    from modules.video_manager import video_manager
    last_cleanup_day = -1
    while True:
        time.sleep(60)

        # 每天执行一次清理
        today = datetime.now().day
        if today != last_cleanup_day:
            _cleanup_expired()
            last_cleanup_day = today

        if not _recording_config["enabled"]:
            continue
        in_sched = _in_schedule()
        for cid in _recording_config["camera_ids"]:
            if in_sched and cid not in _active_recorders:
                stream = video_manager.streams.get(cid)
                if stream and stream.status != "offline":
                    t = RecorderThread(cid, stream)
                    t.start()
                    _active_recorders[cid] = t
            elif not in_sched and cid in _active_recorders:
                _active_recorders[cid].stop()
                del _active_recorders[cid]

threading.Thread(target=_schedule_watcher, daemon=True).start()
