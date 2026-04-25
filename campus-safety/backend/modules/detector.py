"""YOLOv8 检测模块"""
import cv2
import os
import numpy as np
from ultralytics import YOLO
from config import Config

_model = None

def get_model():
    global _model
    if _model is None:
        import torch
        import urllib.request
        
        model_path = Config.YOLO_MODEL_PATH
        
        # 如果模型文件不存在且是默认名称，自动下载
        if not os.path.exists(model_path) and model_path == "yolov8n.pt":
            print("[Detector] yolov8n.pt 不存在，尝试自动下载...")
        
        # 兼容 PyTorch 2.6+ 的 weights_only 默认值变更
        _orig_load = torch.load
        torch.load = lambda *args, **kwargs: _orig_load(*args, **{**kwargs, 'weights_only': False})
        _model = YOLO(model_path)  # ultralytics 会自动下载
        torch.load = _orig_load
        print(f"[Detector] 模型加载成功: {model_path}")
    return _model

def detect_frame(frame):
    """
    对单帧图像进行检测
    返回: list of dict {class_name, confidence, bbox: [x1,y1,x2,y2]}
    只返回危险行为类别
    """
    import modules.detection_config as det_cfg
    model = get_model()
    results = model(frame, verbose=False)[0]

    confidence_threshold = det_cfg.get("confidence", Config.YOLO_CONFIDENCE)
    danger_classes = det_cfg.get("dangerClasses", Config.DANGER_CLASSES)

    detections = []
    for box in results.boxes:
        cls_id = int(box.cls[0])
        cls_name = model.names[cls_id]
        conf = float(box.conf[0])

        if cls_name in danger_classes and conf >= confidence_threshold:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            detections.append({
                "class_name": cls_name,
                "confidence": conf,
                "bbox": [x1, y1, x2, y2],
            })

    return detections

def draw_detections(frame, detections):
    """在帧上绘制检测框，支持中文标签"""
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    colors = {
        "fighting": (255, 0, 0),      # 红
        "falling":  (255, 165, 0),    # 橙
        "intrusion":(0, 0, 255),      # 蓝
        "objects":  (0, 200, 0),      # 绿
    }
    labels_cn = {
        "fighting": "打架/暴力",
        "falling":  "跌倒",
        "intrusion":"陌生人入侵",
        "objects":  "正常",
    }

    # 转为 PIL 图像
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)

    # 尝试加载中文字体，找不到则用默认字体
    font = None
    font_paths = [
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, 18)
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()

    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        cls = det["class_name"]
        conf = det["confidence"]
        color = colors.get(cls, (0, 255, 0))
        label = f"{labels_cn.get(cls, cls)} {conf:.2f}"

        # 画框（PIL颜色是RGB）
        draw.rectangle([x1, y1, x2, y2], outline=color, width=2)

        # 画标签背景
        bbox_text = font.getbbox(label) if hasattr(font, 'getbbox') else (0, 0, len(label)*10, 18)
        text_w = bbox_text[2] - bbox_text[0]
        text_h = bbox_text[3] - bbox_text[1]
        draw.rectangle([x1, y1 - text_h - 4, x1 + text_w + 6, y1], fill=color)

        # 画文字
        draw.text((x1 + 3, y1 - text_h - 2), label, font=font, fill=(255, 255, 255))

    # 转回 OpenCV 格式
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
