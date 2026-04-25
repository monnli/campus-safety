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

def _local_answer_query(query: str, events_context: str) -> str:
    """
    LLM 不可用时的本地兜底回答（基于 events_context 文本摘要 + 简单关键词）。
    注意：这不是真正的语义理解，但能保证演示/断网场景下仍可用。
    """
    q = (query or "").strip()
    if not q:
        return "请输入要查询的问题。"

    # events_context 由 app.py 拼接，包含若干行事件摘要；这里做轻量解析
    lines = [ln.strip() for ln in (events_context or "").splitlines() if ln.strip() and not ln.startswith("暂无")]
    if "暂无相关事件记录" in (events_context or "") or not lines:
        return "当前数据库中没有匹配到相关事件记录（或事件数据为空）。你可以先去「事件记录」确认是否有数据，或调整问题关键词。"

    # 哪个区域最危险 / 高发区域
    if any(k in q for k in ["哪个区域", "哪块区域", "哪里最危险", "最危险", "高发区域", "区域风险"]):
        from collections import Counter

        areas = []
        for ln in lines:
            # 形如：[12:34] 操场 - fighting (置信度0.93): ...
            if "]" in ln and " - " in ln:
                try:
                    tail = ln.split("]", 1)[1].strip()
                    area = tail.split(" - ", 1)[0].strip()
                    if area:
                        areas.append(area)
                except Exception:
                    continue
        if not areas:
            return "我能找到相关事件记录，但无法从当前数据格式中解析区域字段。请尝试更具体的问题，例如：「今天操场发生了几次打架？」"
        top = Counter(areas).most_common(3)
        top_txt = "、".join([f"{a}（{c}次）" for a, c in top])
        return f"按当前匹配到的事件记录统计，事件出现频次较高的区域为：{top_txt}。提示：该结论来自本地事件统计；若需更深入的成因分析与建议，请配置可用的 DashScope API Key 以启用大模型回答。"

    # 今天发生了哪些事件
    if "今天" in q:
        return f"根据当前匹配到的事件记录（最多展示部分摘要），共 {len(lines)} 条相关摘要行。你可以在「事件记录」页面按时间筛选查看完整列表。\n\n提示：更智能的归纳总结需要 DashScope LLM；当前为离线/兜底模式。"

    # 建议类
    if any(k in q for k in ["建议", "怎么办", "措施", "防控"]):
        return (
            "基于当前事件数据，建议优先做三件事：\n"
            "1）对事件高发区域与时段加密巡逻与视频巡查；\n"
            "2）对重复出现的风险类型（如打架/入侵）建立快速响应流程；\n"
            "3）完善告警闭环：确认、处置、复盘并标注误报。\n\n"
            "提示：更个性化的建议可启用 DashScope LLM（配置 DASHSCOPE_API_KEY）。"
        )

    return (
        "当前大模型服务不可用，我已切换到本地兜底模式：仍可根据事件记录给出统计型回答，但无法进行复杂推理。\n"
        f"你问的是：{q}\n"
        f"我匹配到的事件摘要行数：{len(lines)}。建议你把问题改得更具体（带时间/地点/行为类型关键词），或检查 `.env` 中的 `DASHSCOPE_API_KEY` 是否有效、网络是否可达。"
    )


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
        # 非 200：通常是 Key/额度/权限/模型名/网络等问题
        return _local_answer_query(query, events_context) + (
            f"\n\n（说明：DashScope LLM 调用未成功，status={getattr(response, 'status_code', 'unknown')}，"
            f"message={getattr(response, 'message', '')}）"
        )
    except Exception as e:
        return _local_answer_query(query, events_context) + f"\n\n（说明：DashScope LLM 调用异常：{e}）"

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
