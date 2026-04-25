"""认证模块 - JWT + 多角色权限"""
import jwt
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

SECRET = "campus-safety-jwt-secret"

# 预设用户（demo阶段硬编码，生产环境应存数据库）
USERS = {
    "admin": {
        "password": hashlib.md5("admin123".encode()).hexdigest(),
        "role": "principal",
        "name": "张校长",
        "display": "校长"
    },
    "safety": {
        "password": hashlib.md5("safety123".encode()).hexdigest(),
        "role": "manager",
        "name": "李主任",
        "display": "安全主任"
    },
    "guard": {
        "password": hashlib.md5("guard123".encode()).hexdigest(),
        "role": "guard",
        "name": "王保安",
        "display": "保安"
    },
}

# 角色权限定义
ROLE_PERMISSIONS = {
    "principal": ["monitor", "events", "stats", "chat", "dashboard", "settings"],
    "manager":   ["monitor", "events", "stats", "chat", "dashboard"],
    "guard":     ["monitor", "events"],
}

def generate_token(username):
    user = USERS[username]
    payload = {
        "username": username,
        "role": user["role"],
        "name": user["name"],
        "display": user["display"],
        "exp": datetime.utcnow() + timedelta(hours=12),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")

def verify_token(token):
    try:
        return jwt.decode(token, SECRET, algorithms=["HS256"])
    except Exception:
        return None

def login(username, password):
    user = USERS.get(username)
    if not user:
        return None, "用户不存在"
    if user["password"] != hashlib.md5(password.encode()).hexdigest():
        return None, "密码错误"
    token = generate_token(username)
    return {
        "token": token,
        "username": username,
        "role": user["role"],
        "name": user["name"],
        "display": user["display"],
        "permissions": ROLE_PERMISSIONS[user["role"]],
    }, None

def require_auth(f):
    """路由装饰器：需要登录"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "未登录或登录已过期"}), 401
        request.user = payload
        return f(*args, **kwargs)
    return decorated

def require_role(*roles):
    """路由装饰器：需要指定角色"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get("Authorization", "").replace("Bearer ", "")
            payload = verify_token(token)
            if not payload:
                return jsonify({"error": "未登录或登录已过期"}), 401
            if payload["role"] not in roles:
                return jsonify({"error": "权限不足"}), 403
            request.user = payload
            return f(*args, **kwargs)
        return decorated
    return decorator
