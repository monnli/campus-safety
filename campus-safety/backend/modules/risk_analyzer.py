"""风险预测与态势分析模块"""
import dashscope
from dashscope import Generation
from collections import Counter
from datetime import datetime, timedelta
from config import Config

dashscope.api_key = Config.DASHSCOPE_API_KEY

BEHAVIOR_CN = {
    "person": "人员异常",
    "fighting": "打架斗殴",
    "bullying": "校园霸凌",
    "falling": "人员跌倒",
    "gathering": "异常聚集",
    "intrusion": "陌生人入侵",
}

def analyze_risk(events):
    """
    基于历史事件数据进行风险分析和预测
    返回结构化的风险报告
    """
    if not events:
        return {
            "risk_level": "低",
            "risk_score": 10,
            "high_risk_areas": [],
            "high_risk_hours": [],
            "predictions": [],
            "suggestions": ["当前暂无历史事件数据，系统运行正常。"],
            "summary": "校园安全态势良好，暂无异常记录。"
        }

    # 统计分析
    behavior_counter = Counter(e["behavior"] for e in events)
    area_counter = Counter(e["camera_name"] for e in events)
    hour_counter = Counter(e["timestamp"][11:13] for e in events)

    # 高危区域（事件数前3）
    high_risk_areas = [{"area": k, "count": v} for k, v in area_counter.most_common(3)]

    # 高危时段（事件数前3）
    high_risk_hours = sorted(
        [{"hour": f"{h}:00", "count": c} for h, c in hour_counter.most_common(3)],
        key=lambda x: x["hour"]
    )

    # 风险评分（简单加权）
    weights = {"fighting": 10, "intrusion": 10, "bullying": 8, "gathering": 5, "falling": 6, "person": 3}
    risk_score = min(100, sum(weights.get(b, 3) * c for b, c in behavior_counter.items()))
    risk_level = "高" if risk_score >= 60 else "中" if risk_score >= 30 else "低"

    # 构建 LLM 分析上下文
    recent = events[:20]
    summary_text = "\n".join([
        f"- {e['timestamp'][5:16]} {e['camera_name']} {BEHAVIOR_CN.get(e['behavior'], e['behavior'])}"
        for e in recent
    ])

    prompt = f"""你是校园安全AI分析师。请根据以下近期事件数据，生成一份简洁的风险分析报告。

近期事件（共{len(events)}条）：
{summary_text}

高频区域：{', '.join(f"{a['area']}({a['count']}次)" for a in high_risk_areas)}
高危时段：{', '.join(f"{h['hour']}({h['count']}次)" for h in high_risk_hours)}
当前风险等级：{risk_level}（评分{risk_score}/100）

请输出：
1. 态势总结（2句话）
2. 风险预测（未来可能发生的情况，2-3条）
3. 防控建议（具体可操作的建议，3条）

格式要简洁，每条不超过30字。"""

    predictions = []
    suggestions = []
    summary = f"校园安全风险等级：{risk_level}，近期共记录{len(events)}起事件。"

    try:
        response = Generation.call(
            model=Config.LLM_MODEL,
            prompt=prompt,
            max_tokens=400,
        )
        if response.status_code == 200:
            text = response.output.text
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            # 简单解析
            mode = None
            for line in lines:
                if "态势" in line or "总结" in line:
                    mode = "summary"
                elif "预测" in line:
                    mode = "prediction"
                elif "建议" in line or "防控" in line:
                    mode = "suggestion"
                elif line.startswith(("1.", "2.", "3.", "4.", "-", "•", "·")):
                    content = line.lstrip("1234567890.-•· ")
                    if mode == "prediction":
                        predictions.append(content)
                    elif mode == "suggestion":
                        suggestions.append(content)
                    elif mode == "summary":
                        summary = content
    except Exception as e:
        print(f"[RiskAnalyzer] API异常，使用Mock数据: {e}")
        from modules.mock_data import get_mock_risk_analysis
        mock = get_mock_risk_analysis()
        mock["high_risk_areas"] = high_risk_areas
        mock["high_risk_hours"] = high_risk_hours
        mock["behavior_stats"] = dict(behavior_counter)
        mock["total_events"] = len(events)
        mock["risk_score"] = risk_score
        mock["risk_level"] = risk_level
        return mock

    if not predictions:
        predictions = [f"{h['hour']} 时段 {high_risk_areas[0]['area'] if high_risk_areas else '校园'} 风险较高" for h in high_risk_hours[:2]]
    if not suggestions:
        suggestions = [f"加强 {a['area']} 区域巡逻频次" for a in high_risk_areas[:3]]

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "high_risk_areas": high_risk_areas,
        "high_risk_hours": high_risk_hours,
        "behavior_stats": dict(behavior_counter),
        "predictions": predictions[:3],
        "suggestions": suggestions[:3],
        "summary": summary,
        "total_events": len(events),
    }
