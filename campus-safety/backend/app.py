"""Flask 主应用"""
import os
from dotenv import load_dotenv
load_dotenv()
import cv2
import base64
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from config import Config
from modules.video_manager import video_manager
from modules.detection_scheduler import start_detection_for_camera, register_event_callback
from modules.event_store import get_events, get_event_by_id, update_event_status, get_stats, natural_language_query
from modules.notifier import get_notification_log
from modules.reporter import answer_query, generate_daily_report
from modules.detector import draw_detections, detect_frame
from modules.auth import login, require_auth, require_role
from modules.risk_analyzer import analyze_risk
from modules.session_store import save_camera_source, remove_camera_source, get_all_camera_sources
import modules.detection_config as det_cfg

app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")

os.makedirs(Config.ALERT_CLIPS_DIR, exist_ok=True)

# ── SocketIO 事件回调 ──────────────────────────────────────────
def on_event(event_type, data):
    socketio.emit(event_type, data)

register_event_callback(on_event)

# ── 视频帧推送线程 ─────────────────────────────────────────────
import threading
import time
from flask import Response

def push_frames():
    """通过 WebSocket 推送摄像头状态（不推视频帧，改用 MJPEG 流）"""
    while True:
        socketio.emit("cameras", video_manager.get_all_status())
        time.sleep(2)

threading.Thread(target=push_frames, daemon=True).start()

# ── 启动时自动恢复上次的摄像头接入状态 ───────────────────────
def _restore_cameras():
    time.sleep(2)  # 等待服务完全启动
    saved = get_all_camera_sources()
    if not saved:
        return
    print(f"[App] 恢复 {len(saved)} 路摄像头...")
    for camera_id, source in saved.items():
        stream = video_manager.streams.get(camera_id)
        if stream and stream.status == "offline":
            # 检查视频文件是否还存在（跳过已删除的文件）
            try:
                src = int(source)  # 摄像头索引
            except ValueError:
                src = source
                if isinstance(src, str) and not os.path.exists(src):
                    print(f"[App] 视频文件不存在，跳过恢复: {src}")
                    remove_camera_source(camera_id)
                    continue
            video_manager.start_stream(camera_id, src)
            start_detection_for_camera(camera_id, stream.camera_name)
            print(f"[App] 已恢复: {stream.camera_name} <- {source}")

threading.Thread(target=_restore_cameras, daemon=True).start()

# 检测结果缓存：camera_id -> list of detections
_detection_cache = {}
_detection_cache_lock = {}

def _get_cache_lock(camera_id):
    if camera_id not in _detection_cache_lock:
        import threading
        _detection_cache_lock[camera_id] = threading.Lock()
    return _detection_cache_lock[camera_id]

def _detection_worker(camera_id):
    """独立检测线程，持续更新检测结果缓存"""
    import gevent
    from modules.detector import detect_frame
    frame_count = 0
    while True:
        stream = video_manager.streams.get(camera_id)
        if stream is None or stream.status == "offline":
            gevent.sleep(0.5)
            continue
        frame = stream.get_current_frame()
        if frame is None:
            gevent.sleep(0.1)
            continue
        frame_count += 1
        if frame_count % Config.FRAME_SKIP == 0:
            try:
                detections = detect_frame(frame)
                with _get_cache_lock(camera_id):
                    _detection_cache[camera_id] = detections
            except Exception:
                pass
        gevent.sleep(0.04)

_detection_workers_started = set()

def ensure_detection_worker(camera_id):
    if camera_id not in _detection_workers_started:
        import threading
        t = threading.Thread(target=_detection_worker, args=(camera_id,), daemon=True)
        t.start()
        _detection_workers_started.add(camera_id)

def generate_mjpeg(camera_id):
    """生成单路摄像头的 MJPEG 流，检测框异步叠加"""
    import gevent
    from modules.detector import draw_detections
    ensure_detection_worker(camera_id)
    while True:
        stream = video_manager.streams.get(camera_id)
        if stream is None or stream.status == "offline":
            gevent.sleep(0.1)
            continue
        frame = stream.get_current_frame()
        if frame is None:
            gevent.sleep(0.05)
            continue

        # 取缓存的检测结果叠加，不阻塞推流
        with _get_cache_lock(camera_id):
            detections = _detection_cache.get(camera_id, [])
        if detections:
            frame = draw_detections(frame.copy(), detections)

        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")

        cap = stream.cap
        fps = cap.get(cv2.CAP_PROP_FPS) if cap else 25
        if fps <= 0 or fps > 120:
            fps = 25
        gevent.sleep(1.0 / fps)

# ── REST API ───────────────────────────────────────────────────

@app.route("/api/cameras", methods=["GET"])
def get_cameras():
    """获取所有摄像头状态"""
    return jsonify(video_manager.get_all_status())

@app.route("/api/stream/<camera_id>")
def video_stream(camera_id):
    """MJPEG 视频流"""
    return Response(
        generate_mjpeg(camera_id),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/api/cameras/start", methods=["POST"])
def start_camera():
    """启动摄像头视频流"""
    data = request.json
    camera_id = data.get("camera_id")
    source = data.get("source")  # 视频文件路径、RTSP URL 或 "0"/"1" 摄像头索引
    
    if not camera_id or source is None:
        return jsonify({"error": "camera_id 和 source 必填"}), 400
    
    stream = video_manager.streams.get(camera_id)
    if not stream:
        return jsonify({"error": "摄像头不存在"}), 404
    
    video_manager.start_stream(camera_id, source)
    start_detection_for_camera(camera_id, stream.camera_name)
    save_camera_source(camera_id, source)
    return jsonify({"success": True, "camera_id": camera_id})

@app.route("/api/cameras/add", methods=["POST"])
def add_camera():
    """动态添加新摄像头"""
    data = request.json
    name = data.get("name", "").strip()
    location = data.get("location", "").strip()
    if not name:
        return jsonify({"error": "摄像头名称不能为空"}), 400

    cam_config = {
        "id": f"cam_{len(video_manager.streams) + 1:03d}_{name}",
        "name": name,
        "location": location or name,
        "x": 50, "y": 50,
        "is_drone": False,
    }
    from modules.video_manager import VideoStream
    stream = VideoStream(cam_config)
    video_manager.streams[cam_config["id"]] = stream
    return jsonify({"success": True, "camera": stream.to_dict()})

@app.route("/api/cameras/<camera_id>", methods=["DELETE"])
def delete_camera(camera_id):
    """删除摄像头"""
    if camera_id not in video_manager.streams:
        return jsonify({"error": "摄像头不存在"}), 404
    video_manager.stop_stream(camera_id)
    del video_manager.streams[camera_id]
    remove_camera_source(camera_id)
    return jsonify({"success": True})

@app.route("/api/cameras/stop", methods=["POST"])
def stop_camera():
    """停止视频流（保留摄像头，变为离线状态）"""
    camera_id = request.json.get("camera_id")
    video_manager.stop_stream(camera_id)
    remove_camera_source(camera_id)
    return jsonify({"success": True})

@app.route("/api/cameras/pause", methods=["POST"])
def pause_camera():
    """暂停视频流"""
    camera_id = request.json.get("camera_id")
    stream = video_manager.streams.get(camera_id)
    if stream:
        stream.paused = True
        stream.status = "paused"
    return jsonify({"success": True})

@app.route("/api/cameras/resume", methods=["POST"])
def resume_camera():
    """恢复视频流"""
    camera_id = request.json.get("camera_id")
    stream = video_manager.streams.get(camera_id)
    if stream:
        stream.paused = False
        stream.status = "online"
    return jsonify({"success": True})



@app.route("/api/cameras/upload", methods=["POST"])
def upload_video():
    """上传视频文件并启动分析"""
    camera_id = request.form.get("camera_id")
    file = request.files.get("video")
    
    if not camera_id or not file:
        return jsonify({"error": "camera_id 和 video 必填"}), 400
    
    upload_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, file.filename)
    file.save(filepath)
    
    stream = video_manager.streams.get(camera_id)
    if not stream:
        return jsonify({"error": "摄像头不存在"}), 404
    
    video_manager.start_stream(camera_id, filepath)
    start_detection_for_camera(camera_id, stream.camera_name)
    save_camera_source(camera_id, filepath)
    return jsonify({"success": True, "filepath": filepath})

@app.route("/api/events", methods=["GET"])
def list_events():
    behavior = request.args.get("behavior")
    camera_id = request.args.get("camera_id")
    limit = int(request.args.get("limit", 50))
    date_start = request.args.get("date_start")
    date_end = request.args.get("date_end")
    events = get_events(limit=limit, behavior=behavior, camera_id=camera_id,
                        date_start=date_start, date_end=date_end)
    return jsonify(events)

@app.route("/api/events/<event_id>", methods=["GET"])
def get_event(event_id):
    event = get_event_by_id(event_id)
    if not event:
        return jsonify({"error": "事件不存在"}), 404
    return jsonify(event)

@app.route("/api/events/<event_id>/handle", methods=["POST"])
def handle_event(event_id):
    update_event_status(event_id, "handled")
    return jsonify({"success": True})

@app.route("/api/events/<event_id>/false-alarm", methods=["POST"])
def false_alarm(event_id):
    update_event_status(event_id, "false_alarm")
    return jsonify({"success": True})

@app.route("/api/stats", methods=["GET"])
def stats():
    date_start = request.args.get("date_start")
    date_end = request.args.get("date_end")
    return jsonify(get_stats(date_start=date_start, date_end=date_end))

@app.route("/api/notifications", methods=["GET"])
def notifications():
    return jsonify(get_notification_log())

@app.route("/api/query", methods=["POST"])
def query():
    """自然语言查询"""
    q = request.json.get("query", "")
    if not q:
        return jsonify({"error": "query 不能为空"}), 400
    
    matched_events = natural_language_query(q)
    context = "\n".join([
        f"[{e['timestamp'][11:16]}] {e['camera_name']} - {e['behavior']} (置信度{e['confidence']}): {e['vl_result'][:100]}"
        for e in matched_events
    ]) or "暂无相关事件记录"
    
    answer = answer_query(q, context)
    return jsonify({"answer": answer, "related_events": matched_events})

@app.route("/api/daily-report", methods=["GET"])
def daily_report():
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    events = get_events(limit=200)
    today_events = [e for e in events if e["timestamp"].startswith(today)]
    report = generate_daily_report(today_events)
    return jsonify({"report": report, "date": today, "total": len(today_events)})

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}
    result, error = login(data.get("username", ""), data.get("password", ""))
    if error:
        return jsonify({"error": error}), 401
    return jsonify(result)

@app.route("/api/detection/config", methods=["GET"])
def get_detection_config():
    return jsonify(det_cfg.load())

@app.route("/api/detection/config", methods=["POST"])
@require_auth
def set_detection_config():
    data = request.json or {}
    det_cfg.save(data)
    return jsonify({"success": True})
    result, error = login(data.get("username", ""), data.get("password", ""))
    if error:
        return jsonify({"error": error}), 401
    return jsonify(result)

@app.route("/api/me", methods=["GET"])
@require_auth
def api_me():
    return jsonify(request.user)

# ── 持续录像 ───────────────────────────────────────────────────
from modules.continuous_recorder import get_config, update_config, get_recordings, RECORDINGS_DIR

@app.route("/api/recording/config", methods=["GET"])
@require_auth
def get_recording_config():
    return jsonify(get_config())

# ── 广播配置 ───────────────────────────────────────────────────
import json as _json

_BROADCAST_CONFIG_FILE = os.path.join(os.path.dirname(__file__), "data", "broadcast_config.json")
_DEFAULT_BROADCAST_CONFIG = {
    "repeat_times": 3,       # 广播重复次数
    "custom_texts": {        # 各行为类型的自定义广播内容（空则由AI生成）
        "fighting": "",
        "falling": "",
        "intrusion": "",
    }
}

def _load_broadcast_config():
    os.makedirs(os.path.dirname(_BROADCAST_CONFIG_FILE), exist_ok=True)
    if os.path.exists(_BROADCAST_CONFIG_FILE):
        try:
            with open(_BROADCAST_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = _DEFAULT_BROADCAST_CONFIG.copy()
                cfg.update(_json.load(f))
                return cfg
        except Exception:
            pass
    return _DEFAULT_BROADCAST_CONFIG.copy()

def _save_broadcast_config(cfg):
    os.makedirs(os.path.dirname(_BROADCAST_CONFIG_FILE), exist_ok=True)
    with open(_BROADCAST_CONFIG_FILE, "w", encoding="utf-8") as f:
        _json.dump(cfg, f, ensure_ascii=False, indent=2)

@app.route("/api/broadcast/config", methods=["GET"])
@require_auth
def get_broadcast_config():
    return jsonify(_load_broadcast_config())

@app.route("/api/broadcast/config", methods=["POST"])
@require_role("principal", "manager")
def set_broadcast_config():
    data = request.json or {}
    cfg = _load_broadcast_config()
    cfg.update(data)
    _save_broadcast_config(cfg)
    return jsonify({"success": True})

@app.route("/api/recording/config", methods=["POST"])
@require_role("principal", "manager")
def set_recording_config():
    data = request.json or {}
    update_config(data)
    return jsonify({"success": True})

@app.route("/api/recording/list", methods=["GET"])
@require_auth
def list_recordings():
    camera_id = request.args.get("camera_id")
    date = request.args.get("date")
    return jsonify(get_recordings(camera_id=camera_id, date=date))

@app.route("/static/recordings/<path:filename>")
def serve_recording(filename):
    import os
    filepath = os.path.join(RECORDINGS_DIR, filename)
    if not os.path.exists(filepath):
        return jsonify({"error": "文件不存在"}), 404
    file_size = os.path.getsize(filepath)
    range_header = request.headers.get("Range")
    with open(filepath, "rb") as f:
        if range_header:
            byte_range = range_header.replace("bytes=", "").split("-")
            start = int(byte_range[0])
            end = int(byte_range[1]) if byte_range[1] else file_size - 1
            length = end - start + 1
            f.seek(start)
            data = f.read(length)
            from flask import make_response
            response = make_response(data, 206)
            response.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        else:
            data = f.read()
            from flask import make_response
            response = make_response(data, 200)
    response.headers["Content-Type"] = "video/mp4"
    response.headers["Content-Length"] = str(len(data))
    response.headers["Accept-Ranges"] = "bytes"
    return response

@app.route("/api/risk-analysis", methods=["GET"])
@require_auth
def risk_analysis():
    date_start = request.args.get("date_start")
    date_end = request.args.get("date_end")
    events = get_events(limit=500, date_start=date_start, date_end=date_end)
    result = analyze_risk(events)
    return jsonify(result)

@app.route("/api/trend", methods=["GET"])
@require_auth
def trend():
    """近N天每日事件趋势"""
    from datetime import datetime, timedelta
    days = int(request.args.get("days", 7))
    result = []
    for i in range(days - 1, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        events = get_events(limit=500, date_start=d, date_end=d)
        behavior_count = {}
        for e in events:
            b = e["behavior"]
            behavior_count[b] = behavior_count.get(b, 0) + 1
        result.append({"date": d, "total": len(events), "by_behavior": behavior_count})
    return jsonify(result)

@app.route("/api/heatmap", methods=["GET"])
@require_auth
def heatmap():
    """各摄像头事件热力数据"""
    from config import Config as C
    events = get_events(limit=1000)
    cam_count = {}
    for e in events:
        cam_count[e["camera_name"]] = cam_count.get(e["camera_name"], 0) + 1
    # 返回摄像头位置+事件数
    result = []
    for cam in C.CAMERAS:
        result.append({
            "id": cam["id"],
            "name": cam["name"],
            "x": cam["x"],
            "y": cam["y"],
            "count": cam_count.get(cam["name"], 0),
        })
    return jsonify(result)

# 巡逻任务存储（内存，demo够用）
_patrol_tasks = []

@app.route("/api/patrol", methods=["GET"])
@require_auth
def get_patrol():
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    return jsonify([t for t in _patrol_tasks if t["date"] == today])

@app.route("/api/patrol/generate", methods=["POST"])
@require_auth
def generate_patrol():
    """根据风险分析自动生成今日巡逻任务"""
    from datetime import datetime
    from modules.risk_analyzer import analyze_risk
    today = datetime.now().strftime("%Y-%m-%d")
    events = get_events(limit=500, date_start=today, date_end=today)
    risk = analyze_risk(events)

    tasks = []
    schedules = [
        {"time": "08:00", "label": "早晨"},
        {"time": "10:10", "label": "上午课间"},
        {"time": "12:00", "label": "午休"},
        {"time": "14:10", "label": "下午课间"},
        {"time": "16:30", "label": "放学"},
    ]
    areas = [a["area"] for a in risk.get("high_risk_areas", [])] or ["操场", "校门口", "走廊"]

    for i, s in enumerate(schedules):
        area = areas[i % len(areas)]
        tasks.append({
            "id": f"patrol_{today}_{i}",
            "date": today,
            "time": s["time"],
            "label": s["label"],
            "area": area,
            "status": "pending",  # pending / done
            "guard": "王保安",
        })

    # 替换今日任务
    global _patrol_tasks
    _patrol_tasks = [t for t in _patrol_tasks if t["date"] != today] + tasks
    return jsonify(tasks)

@app.route("/api/patrol/<task_id>/done", methods=["POST"])
@require_auth
def complete_patrol(task_id):
    for t in _patrol_tasks:
        if t["id"] == task_id:
            t["status"] = "done"
            return jsonify({"success": True})
    return jsonify({"error": "任务不存在"}), 404

@app.route("/static/alerts/<path:filename>")
def serve_alert_file(filename):
    from flask import make_response, abort
    import os

    filepath = os.path.join(Config.ALERT_CLIPS_DIR, filename)
    if not os.path.exists(filepath):
        abort(404)

    file_size = os.path.getsize(filepath)
    range_header = request.headers.get("Range")

    with open(filepath, "rb") as f:
        if range_header:
            # 解析 Range: bytes=start-end
            byte_range = range_header.replace("bytes=", "").split("-")
            start = int(byte_range[0])
            end = int(byte_range[1]) if byte_range[1] else file_size - 1
            length = end - start + 1
            f.seek(start)
            data = f.read(length)
            response = make_response(data, 206)
            response.headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        else:
            data = f.read()
            response = make_response(data, 200)

    response.headers["Content-Type"] = "video/mp4"
    response.headers["Content-Length"] = str(len(data))
    response.headers["Accept-Ranges"] = "bytes"
    response.headers["Cache-Control"] = "no-cache"
    return response

# ── 无人机规划 ────────────────────────────────────────────────
from modules.drone_planner import load_plan, save_plan, generate_waypoints, export_kmz_waypoints, save_patrol_history, load_patrol_history

@app.route("/api/drone/plan", methods=["GET"])
def get_drone_plan():
    return jsonify(load_plan())

@app.route("/api/drone/plan", methods=["POST"])
def save_drone_plan():
    plan = request.json or {}
    save_plan(plan)
    return jsonify({"success": True})

@app.route("/api/drone/generate-waypoints", methods=["POST"])
def api_generate_waypoints():
    plan = request.json or load_plan()
    waypoints, flight_info = generate_waypoints(plan)
    plan["waypoints"] = waypoints
    plan["flight_info"] = flight_info
    save_plan(plan)
    save_patrol_history(waypoints, flight_info)
    return jsonify({"waypoints": waypoints, "flight_info": flight_info})

@app.route("/api/drone/history", methods=["GET"])
def drone_history():
    return jsonify(load_patrol_history())

@app.route("/api/amap/search", methods=["GET"])
def amap_search():
    """高德地图搜索代理，解决前端 CORS 问题"""
    keywords = request.args.get("keywords", "")
    if not keywords:
        return jsonify({"status": "0", "pois": []})
    import requests as req
    try:
        resp = req.get(
            "https://restapi.amap.com/v3/place/text",
            params={"keywords": keywords, "key": "9850174b823993ae7aff55287b9843cd", "output": "json", "offset": 1},
            timeout=5,
            proxies={"http": None, "https": None}  # 绕过系统代理
        )
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"status": "0", "error": str(e)})

@app.route("/api/drone/export-kml", methods=["GET"])
def export_kml():
    plan = load_plan()
    waypoints = plan.get("waypoints", [])
    if not waypoints:
        waypoints = generate_waypoints(plan)
    if not waypoints:
        return jsonify({"error": "暂无航点，请先生成航点"}), 400
    kml = export_kmz_waypoints(waypoints)
    from flask import Response
    return Response(kml, mimetype="application/vnd.google-earth.kml+xml",
                    headers={"Content-Disposition": "attachment; filename=patrol_route.kml"})

# ── SocketIO 事件 ──────────────────────────────────────────────

@socketio.on("connect")
def on_connect():
    emit("cameras", video_manager.get_all_status())

@socketio.on("disconnect")
def on_disconnect():
    pass

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
