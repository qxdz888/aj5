#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动更新球鞋展示数据
扫描 images 目录结构，自动生成导航菜单和图片数据

使用说明：
1. 在 images/ 目录下按品牌+子分类创建文件夹结构
2. 把图片放到对应分类文件夹，文件名格式：款式-价格元.jpg
3. 运行此脚本，自动更新 index.html

目录结构示例：
images/
├── nike/
│   ├── 乔一/          ← 放图片
│   ├── 空军/          ← 放图片
│   ├── 小空军/        ← 放图片
│   ├── 开拓者/        ← 放图片
│   └── 高帮/          ← 放图片
├── adidas/
│   ├── 阿迪/          ← 放图片
│   ├── 其他/          ← 放图片
│   ├── 德讯/          ← 放图片
│   └── 贝壳头/        ← 放图片
├── puma/
│   └── 彪马/          ← 放图片
├── wans/              ← 独立品牌，图片直接在文件夹下
└── lv/                ← 独立品牌，图片直接在文件夹下
"""
import os, re
from pathlib import Path

IMAGES_DIR = "images"
INDEX_FILE = "index.html"

# 品牌配置（文件夹名，显示名）
BRANDS = {
    "nike": "Nike",
    "adidas": "Adidas",
    "puma": "Puma",
}

# 独立品牌（没有子分类，图片直接在品牌文件夹下）
STANDALONE_BRANDS = ["wans", "lv"]

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.JPG', '.JPEG', '.PNG', '.WEBP'}

def parse_filename(filename):
    """
    从文件名解析出名称和价格
    支持格式：
    - 黑紫脚趾-129元.jpg → 名称:黑紫脚趾, 价格:129元
    - 黑紫脚趾-129.jpg → 名称:黑紫脚趾, 价格:129元
    - 黑紫脚趾.jpg → 名称:黑紫脚趾, 价格:面议
    """
    name_without_ext = Path(filename).stem

    patterns = [
        r'^(.+?)[-_](\d+元)$',
        r'^(.+?)[-_](\d+)$',
        r'^(.+?)\s+(\d+元)$',
        r'^(.+?)\s+(\d+)$',
    ]

    for pattern in patterns:
        match = re.match(pattern, name_without_ext)
        if match:
            shoe_name = match.group(1).strip()
            price_raw = match.group(2)
            if price_raw.isdigit():
                price = f"{price_raw}元"
            else:
                price = price_raw
            return shoe_name, price

    return name_without_ext, "面议"

def scan_directory():
    """
    扫描 images 目录，返回分类结构和图片数据
    返回格式：{
        'categories': [(brand, subcategory, display_name), ...],
        'shoes': [...]
    }
    """
    categories = []  # [(品牌, 子分类, 显示名), ...]
    shoes = []
    shoe_id = 1

    images_path = Path(IMAGES_DIR)

    # 扫描有子分类的品牌（如 nike/乔一/）
    for brand_folder, brand_display in BRANDS.items():
        brand_path = images_path / brand_folder
        if not brand_path.exists():
            continue

        for subfolder in brand_path.iterdir():
            if not subfolder.is_dir():
                continue

            subcategory = subfolder.name
            display_name = subcategory

            # 扫描该子分类下的图片
            seen = {}
            for ext in IMAGE_EXTENSIONS:
                for f in subfolder.glob(f"*{ext}"):
                    key = f.name.lower()
                    if key not in seen:
                        seen[key] = f

            files = sorted(seen.values(), key=lambda f: f.stat().st_mtime, reverse=True)
            if files:
                categories.append((brand_folder, subcategory, display_name))
                print(f"[INFO] {brand_folder}/{subcategory}: {len(files)} 张图片")

                for idx, f in enumerate(files, 1):
                    shoe_name, shoe_price = parse_filename(f.name)
                    shoes.append({
                        "id": shoe_id,
                        "name": shoe_name,
                        "category": display_name,
                        "imgIndex": idx,
                        "price": shoe_price,
                        "image": f"{IMAGES_DIR}/{brand_folder}/{subcategory}/{f.name}"
                    })
                    shoe_id += 1

    # 扫描独立品牌（图片直接在品牌文件夹下）
    for brand_folder in STANDALONE_BRANDS:
        brand_path = images_path / brand_folder
        if not brand_path.exists():
            continue

        # 检查是否有子文件夹
        subfolders = [f for f in brand_path.iterdir() if f.is_dir()]
        files = []

        if not subfolders:
            # 直接是图片文件
            seen = {}
            for ext in IMAGE_EXTENSIONS:
                for f in brand_path.glob(f"*{ext}"):
                    key = f.name.lower()
                    if key not in seen:
                        seen[key] = f
            files = sorted(seen.values(), key=lambda f: f.stat().st_mtime, reverse=True)

        if files:
            display_name = brand_folder.upper() if brand_folder == "lv" else brand_folder.capitalize()
            print(f"[INFO] {brand_folder}: {len(files)} 张图片")

            for idx, f in enumerate(files, 1):
                shoe_name, shoe_price = parse_filename(f.name)
                shoes.append({
                    "id": shoe_id,
                    "name": shoe_name,
                    "category": display_name,
                    "imgIndex": idx,
                    "price": shoe_price,
                    "image": f"{IMAGES_DIR}/{brand_folder}/{f.name}"
                })
                shoe_id += 1

    return categories, shoes

def generate_nav_html(categories):
    """
    根据目录结构生成导航HTML
    """
    # 按品牌分组
    brand_categories = {}
    for brand_folder, subcategory, display_name in categories:
        if brand_folder not in brand_categories:
            brand_categories[brand_folder] = []
        if subcategory:
            brand_categories[brand_folder].append(subcategory)

    nav_buttons = []

    # 全部按钮
    nav_buttons.append('<button class="nav-btn active" data-category="all">全部</button>')

    # 品牌下拉菜单
    for brand_folder, brand_display in BRANDS.items():
        subs = brand_categories.get(brand_folder)
        if not subs:
            continue

        children = ",".join(subs)
        nav_buttons.append(f'''<div class="nav-dropdown">
          <button class="nav-btn nav-dropbtn" data-category="{brand_folder}" data-children="{children}">
            {brand_display} <span class="nav-arrow">▼</span>
          </button>
          <div class="nav-dropdown-content">''')

        for sub in subs:
            nav_buttons.append(f'<button class="nav-btn" data-category="{sub}">{sub}</button>')

        nav_buttons.append('</div>')
        nav_buttons.append('</div>')

    # 独立品牌
    for brand_folder in STANDALONE_BRANDS:
        # 检查这个品牌是否有图片
        brand_path = Path(IMAGES_DIR) / brand_folder
        if not brand_path.exists():
            continue

        has_images = False
        for ext in IMAGE_EXTENSIONS:
            if list(brand_path.glob(f"*{ext}")):
                has_images = True
                break

        if has_images:
            display_name = brand_folder.upper() if brand_folder == "lv" else brand_folder.capitalize()
            nav_buttons.append(f'<button class="nav-btn" data-category="{display_name}">{display_name}</button>')

    return "\n        ".join(nav_buttons)

def update_index_html(categories, shoes):
    """更新 index.html 中的导航和shoes数据"""
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 生成新的导航HTML
    new_nav = generate_nav_html(categories)

    # 替换导航区域（使用标记）
    start_marker = "<!-- AUTO_NAV_START -->"
    end_marker = "<!-- AUTO_NAV_END -->"

    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        print("[ERR] 未找到导航标记！请确保index.html包含 <!-- AUTO_NAV_START --> 和 <!-- AUTO_NAV_END -->")
        return False

    # 替换导航部分
    content = content[:start_idx + len(start_marker)] + "\n        " + new_nav + "\n        " + content[end_idx:]

    # 生成shoes数据
    js = "const shoes = [\n" + ",\n".join(
        f'  {{ id: {s["id"]}, name: "{s["name"]}", category: "{s["category"]}", imgIndex: {s["imgIndex"]}, price: "{s["price"]}", image: "{s["image"]}" }}'
        for s in shoes
    ) + "\n];"

    # 替换shoes数据
    content = re.sub(r'const shoes = \[.*?\];', js, content, flags=re.DOTALL)

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[OK] 已更新 {len(shoes)} 个商品")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("自动更新鞋款展示数据")
    print("=" * 50)
    categories, shoes = scan_directory()
    if not shoes:
        print("\n[ERR] 无数据！")
        print("请在 images 目录下创建分类文件夹并放入图片")
        print("\n目录结构示例：")
        print("  images/nike/乔一/黑紫脚趾-129元.jpg")
        print("  images/adidas/阿迪/白贝壳-99元.jpg")
    else:
        update_index_html(categories, shoes)
        print("\n完成！请提交到 GitHub 部署")
