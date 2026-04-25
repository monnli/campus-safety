"""无人机巡逻路径规划模块"""
import json
import os
import math
import threading
from datetime import datetime

PLAN_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "drone_plan.json")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "drone_history.json")
_lock = threading.Lock()

DEFAULT_PLAN = {
    "school": {"name": "", "center": None, "buildings": []},
    "home_routes": [],
    "waypoints": [],
    "flight_info": {},
    "settings": {
        "patrol_radius": 1000,
        "base_altitude": 30,
        "building_clearance": 10,
        "speed": 5,
        "waypoint_interval": 100,  # 航点间距（米）
    }
}


def load_plan():
    os.makedirs(os.path.dirname(PLAN_FILE), exist_ok=True)
    if os.path.exists(PLAN_FILE):
        try:
            with open(PLAN_FILE, "r", encoding="utf-8") as f:
                plan = json.load(f)
                for k, v in DEFAULT_PLAN.items():
                    if k not in plan:
                        plan[k] = v
                if "waypoint_interval" not in plan.get("settings", {}):
                    plan["settings"]["waypoint_interval"] = 100
                return plan
        except Exception:
            pass
    return dict(DEFAULT_PLAN)


def save_plan(plan):
    os.makedirs(os.path.dirname(PLAN_FILE), exist_ok=True)
    with open(PLAN_FILE, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)


def _haversine(lng1, lat1, lng2, lat2):
    """计算两点间距离（米）"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def _interpolate_path(path, interval_m):
    """
    沿路径按固定距离插值，生成均匀分布的点
    interval_m: 插值间距（米）
    """
    if len(path) < 2:
        return path

    result = [path[0]]
    accumulated = 0.0

    for i in range(len(path) - 1):
        p1, p2 = path[i], path[i+1]
        seg_dist = _haversine(p1[0], p1[1], p2[0], p2[1])
        if seg_dist == 0:
            continue

        # 在这段路径上插值
        steps = max(1, int(seg_dist / interval_m))
        for s in range(1, steps + 1):
            t = s / steps
            lng = p1[0] + (p2[0] - p1[0]) * t
            lat = p1[1] + (p2[1] - p1[1]) * t
            result.append([lng, lat])

    # 确保终点在列表中
    if result[-1] != path[-1]:
        result.append(path[-1])

    return result


def _get_altitude_for_point(lng, lat, buildings, base_alt, clearance):
    """根据附近建筑物计算该点的飞行高度"""
    max_h = 0
    for b in buildings:
        if b.get("polygon") and b["polygon"]:
            for p in b["polygon"]:
                dist = _haversine(lng, lat, p[0], p[1])
                if dist < 150:  # 150米范围内的建筑物
                    h = b.get("height", 0)
                    if h > max_h:
                        max_h = h
    return max(base_alt, max_h + clearance)


def _calc_total_distance(waypoints):
    """计算航点总距离（米）"""
    total = 0
    for i in range(len(waypoints) - 1):
        total += _haversine(
            waypoints[i]["lng"], waypoints[i]["lat"],
            waypoints[i+1]["lng"], waypoints[i+1]["lat"]
        )
    return total


def generate_waypoints(plan):
    """
    生成巡逻航点：
    1. 学校起飞点
    2. 沿每条回家路线按固定间距插值生成均匀航点，高度自适应建筑物
    3. 返航降落
    返回: (waypoints, flight_info)
    """
    settings = plan.get("settings", DEFAULT_PLAN["settings"])
    base_alt = settings.get("base_altitude", 30)
    clearance = settings.get("building_clearance", 10)
    speed = settings.get("speed", 5)
    interval = settings.get("waypoint_interval", 100)
    buildings = plan.get("school", {}).get("buildings", [])
    home_routes = plan.get("home_routes", [])

    waypoints = []
    center = plan.get("school", {}).get("center")

    # 起飞点
    if center:
        waypoints.append({
            "id": 0,
            "lng": center[0],
            "lat": center[1],
            "altitude": base_alt,
            "action": "takeoff",
            "label": "起飞点（学校）",
            "route": "学校"
        })

    wp_id = 1
    for route in home_routes:
        path = route.get("path", [])
        route_name = route.get("name", "路线")
        if len(path) < 2:
            continue

        # 按固定间距插值
        interpolated = _interpolate_path(path, interval)

        for i, point in enumerate(interpolated):
            lng, lat = point[0], point[1]
            altitude = _get_altitude_for_point(lng, lat, buildings, base_alt, clearance)
            is_last = (i == len(interpolated) - 1)

            waypoints.append({
                "id": wp_id,
                "lng": lng,
                "lat": lat,
                "altitude": altitude,
                "action": "hover" if is_last else "fly",
                "label": f"{route_name} 航点{i+1}",
                "route": route_name,
            })
            wp_id += 1

    # 返航
    if center and len(waypoints) > 1:
        waypoints.append({
            "id": wp_id,
            "lng": center[0],
            "lat": center[1],
            "altitude": base_alt,
            "action": "land",
            "label": "返航降落",
            "route": "返航"
        })

    # 计算飞行信息
    total_dist = _calc_total_distance(waypoints)
    flight_time_min = round(total_dist / speed / 60, 1) if speed > 0 else 0

    flight_info = {
        "total_waypoints": len(waypoints),
        "total_distance_m": round(total_dist),
        "total_distance_km": round(total_dist / 1000, 2),
        "estimated_time_min": flight_time_min,
        "routes_count": len(home_routes),
        "speed_ms": speed,
        "waypoint_interval_m": interval,
    }

    return waypoints, flight_info


def save_patrol_history(waypoints, flight_info):
    """保存巡逻历史记录"""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass

    record = {
        "time": datetime.now().isoformat(),
        "waypoints_count": len(waypoints),
        "flight_info": flight_info,
    }
    history.insert(0, record)
    history = history[:50]  # 保留最近50条

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def load_patrol_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _point_near_polygon(lng, lat, polygon, radius_m=100):
    if not polygon:
        return False
    for p in polygon:
        if _haversine(lng, lat, p[0], p[1]) < radius_m:
            return True
    return False


def export_kmz_waypoints(waypoints):
    """生成大疆无人机 KML 格式航线内容"""
    kml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>',
        '<name>校园安全巡逻航线</name>',
    ]

    for wp in waypoints:
        kml_lines.append(f'''  <Placemark>
    <name>{wp["label"]}</name>
    <description>高度:{wp["altitude"]}m 动作:{wp["action"]}</description>
    <Point>
      <altitudeMode>relativeToGround</altitudeMode>
      <coordinates>{wp["lng"]},{wp["lat"]},{wp["altitude"]}</coordinates>
    </Point>
  </Placemark>''')

    if waypoints:
        coords = " ".join([f'{wp["lng"]},{wp["lat"]},{wp["altitude"]}' for wp in waypoints])
        kml_lines.append(f'''  <Placemark>
    <name>巡逻路径</name>
    <LineString>
      <altitudeMode>relativeToGround</altitudeMode>
      <coordinates>{coords}</coordinates>
    </LineString>
  </Placemark>''')

    kml_lines.extend(['</Document>', '</kml>'])
    return "\n".join(kml_lines)
