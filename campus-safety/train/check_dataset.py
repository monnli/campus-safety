"""
数据集检查脚本 - 合并前先运行此脚本查看各数据集的类别
使用方法：python check_dataset.py
"""
import os
import yaml
import glob

DATASETS_ROOT = r"C:\path\to\your\datasets"  # 修改为数据集所在目录

DATASET_DIRS = [
    "Fall Detection.yolo26",
    "Fighting Detection Dataset.yolo26",
    "fighting recognition.yolo26",
    "Intrusion Detection by YOLOv11.yolo26",
    "violence detection.yolo26",
]

for ds_name in DATASET_DIRS:
    ds_path = os.path.join(DATASETS_ROOT, ds_name)
    print(f"\n{'='*50}")
    print(f"数据集: {ds_name}")

    if not os.path.exists(ds_path):
        print("  ❌ 目录不存在")
        continue

    # 找 yaml
    yaml_file = None
    for name in ["data.yaml", "dataset.yaml"]:
        p = os.path.join(ds_path, name)
        if os.path.exists(p):
            yaml_file = p
            break
    if not yaml_file:
        yamls = glob.glob(os.path.join(ds_path, "*.yaml"))
        yaml_file = yamls[0] if yamls else None

    if yaml_file:
        with open(yaml_file, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        names = cfg.get("names", [])
        print(f"  类别数: {cfg.get('nc', '?')}")
        print(f"  类别名: {names}")
    else:
        print("  ❌ 未找到 yaml 文件")

    # 统计图片数量
    for split in ["train", "val", "test"]:
        for img_dir in [
            os.path.join(ds_path, split, "images"),
            os.path.join(ds_path, split),
        ]:
            if os.path.exists(img_dir):
                imgs = []
                for ext in ["*.jpg", "*.jpeg", "*.png"]:
                    imgs.extend(glob.glob(os.path.join(img_dir, ext)))
                print(f"  {split}: {len(imgs)} 张图片")
                break
