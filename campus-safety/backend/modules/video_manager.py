"""视频流管理模块 - 管理多路摄像头/无人机视频流"""
import cv2
import os
import time
import threading
import uuid
import numpy as np
from collections import deque
from datetime import datetime
from config import Config

class VideoStream:
    """单路视频流"""
    
    def __init__(self, camera_config, source=None):
        self.camera_id = camera_config["id"]
        self.camera_name = camera_config["name"]
        self.location = camera_config["location"]
        self.is_drone = camera_config.get("is_drone", False)
        self.x = camera_config.get("x", 50)
        self.y = camera_config.get("y", 50)
        
        self.source = source          # 视频文件路径 或 RTSP URL
        self.cap = None
        self.running = False
        self.paused = False
        self.status = "offline"       # offline / online / paused / alert
        
        # 环形缓冲区，保存最近 N 秒的帧（用于触发前截取）
        fps_estimate = 25
        buffer_size = Config.PRE_EVENT_SECONDS * fps_estimate
        self.frame_buffer = deque(maxlen=buffer_size)
        
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self._thread = None
    
    def start(self, source):
        """启动视频流"""
        # 支持数字索引（本地摄像头），如 "0" -> 0
        try:
            source = int(source)
        except (ValueError, TypeError):
            pass
        self.source = source
        self.running = True
        self.status = "online"
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        self.running = False
        self.status = "offline"
        if self.cap:
            self.cap.release()
    
    def _read_loop(self):
        import gevent
        self.cap = cv2.VideoCapture(self.source)
        target_w = 640

        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or fps > 120:
            fps = 25
        frame_interval = 1.0 / fps

        next_frame_time = time.time()

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                next_frame_time = time.time()
                continue

            # 暂停时不更新帧，保持最后一帧画面
            if self.paused:
                gevent.sleep(0.1)
                continue

            h, w = frame.shape[:2]
            target_h = int(h * target_w / w)
            frame = cv2.resize(frame, (target_w, target_h))

            with self.frame_lock:
                self.current_frame = frame.copy()
                self.frame_buffer.append((time.time(), frame.copy()))

            next_frame_time += frame_interval
            sleep_time = next_frame_time - time.time()
            if sleep_time > 0:
                gevent.sleep(sleep_time)
            else:
                # 处理太慢时重置，避免一直追帧
                next_frame_time = time.time()
                gevent.sleep(0)

        self.cap.release()
    
    def get_current_frame(self):
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def save_clip_with_post(self, behavior, post_seconds=5):
        """
        保存触发前N秒 + 触发后N秒的完整视频片段
        触发后的帧通过继续监听 frame_buffer 获取
        返回: filepath
        """
        import gevent
        os.makedirs(Config.ALERT_CLIPS_DIR, exist_ok=True)

        # 先取触发前的帧
        with self.frame_lock:
            pre_frames = [(ts, f.copy()) for ts, f in self.frame_buffer]

        # 继续收集触发后的帧
        fps = 25
        if self.cap:
            _fps = self.cap.get(cv2.CAP_PROP_FPS)
            if 0 < _fps <= 120:
                fps = _fps

        post_count = int(post_seconds * fps)
        post_frames = []
        deadline = time.time() + post_seconds + 1.0

        while len(post_frames) < post_count and time.time() < deadline:
            with self.frame_lock:
                buf = list(self.frame_buffer)
            # 只取触发后新增的帧
            new_frames = [(ts, f) for ts, f in buf if not pre_frames or ts > pre_frames[-1][0]]
            post_frames = new_frames
            time.sleep(0.1)

        all_frames = pre_frames + [(ts, f.copy()) for ts, f in post_frames]
        if not all_frames:
            return None

        filename = (
            f"{self.camera_id}_{behavior}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
            f"{uuid.uuid4().hex[:6]}.mp4"
        )
        filepath = os.path.join(Config.ALERT_CLIPS_DIR, filename)

        h, w = all_frames[0][1].shape[:2]

        # 先用 mp4v 写原始文件
        raw_path = filepath.replace(".mp4", "_raw.mp4")
        writer = cv2.VideoWriter(
            raw_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h)
        )
        for _, f in all_frames:
            writer.write(f)
        writer.release()

        # 用 ffmpeg 转成 H.264，浏览器兼容
        import subprocess
        ffmpeg_candidates = [
            Config.FFMPEG_PATH,
            "ffmpeg",
        ]
        converted = False
        for ffmpeg_bin in ffmpeg_candidates:
            try:
                result = subprocess.run(
                    [ffmpeg_bin, "-y", "-i", raw_path,
                     "-vcodec", "libx264", "-pix_fmt", "yuv420p",
                     "-movflags", "+faststart", filepath],
                    capture_output=True, timeout=60
                )
                if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
                    os.remove(raw_path)
                    print(f"[VideoManager] ffmpeg 转码成功: {os.path.basename(filepath)}")
                    converted = True
                    break
                else:
                    print(f"[VideoManager] ffmpeg stderr: {result.stderr.decode('utf-8', errors='ignore')[-300:]}")
            except Exception as e:
                print(f"[VideoManager] ffmpeg ({ffmpeg_bin}) 失败: {e}")
                continue

        if not converted:
            # 降级：直接用 mp4v
            if os.path.exists(raw_path):
                os.rename(raw_path, filepath)
            print(f"[VideoManager] 降级使用 mp4v: {os.path.basename(filepath)}")

        return filepath

    def extract_keyframes(self, clip_path, fps_sample=1.0, max_frames=16):
        """
        按时间密度从视频片段抽取帧，每秒抽 fps_sample 帧
        max_frames: 最多抽取帧数上限，避免 token 过多
        返回: list of numpy frames
        """
        cap = cv2.VideoCapture(clip_path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 25
        if total <= 0:
            cap.release()
            return []

        # 计算抽帧间隔
        interval = max(1, int(fps / fps_sample))
        indices = list(range(0, total, interval))

        # 超出上限时均匀降采样
        if len(indices) > max_frames:
            step = len(indices) / max_frames
            indices = [indices[int(i * step)] for i in range(max_frames)]

        frames = []
        for idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if ret:
                frames.append(frame)
        cap.release()
        return frames
    
    def to_dict(self):
        return {
            "id": self.camera_id,
            "name": self.camera_name,
            "location": self.location,
            "is_drone": self.is_drone,
            "status": self.status,
            "x": self.x,
            "y": self.y,
        }

class VideoManager:
    """多路视频流管理器"""
    
    def __init__(self):
        self.streams = {}  # camera_id -> VideoStream
        self._init_streams()
    
    def _init_streams(self):
        for cam in Config.CAMERAS:
            stream = VideoStream(cam)
            self.streams[cam["id"]] = stream
    
    def start_stream(self, camera_id, source):
        """启动指定摄像头的视频流"""
        if camera_id in self.streams:
            self.streams[camera_id].start(source)
            return True
        return False
    
    def stop_stream(self, camera_id):
        if camera_id in self.streams:
            self.streams[camera_id].stop()
    
    def get_frame(self, camera_id):
        stream = self.streams.get(camera_id)
        if stream:
            return stream.get_current_frame()
        return None
    
    def save_clip(self, camera_id, behavior):
        stream = self.streams.get(camera_id)
        if stream:
            return stream.save_clip_with_post(behavior, post_seconds=5)
        return None

    def extract_keyframes(self, camera_id, clip_path, fps_sample=1.0, max_frames=16):
        stream = self.streams.get(camera_id)
        if stream:
            return stream.extract_keyframes(clip_path, fps_sample, max_frames)
        return []
    
    def set_status(self, camera_id, status):
        if camera_id in self.streams:
            self.streams[camera_id].status = status
    
    def get_all_status(self):
        return [s.to_dict() for s in self.streams.values()]
    
    def get_active_camera_ids(self):
        return [cid for cid, s in self.streams.items() if s.status != "offline"]


# 全局单例
video_manager = VideoManager()
