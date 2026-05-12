#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动更新球鞋展示数据
扫描 images 目录下的图片，自动生成 JavaScript 数据
支持从文件名提取名称和价格
目录结构：images/品牌/分类/图片.jpg
"""
import os, re
from pathlib import Path

IMAGES_DIR = "images"
INDEX_FILE = "index.html"

# 分类配置（品牌/文件夹路径, 显示分类名）
CATEGORIES = [
    # Nike 品牌
    ("nike/乔一", "乔一"),
    ("nike/空军", "空军"),
    ("nike/小空军", "小空军"),
    ("nike/开拓者", "开拓者"),
    ("nike/高帮", "高帮"),
    # Adidas 品牌
    ("adidas/其他", "其他"),
    ("adidas/德讯", "德讯"),
    ("adidas/贝壳头", "贝壳头"),
    # Puma 品牌
    ("puma/彪马", "彪马"),
    # 独立品牌
    ("wans", "wans"),
    ("lv", "lv"),
]

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.JPG', '.JPEG', '.PNG', '.WEBP'}

def parse_filename(filename):
    """
    从文件名解析出名称和价格
    支持格式：
    - 黑紫脚趾-129元.jpg → 名称:黑紫脚趾, 价格:129元
    - 黑紫脚趾-129.jpg → 名称:黑紫脚趾, 价格:129元
    - 黑紫脚趾.jpg → 名称:黑紫脚趾, 价格:面议
    - 黑紫脚趾_129元.jpg → 名称:黑紫脚趾, 价格:129元
    """
    # 去掉扩展名
    name_without_ext = Path(filename).stem

    # 尝试用多种分隔符分割
    # 格式: 名称-价格 或 名称_价格 或 名称 价格
    patterns = [
        r'^(.+?)[-_](\d+元)$',      # 黑紫脚趾-129元 或 黑紫脚趾_129元
        r'^(.+?)[-_](\d+)$',         # 黑紫脚趾-129 或 黑紫脚趾_129
        r'^(.+?)\s+(\d+元)$',        # 黑紫脚趾 129元
        r'^(.+?)\s+(\d+)$',          # 黑紫脚趾 129
    ]

    for pattern in patterns:
        match = re.match(pattern, name_without_ext)
        if match:
            shoe_name = match.group(1).strip()
            price_raw = match.group(2)
            # 确保价格带"元"
            if price_raw.isdigit():
                price = f"{price_raw}元"
            else:
                price = price_raw
            return shoe_name, price

    # 没有价格信息
    return name_without_ext, "面议"

def scan_images():
    """扫描图片目录，返回鞋子数据列表"""
    shoes = []
    shoe_id = 1
    for folder, display in CATEGORIES:
        path = Path(IMAGES_DIR) / folder
        if not path.exists():
            print(f"[WARN] 目录不存在: {path}")
            continue

        # 使用 dict 按小写文件名去重（解决大小写重复问题）
        seen = {}
        for ext in IMAGE_EXTENSIONS:
            for f in path.glob(f"*{ext}"):
                key = f.name.lower()  # 用小写作为 key 去重
                if key not in seen:
                    seen[key] = f  # 保留原始 Path 对象

        # 排序
        files = sorted(seen.values(), key=lambda x: x.name)

        if not files:
            print(f"[WARN] 无图片: {folder}")
            continue
        print(f"[INFO] {folder}: {len(files)} 张图片")
        for idx, f in enumerate(files, 1):
            # 从文件名解析名称和价格
            shoe_name, shoe_price = parse_filename(f.name)

            shoes.append({
                "id": shoe_id,
                "name": shoe_name,
                "category": display,
                "imgIndex": idx,
                "price": shoe_price,
                "image": f"{IMAGES_DIR}/{folder}/{f.name}"
            })
            shoe_id += 1
    return shoes

def update_html(shoes):
    """更新 index.html 中的 shoes 数据"""
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    js = "const shoes = [\n" + ",\n".join(
        f'  {{ id: {s["id"]}, name: "{s["name"]}", category: "{s["category"]}", imgIndex: {s["imgIndex"]}, price: "{s["price"]}", image: "{s["image"]}"'
        for s in shoes
    ) + "\n];"

    # 匹配 const shoes = [...] 块
    new = re.sub(r'const shoes = \[.*?\];', js, content, flags=re.DOTALL)
    if new == content:
        print("[WARN] 无变更")
        return False
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(new)
    print(f"[OK] 已更新 {len(shoes)} 个商品")
    return True

if __name__ == "__main__":
    shoes = scan_images()
    if not shoes:
        print("[ERR] 无数据")
    else:
        update_html(shoes)
