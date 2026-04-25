"""通知模块 - 短信模拟 + 监控室警报"""
from datetime import datetime
from modules.event_store import save_notification, get_notifications

ADMIN_CONTACTS = [
    {"name": "张校长", "phone": "138****0001", "role": "校长"},
    {"name": "李主任", "phone": "139****0002", "role": "安全主任"},
    {"name": "王保安", "phone": "137****0003", "role": "保安队长"},
]

def send_sms_alert(event):
    behavior_cn = {
        "person": "人员异常",
        "fighting": "打架斗殴",
        "bullying": "校园霸凌",
        "falling": "人员跌倒",
        "gathering": "异常聚集",
        "intrusion": "陌生人入侵",
    }.get(event["behavior"], event["behavior"])

    notifications = []
    for admin in ADMIN_CONTACTS:
        msg = (
            f"【校园安全预警】{event['timestamp'][11:16]} "
            f"{event['camera_name']}发现{behavior_cn}，"
            f"请立即处置。事件ID: {event['id'][:8]}"
        )
        record = {
            "time": datetime.now().isoformat(),
            "recipient": admin["name"],
            "phone": admin["phone"],
            "role": admin["role"],
            "message": msg,
            "status": "已发送（模拟）",
            "event_id": event["id"],
        }
        save_notification(record)
        notifications.append(record)

    return notifications

def trigger_alarm(event):
    behavior_cn = {
        "person": "人员异常",
        "fighting": "打架斗殴",
        "bullying": "校园霸凌",
        "falling": "人员跌倒",
        "gathering": "异常聚集",
        "intrusion": "陌生人入侵",
    }.get(event["behavior"], event["behavior"])

    return {
        "type": "alarm",
        "event_id": event["id"],
        "camera_name": event["camera_name"],
        "behavior": behavior_cn,
        "timestamp": event["timestamp"],
        "level": "HIGH" if event["behavior"] in ["fighting", "intrusion"] else "MEDIUM",
    }

def get_notification_log(limit=30):
    return get_notifications(limit)
