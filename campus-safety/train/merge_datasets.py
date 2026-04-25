"""
数据集合并脚本 - 精确ID映射版本
最终类别：
  0: fighting  (来源: Fighting/0, fight/0, violence/1)
  1: falling   (来源: Fall/0)
  2: intrusion (来源: Intrusion detected/0)
  3: objects   (来源: Non-fall/1, nofight/1, objects/0)

映射表（原始ID → 新ID）：
  Fall Detection:           {0→1, 1→3}
  Fighting Detection:       {0→0}
  fighting recognition:     {0→0, 1→3}
  Intrusion Detection:      {0→2}
  violence detection:       {0→3, 1→0}

使用方法：python merge_datasets.py
"""
import os
import shutil
import yaml
import glob
from pathlib import Path

# ── 修改为你的数据集实际路径 ──────────────────────────────────
DATASETS_ROOT = r"C:\path\to\your\datasets"  # ← 改成你的路径
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "merged_dataset")
# ────────────────────────────────────────────────────────────────

FINAL_CLASSES = ["fighting", "falling", "intrusion", "objects"]

# 精确映射：原始ID → 新ID（基于已知的原始类别ID）
# None 表示丢弃该标注行
DATASET_ID_MAPPINGS = {
    "Fall Detection.yolo26": {
        # ['Fall'=0, 'Non-fall'=1]
        0: 1,   # Fall → falling
        1: 3,   # Non-fall → objects
    },
    "Fighting Detection Dataset.yolo26": {
        # ['Fighting'=0]
        0: 0,   # Fighting → fighting
    },
    "fighting recognition.yolo26": {
        # ['fight'=0, 'nofight'=1]
        0: 0,   # fight → fighting
        1: 3,   # nofight → objects
    },
    "Intrusion Detection by YOLOv11.yolo26": {
        # ['Intrusion detected'=0]
        0: 2,   # Intrusion detected → intrusion
    },
    "violence detection.yolo26": {
        # ['objects'=0, 'violence'=1]
        0: 3,   # objects → objects
        1: 0,   # violence → fighting
    },
}


def find_yaml(dataset_dir):
    for name in ["data.yaml", "dataset.yaml"]:
        p = os.path.join(dataset_dir, name)
        if os.path.exists(p):
            return p
    yamls = glob.glob(os.path.join(dataset_dir, "*.yaml"))
    return yamls[0] if yamls else None


def remap_label_file(src_label_path, dst_label_path, id_mapping):
    """
    精确重映射标注文件的类别ID
    
    id_mapping: {原始ID: 新ID}
    
    示例（violence detection）：
      原txt行：0 0.5 0.3 0.2 0.4  → 原ID=0(objects) → 新ID=3
      原txt行：1 0.3 0.6 0.1 0.2  → 原ID=1(violence) → 新ID=0(fighting)
    """
    if not os.path.exists(src_label_path):
        return 0

    new_lines = []
    with open(src_label_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue

            old_id = int(parts[0])
            new_id = id_mapping.get(old_id)

            if new_id is None:
                continue  # 该ID不在映射中，丢弃

            # 保留坐标，只替换类别ID
            new_lines.append(f"{new_id} {' '.join(parts[1:])}")

    if new_lines:
        os.makedirs(os.path.dirname(dst_label_path), exist_ok=True)
        with open(dst_label_path, "w") as f:
            f.write("\n".join(new_lines) + "\n")
        return len(new_lines)
    return 0


def merge():
    print("=" * 60)
    print("开始合并数据集")
    print(f"最终类别: {FINAL_CLASSES}")
    print("=" * 60)

    for split in ["train", "val", "test"]:
        os.makedirs(os.path.join(OUTPUT_DIR, split, "images"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, split, "labels"), exist_ok=True)

    total_images = {"train": 0, "val": 0, "test": 0}
    class_stats = {i: 0 for i in range(len(FINAL_CLASSES))}

    for ds_name, id_mapping in DATASET_ID_MAPPINGS.items():
        ds_path = os.path.join(DATASETS_ROOT, ds_name)
        if not os.path.exists(ds_path):
            print(f"\n❌ 不存在: {ds_path}")
            continue

        print(f"\n📁 {ds_name}")
        mapping_desc = {FINAL_CLASSES[v]: f"原ID={k}" for k, v in id_mapping.items()}
        print(f"   ID映射: {id_mapping}  ({mapping_desc})")

        prefix = ds_name.split(".")[0].replace(" ", "_")[:25]

        for split in ["train", "val", "test"]:
            img_dir = None
            for candidate in [
                os.path.join(ds_path, split, "images"),
                os.path.join(ds_path, split),
                os.path.join(ds_path, "images", split),
            ]:
                if os.path.exists(candidate):
                    img_dir = candidate
                    break
            if not img_dir:
                continue

            label_dir = img_dir.replace("images", "labels")

            img_files = []
            for ext in ["*.jpg", "*.jpeg", "*.png", "*.bmp"]:
                img_files.extend(glob.glob(os.path.join(img_dir, ext)))

            count = 0
            for img_path in img_files:
                img_name = os.path.basename(img_path)
                stem = Path(img_name).stem

                dst_img = os.path.join(OUTPUT_DIR, split, "images", f"{prefix}_{img_name}")
                dst_label = os.path.join(OUTPUT_DIR, split, "labels", f"{prefix}_{stem}.txt")

                shutil.copy2(img_path, dst_img)

                src_label = os.path.join(label_dir, f"{stem}.txt")
                remap_label_file(src_label, dst_label, id_mapping)
                count += 1

            total_images[split] += count
            if count > 0:
                print(f"   {split}: {count} 张")

    # 统计各类别数量
    for split in ["train", "val"]:
        label_dir = os.path.join(OUTPUT_DIR, split, "labels")
        for lf in glob.glob(os.path.join(label_dir, "*.txt")):
            with open(lf) as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        cid = int(parts[0])
                        if cid in class_stats:
                            class_stats[cid] += 1

    # 生成 data.yaml
    yaml_content = {
        "path": OUTPUT_DIR.replace("\\", "/"),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "nc": len(FINAL_CLASSES),
        "names": FINAL_CLASSES,
    }
    yaml_out = os.path.join(OUTPUT_DIR, "data.yaml")
    with open(yaml_out, "w", encoding="utf-8") as f:
        yaml.dump(yaml_content, f, allow_unicode=True, default_flow_style=False)

    print("\n" + "=" * 60)
    print("✅ 合并完成！")
    print(f"   训练集: {total_images['train']} 张")
    print(f"   验证集: {total_images['val']} 张")
    print(f"   测试集: {total_images['test']} 张")
    print(f"   总计:   {sum(total_images.values())} 张")
    print("\n各类别标注框数量（train+val）:")
    for cid, cnt in class_stats.items():
        print(f"   ID={cid} {FINAL_CLASSES[cid]}: {cnt} 个")
    print(f"\n   data.yaml: {yaml_out}")


if __name__ == "__main__":
    print("完整ID映射预览：")
    print(f"{'数据集':<40} {'原ID':<6} {'原类名':<25} {'新ID':<6} {'新类名'}")
    print("-" * 90)
    src_names = {
        "Fall Detection.yolo26":              {0: "Fall", 1: "Non-fall"},
        "Fighting Detection Dataset.yolo26":  {0: "Fighting"},
        "fighting recognition.yolo26":        {0: "fight", 1: "nofight"},
        "Intrusion Detection by YOLOv11.yolo26": {0: "Intrusion detected"},
        "violence detection.yolo26":          {0: "objects", 1: "violence"},
    }
    for ds, id_map in DATASET_ID_MAPPINGS.items():
        for old_id, new_id in id_map.items():
            old_name = src_names[ds].get(old_id, "?")
            new_name = FINAL_CLASSES[new_id]
            print(f"  {ds:<40} {old_id:<6} {old_name:<25} {new_id:<6} {new_name}")
    print()
    confirm = input("确认映射正确，输入 y 开始合并: ")
    if confirm.lower() == "y":
        merge()
    else:
        print("已取消，请修改后重新运行")
