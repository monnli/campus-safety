"""Mock 数据模式 - API 不可用时返回预设数据，保证演示流畅"""

MOCK_VL_RESULTS = {
    "person": {
        "confirmed": True,
        "description": "图像中检测到多名学生在操场区域存在异常聚集行为，其中两名学生存在明显的肢体冲突动作，周围有学生围观，情况需要立即关注和处置。"
    },
    "fighting": {
        "confirmed": True,
        "description": "视频帧中清晰可见两名学生发生激烈肢体冲突，存在推搡、拉扯等暴力行为，周围有多名学生围观，事态有进一步升级的风险。"
    },
    "bullying": {
        "confirmed": True,
        "description": "图像显示一名学生被多名学生围堵，存在明显的威胁和欺凌行为，被围学生表现出明显的恐惧和无助，属于典型的校园霸凌场景。"
    },
    "falling": {
        "confirmed": True,
        "description": "检测到一名学生在走廊区域突然倒地，倒地姿势异常，周围无人注意，疑似突发身体不适或意外跌倒，需要立即派人查看。"
    },
    "gathering": {
        "confirmed": True,
        "description": "操场区域出现大量学生异常聚集，人群密度超出正常水平，聚集中心区域有明显的争执迹象，存在群体性事件风险。"
    },
    "intrusion": {
        "confirmed": True,
        "description": "校门口出现一名陌生成年人，其行为举止可疑，在校门附近徘徊超过5分钟，未经登记进入校园区域，需要安保人员立即核查身份。"
    },
}

MOCK_REPORTS = {
    "person": {
        "report": """【预警报告】
事件概述：AI系统于监控区域检测到人员异常行为，经多模态模型二次确认，判定存在安全风险。

风险等级：中级（MEDIUM）

建议处置措施：
1. 立即派遣安保人员前往事发区域进行现场核查
2. 通知班主任或相关教师关注涉事学生状态
3. 调取事发前后完整视频录像留存备查
4. 若情况属实，按校园安全应急预案启动相应处置流程""",
        "broadcast_text": "请注意，监控系统检测到异常情况，安保人员请立即前往操场区域处置，其他同学请保持秩序。"
    },
    "fighting": {
        "report": """【紧急预警报告】
事件概述：AI系统检测到打架斗殴事件，经Qwen-VL多模态模型确认，现场存在激烈肢体冲突。

风险等级：高级（HIGH）

建议处置措施：
1. 立即派遣多名安保人员前往现场制止冲突
2. 同时通知校长、安全主任到场处置
3. 保护现场，防止事态扩大
4. 对涉事学生进行隔离和心理疏导
5. 联系家长并做好事件记录""",
        "broadcast_text": "紧急广播：请所有同学立即保持秩序，安保人员请迅速前往操场处置紧急情况，无关人员请勿围观。"
    },
}

MOCK_RISK_ANALYSIS = {
    "risk_level": "中",
    "risk_score": 45,
    "high_risk_areas": [
        {"area": "操场", "count": 8},
        {"area": "校门口", "count": 5},
        {"area": "走廊A", "count": 3},
    ],
    "high_risk_hours": [
        {"hour": "12:00", "count": 6},
        {"hour": "16:30", "count": 5},
        {"hour": "10:00", "count": 4},
    ],
    "behavior_stats": {"person": 16, "fighting": 2, "gathering": 3},
    "predictions": [
        "午休时段（12:00-13:00）操场区域人员聚集风险较高",
        "放学后（16:30-17:00）校门口周边存在安全隐患",
        "走廊区域课间时段需加强巡逻频次",
    ],
    "suggestions": [
        "建议在操场增设1名安保人员，重点关注午休时段",
        "放学时段启动无人机巡逻，覆盖校园周边区域",
        "对近期频繁出现异常行为的学生开展心理健康评估",
    ],
    "summary": "校园安全风险等级：中，近期共记录21起事件，操场为高风险区域，建议加强重点时段巡逻。",
    "total_events": 21,
}

def get_mock_vl_result(behavior):
    return MOCK_VL_RESULTS.get(behavior, MOCK_VL_RESULTS["person"])

def get_mock_report(behavior):
    return MOCK_REPORTS.get(behavior, MOCK_REPORTS["person"])

def get_mock_risk_analysis():
    return MOCK_RISK_ANALYSIS
