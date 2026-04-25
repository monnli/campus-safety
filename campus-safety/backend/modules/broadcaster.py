"""TTS 广播模块 - 阿里云语音合成"""
import os
import uuid
import requests
from config import Config

# 阿里云 TTS REST API
TTS_URL = "https://nls-gateway.cn-shanghai.aliyuncs.com/stream/v1/tts"

def text_to_speech(text, output_dir=None):
    """
    将文字转为语音文件
    返回: 音频文件路径 或 None
    """
    if output_dir is None:
        output_dir = Config.ALERT_CLIPS_DIR
    
    os.makedirs(output_dir, exist_ok=True)
    filename = f"broadcast_{uuid.uuid4().hex[:8]}.mp3"
    filepath = os.path.join(output_dir, filename)
    
    headers = {
        "X-NLS-Token": Config.TTS_TOKEN,
        "Content-Type": "application/json",
    }
    payload = {
        "appkey": Config.TTS_APP_KEY,
        "text": text,
        "format": "mp3",
        "sample_rate": 16000,
        "voice": "zhiyan_emo",   # 情感女声，适合广播
        "volume": 100,
        "speech_rate": 0,
        "pitch_rate": 0,
    }
    
    try:
        resp = requests.post(TTS_URL, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200 and resp.headers.get("Content-Type", "").startswith("audio"):
            with open(filepath, "wb") as f:
                f.write(resp.content)
            return filepath
        else:
            print(f"[TTS] 合成失败: {resp.status_code} {resp.text}")
            return None
    except Exception as e:
        print(f"[TTS] 异常: {e}")
        return None

def broadcast_alert(broadcast_text):
    """
    触发广播：合成语音并返回可播放的文件路径
    TTS 未配置时返回 None，不影响其他流程
    """
    if Config.TTS_APP_KEY == "your-tts-appkey":
        print(f"[TTS] 未配置，跳过广播: {broadcast_text}")
        return None
    audio_path = text_to_speech(broadcast_text)
    return audio_path
