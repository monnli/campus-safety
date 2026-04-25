"""Qwen LLM 报告生成与自然语言查询模块"""
import dashscope
from dashscope import Generation
from config import Config
from datetime import datetime

dashscope.api_key = Config.DASHSCOPE_API_KEY

BEHAVIOR_CN = {
    "person": "人员异常行为",
    "fighting": "打架斗殴",
    "bullying": "校园霸凌",
    "falling": "人员跌倒",
    "gathering": "异常聚集",
    "intrusion": "陌生人入侵",
}

def generate_alert_report(camera_name, behavior, vl_description, timestamp=None):
    """
    生成预警报告
    返回: {"report": str, "broadcast_text": str}
    """
    ts = timestamp or datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    behavior_cn = BEHAVIOR_CN.get(behavior, behavior)
    
    prompt = f"""你是一个校园安全AI助手。请根据以下信息生成一份简洁的安全预警报告，并生成一段用于校园广播驱离的播报文字。

事件信息：
- 时间：{ts}
- 地点：{camera_name}
- 检测到的行为：{behavior_cn}
- 视觉分析结果：{vl_description}

请输出以下两部分（用---分隔）：
1. 预警报告（包含：事件概述、风险等级、建议处置措施）
2. 广播播报文字（简短、权威、适合校园广播，不超过50字）"""

    try:
        response = Generation.call(
            model=Config.LLM_MODEL,
            prompt=prompt,
            max_tokens=500,
        )
        
        if response.status_code == 200:
            text = response.output.text
            parts = text.split("---")
            report = parts[0].strip() if len(parts) > 0 else text
            broadcast = parts[1].strip() if len(parts) > 1 else f"注意，{camera_name}发现{behavior_cn}，请相关人员立即前往处置。"
            return {"report": report, "broadcast_text": broadcast}
        else:
            return {
                "report": f"报告生成失败: {response.message}",
                "broadcast_text": f"注意，{camera_name}发现{behavior_cn}，请相关人员立即前往处置。"
            }
    except Exception as e:
        print(f"[Reporter] API异常，使用Mock数据: {e}")
        from modules.mock_data import get_mock_report
        return get_mock_report(behavior)

def answer_query(query, events_context):
    """
    自然语言查询历史事件
    events_context: 相关事件列表的文本摘要
    """
    prompt = f"""你是校园安全管理系统的AI助手。管理员提出了以下问题，请根据提供的事件数据回答。

管理员问题：{query}

相关事件数据：
{events_context}

请用简洁、专业的语言回答，如果数据中没有相关信息请如实说明。"""

    try:
        response = Generation.call(
            model=Config.LLM_MODEL,
            prompt=prompt,
            max_tokens=300,
        )
        if response.status_code == 200:
            return response.output.text
        return "查询服务暂时不可用，请稍后再试。"
    except Exception as e:
        return f"查询异常: {str(e)}"

def generate_daily_report(events):
    """生成日报"""
    if not events:
        return "今日暂无安全事件记录。"
    
    summary = "\n".join([
        f"- {e['timestamp'][11:16]} {e['camera_name']} 发现{BEHAVIOR_CN.get(e['behavior'], e['behavior'])}（置信度{e['confidence']}）"
        for e in events[:20]
    ])
    
    prompt = f"""请根据以下今日校园安全事件记录，生成一份简洁的日报总结，包括：事件总览、高频区域、高频行为类型、安全建议。

今日事件记录：
{summary}

总计 {len(events)} 起事件。"""

    try:
        response = Generation.call(
            model=Config.LLM_MODEL,
            prompt=prompt,
            max_tokens=400,
        )
        if response.status_code == 200:
            return response.output.text
        return "日报生成失败。"
    except Exception as e:
        return f"日报生成异常: {str(e)}"
