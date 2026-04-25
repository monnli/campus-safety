"""检测调度器 - 协调 YOLO -> Qwen-VL -> LLM -> 广播/通知 的完整流程"""
import threading
import time
from config import Config
from modules.detector import detect_frame, draw_detections
from modules.analyzer import analyze_frames
from modules.reporter import generate_alert_report
from modules.broadcaster import broadcast_alert
from modules.notifier import send_sms_alert, trigger_alarm
from modules.event_store import add_event
from modules.video_manager import video_manager

# 冷却时间：同一摄像头同一行为，N秒内不重复触发
COOLDOWN_SECONDS = 30
_last_trigger = {}  # (camera_id, behavior) -> timestamp
_lock = threading.Lock()

# 事件回调，用于 SocketIO 推送
_event_callbacks = []

def register_event_callback(fn):
    _event_callbacks.append(fn)

def _notify_callbacks(event_type, data):
    for fn in _event_callbacks:
        try:
            fn(event_type, data)
        except Exception as e:
            print(f"[Scheduler] 回调异常: {e}")

def _is_cooldown(camera_id, behavior):
    import modules.detection_config as det_cfg
    cooldown = det_cfg.get("cooldown", COOLDOWN_SECONDS)
    key = (camera_id, behavior)
    with _lock:
        last = _last_trigger.get(key, 0)
        if time.time() - last < cooldown:
            return True
        _last_trigger[key] = time.time()
    return False

def _handle_detection(camera_id, camera_name, frame, detection):
    """处理单次检测触发的完整流程"""
    behavior = detection["class_name"]
    confidence = detection["confidence"]

    print(f"[Scheduler] {camera_name} 检测到 {behavior} ({confidence:.2f})")

    # 1. 保存视频片段（前5秒 + 后5秒），在独立线程中完成后续录制
    clip_path = video_manager.save_clip(camera_id, behavior)

    # 2. 从片段抽取关键帧做 Qwen-VL 多帧分析
    keyframes = []
    if clip_path:
        keyframes = video_manager.extract_keyframes(camera_id, clip_path, fps_sample=1.0, max_frames=16)

    # 没有片段时降级用当前帧
    if not keyframes:
        keyframes = [frame]

    vl_result = analyze_frames(keyframes, behavior)
    if not vl_result["confirmed"]:
        print(f"[Scheduler] Qwen-VL 未确认，忽略此次检测")
        return

    # 3. Qwen LLM 生成报告和广播文字
    report_data = generate_alert_report(camera_name, behavior, vl_result["description"])

    # 4. 存储事件
    event = add_event(
        camera_id=camera_id,
        camera_name=camera_name,
        behavior=behavior,
        confidence=confidence,
        clip_path=clip_path,
        vl_result=vl_result["description"],
        report=report_data["report"],
    )

    # 5. 设置摄像头状态为告警
    video_manager.set_status(camera_id, "alert")

    # 6. 广播驱离（TTS）
    audio_path = broadcast_alert(report_data["broadcast_text"])

    # 7. 短信通知 + 监控室警报
    notifications = send_sms_alert(event)
    alarm = trigger_alarm(event)

    # 8. 推送给前端
    _notify_callbacks("new_event", {
        "event": event,
        "alarm": alarm,
        "broadcast_text": report_data["broadcast_text"],
        "audio_path": audio_path,
        "notifications": notifications,
    })

    print(f"[Scheduler] 事件处理完成: {event['id']}")

def _detection_loop(camera_id, camera_name):
    """单路摄像头的检测循环"""
    frame_count = 0
    while True:
        stream = video_manager.streams.get(camera_id)
        if not stream or stream.status == "offline":
            time.sleep(1)
            continue
        
        frame = stream.get_current_frame()
        if frame is None:
            time.sleep(0.1)
            continue
        
        frame_count += 1
        # 每隔 FRAME_SKIP 帧检测一次
        import modules.detection_config as det_cfg
        frame_skip = det_cfg.get("frameSkip", Config.FRAME_SKIP)
        if frame_count % frame_skip != 0:
            time.sleep(0.04)
            continue
        
        detections = detect_frame(frame)
        
        if detections:
            # 取置信度最高的检测结果
            best = max(detections, key=lambda d: d["confidence"])
            
            if not _is_cooldown(camera_id, best["class_name"]):
                # 异步处理，不阻塞检测循环
                t = threading.Thread(
                    target=_handle_detection,
                    args=(camera_id, camera_name, frame.copy(), best),
                    daemon=True
                )
                t.start()
        else:
            # 无检测时恢复正常状态
            if stream.status == "alert":
                video_manager.set_status(camera_id, "online")
                _notify_callbacks("status_update", {"camera_id": camera_id, "status": "online"})
        
        time.sleep(0.04)

def start_detection_for_camera(camera_id, camera_name):
    """为指定摄像头启动检测线程"""
    t = threading.Thread(
        target=_detection_loop,
        args=(camera_id, camera_name),
        daemon=True
    )
    t.start()
    print(f"[Scheduler] 启动检测线程: {camera_name}")
