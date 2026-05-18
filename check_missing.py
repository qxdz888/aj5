import json, os
from collections import Counter
from pathlib import Path

IMAGES_DIR = "images"
exts = {'.jpg','.jpeg','.png','.webp','.JPG','.JPEG','.PNG','.WEBP'}

# 磁盘上所有图片（相对路径，和 manifest 里的后缀匹配）
disk_rel = set()
for root, dirs, files in os.walk(IMAGES_DIR):
    for f in files:
        if any(f.lower().endswith(e) for e in exts):
            rel = os.path.join(root, f).replace('\\', '/')
            # 取 manifest 中对应的后缀部分
            disk_rel.add(rel)

print(f"磁盘图片总数: {len(disk_rel)}")

# manifest.json 里的图片路径（去掉前缀，只留相对部分）
m = json.load(open('manifest.json'))
manifest_rel = set()
for s in m['shoes']:
    url = s['image']
    # https://aj5.netlify.app/images/xxx -> images/xxx
    if 'images/' in url:
        rel = 'images/' + url.split('images/', 1)[1]
        manifest_rel.add(rel)

print(f"manifest 记录数: {len(manifest_rel)}")

missing = disk_rel - manifest_rel
extra = manifest_rel - disk_rel

if missing:
    print(f"\nmanifest 缺少 {len(missing)} 个图片，按目录统计：")
    dirs = Counter()
    for f in missing:
        parts = f.split('/')
        if len(parts) >= 3:
            dirs[parts[1] + '/' + parts[2]] += 1
        elif len(parts) >= 2:
            dirs[parts[1]] += 1
    for d, c in sorted(dirs.items()):
        print(f"  images/{d}/ : {c} 张")
else:
    print("\nmanifest 已包含所有磁盘图片")

if extra:
    print(f"\nmanifest 中有 {len(extra)} 个图片在磁盘上不存在（已删除但未更新）：")
    for f in sorted(extra)[:5]:
        print(" ", f)
