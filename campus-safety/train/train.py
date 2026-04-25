"""
YOLO26x 微调训练脚本
使用方法：python train.py
"""
import os
from ultralytics import YOLO

# ── 配置 ──────────────────────────────────────────────────────
BASE_MODEL = "../backend/yolo26x.pt"          # 预训练模型路径
DATA_YAML  = "merged_dataset/data.yaml"       # 合并后的数据集配置
PROJECT    = "runs"                            # 训练结果保存目录
NAME       = "campus_safety_v1"               # 本次训练名称

EPOCHS     = 100        # 训练轮数（建议50~150）
IMGSZ      = 640        # 输入图像尺寸
BATCH      = 8          # 批大小（GPU显存不足时调小，如4或2）
WORKERS    = 4          # 数据加载线程数
DEVICE     = 0          # GPU设备号，无GPU时填 "cpu"
LR0        = 0.01       # 初始学习率
PATIENCE   = 30         # 早停耐心值（N轮无提升则停止）
# ────────────────────────────────────────────────────────────────


def train():
    print("=" * 60)
    print("开始微调 YOLO26x")
    print(f"  基础模型: {BASE_MODEL}")
    print(f"  数据集:   {DATA_YAML}")
    print(f"  训练轮数: {EPOCHS}")
    print(f"  批大小:   {BATCH}")
    print(f"  设备:     {DEVICE}")
    print("=" * 60)

    model = YOLO(BASE_MODEL)

    results = model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        workers=WORKERS,
        device=DEVICE,
        lr0=LR0,
        patience=PATIENCE,
        project=PROJECT,
        name=NAME,
        # 数据增强（针对校园场景优化）
        augment=True,
        hsv_h=0.015,    # 色调增强
        hsv_s=0.7,      # 饱和度增强
        hsv_v=0.4,      # 亮度增强
        degrees=10,     # 旋转角度
        translate=0.1,  # 平移
        scale=0.5,      # 缩放
        flipud=0.0,     # 上下翻转（监控场景不翻转）
        fliplr=0.5,     # 左右翻转
        mosaic=1.0,     # Mosaic增强
        mixup=0.1,      # Mixup增强
        # 保存设置
        save=True,
        save_period=10,  # 每10轮保存一次检查点
        val=True,
        plots=True,      # 生成训练曲线图
        verbose=True,
    )

    print("\n" + "=" * 60)
    print("✅ 训练完成！")
    best_model = os.path.join(PROJECT, NAME, "weights", "best.pt")
    print(f"   最佳模型: {best_model}")
    print(f"   训练结果: {os.path.join(PROJECT, NAME)}")

    # 验证最佳模型
    print("\n开始验证最佳模型...")
    best = YOLO(best_model)
    metrics = best.val(data=DATA_YAML, imgsz=IMGSZ, device=DEVICE)
    print(f"\n验证结果:")
    print(f"  mAP50:    {metrics.box.map50:.4f}")
    print(f"  mAP50-95: {metrics.box.map:.4f}")
    print(f"  Precision: {metrics.box.mp:.4f}")
    print(f"  Recall:    {metrics.box.mr:.4f}")

    return best_model


if __name__ == "__main__":
    best_model_path = train()
    print(f"\n训练完成后，将 .env 中的 YOLO_MODEL_PATH 改为:")
    print(f"  YOLO_MODEL_PATH={os.path.abspath(best_model_path)}")
