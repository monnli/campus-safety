# 配置文件
import os

class Config:
    # 阿里云 DashScope API
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "your-api-key-here")
    
    # 模型选型
    VL_MODEL = "qwen-vl-max-latest"
    LLM_MODEL = "qwen-max-latest"
    
    # YOLOv8 模型路径
    YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolo26x.pt")
    YOLO_CONFIDENCE = 0.5  # 置信度阈值
    
    # 微调模型类别（与训练数据集 FINAL_CLASSES 对应）
    DANGER_CLASSES = ["fighting", "falling", "intrusion"]
    # objects 类（ID=3）为正常类，不触发预警
    
    # 视频处理
    FRAME_SKIP = 3          # 每隔几帧检测一次，降低计算量
    PRE_EVENT_SECONDS = 5   # 触发前保留几秒视频
    CLIP_DURATION = 15      # 存档片段总时长（秒）
    
    # 存档路径
    ALERT_CLIPS_DIR = os.path.join(os.path.dirname(__file__), "static", "alerts")
    
    # ffmpeg 路径（用于视频转码）
    FFMPEG_PATH = os.getenv("FFMPEG_PATH", r"C:\Users\29678\ffmpeg\bin\ffmpeg.exe")

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "campus-safety-secret")
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    
    # 阿里云 TTS
    TTS_APP_KEY = os.getenv("TTS_APP_KEY", "your-tts-appkey")
    TTS_TOKEN = os.getenv("TTS_TOKEN", "your-tts-token")
    
    # 摄像头配置
    CAMERAS = [
        {"id": "cam_001", "name": "操场", "location": "操场中央", "x": 45, "y": 60},
        {"id": "cam_002", "name": "校门口", "location": "正门", "x": 50, "y": 95},
        {"id": "cam_003", "name": "走廊A", "location": "教学楼A走廊", "x": 25, "y": 40},
        {"id": "cam_004", "name": "走廊B", "location": "教学楼B走廊", "x": 75, "y": 40},
        {"id": "cam_005", "name": "食堂", "location": "食堂入口", "x": 30, "y": 70},
        {"id": "drone_001", "name": "无人机", "location": "巡逻中", "x": 50, "y": 50, "is_drone": True},
    ]
    
    # 无人机巡逻时间段（课间+放学后半小时）
    DRONE_PATROL_SCHEDULES = [
        {"start": "10:00", "end": "10:15"},  # 上午课间
        {"start": "12:00", "end": "12:30"},  # 午休
        {"start": "14:00", "end": "14:15"},  # 下午课间
        {"start": "16:30", "end": "17:00"},  # 下午放学
        {"start": "18:00", "end": "18:30"},  # 晚放学
    ]
