"""Qwen-VL 多模态分析模块 - 支持单帧和多帧视频级分析"""
import base64
import cv2
import dashscope
from dashscope import MultiModalConversation
from config import Config

dashscope.api_key = Config.DASHSCOPE_API_KEY

BEHAVIOR_PROMPTS = {
    "person": "请分析这组连续视频帧，判断图中的人员是否存在异常行为，例如打架、跌倒、聚集、霸凌或可疑举动。结合多帧的时序变化描述你看到的情况，并给出是否存在安全风险的结论。",
    "fighting": "请分析这组连续视频帧，判断图中是否存在打架、肢体冲突或暴力行为。结合多帧的时序变化描述事件经过，并给出是否确认为危险行为的结论。",
    "bullying": "请分析这组连续视频帧，判断图中是否存在霸凌、欺负、威胁或孤立他人的行为。结合多帧的时序变化描述事件经过，并给出是否确认为危险行为的结论。",
    "falling": "请分析这组连续视频帧，判断图中是否有人员跌倒、摔伤或处于异常倒地状态。结合多帧的时序变化描述事件经过，并给出是否确认为危险行为的结论。",
    "gathering": "请分析这组连续视频帧，判断图中是否存在异常人员聚集、围观或可能引发冲突的群体行为。结合多帧的时序变化描述事件经过，并给出是否确认为危险行为的结论。",
    "intrusion": "请分析这组连续视频帧，判断图中是否存在陌生人闯入、非法入侵校园或可疑人员的情况。结合多帧的时序变化描述事件经过，并给出是否确认为危险行为的结论。",
}

def _frame_to_base64(frame):
    _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return base64.b64encode(buffer).decode("utf-8")

def analyze_frames(frames, behavior):
    """
    使用 Qwen-VL 对多帧进行视频级分析
    frames: list of numpy frames（从视频片段均匀抽取）
    返回: {"confirmed": bool, "description": str}
    """
    if not frames:
        return {"confirmed": True, "description": "无可用帧，默认确认。"}

    prompt = BEHAVIOR_PROMPTS.get(behavior, "请分析这组连续视频帧是否存在危险行为，并描述事件经过。")

    # 构建多图消息，每帧作为一个 image content
    content = []
    for frame in frames:
        b64 = _frame_to_base64(frame)
        content.append({"image": f"data:image/jpeg;base64,{b64}"})
    content.append({"text": prompt})

    try:
        response = MultiModalConversation.call(
            model=Config.VL_MODEL,
            messages=[{"role": "user", "content": content}]
        )

        if response.status_code == 200:
            description = response.output.choices[0].message.content[0]["text"]
            confirmed = any(kw in description for kw in ["确认", "存在", "发现", "是的", "确实", "异常", "危险"])
            return {"confirmed": confirmed, "description": description}
        else:
            return {"confirmed": True, "description": f"分析服务异常: {response.message}"}

    except Exception as e:
        print(f"[Analyzer] API异常，使用Mock数据: {e}")
        from modules.mock_data import get_mock_vl_result
        return get_mock_vl_result(behavior)

def analyze_frame(frame, behavior):
    """单帧分析（兼容旧接口）"""
    return analyze_frames([frame], behavior)
