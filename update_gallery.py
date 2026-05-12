#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动更新球鞋展示数据
扫描 images 目录结构，自动生成导航菜单和图片数据

使用说明：
1. 在 images/ 目录下按分类创建文件夹（扁平结构）
2. 把图片放到对应分类文件夹，文件名格式：款式-价格元.jpg
3. 运行此脚本，自动更新 index.html

目录结构示例（扁平）：
images/
├── 乔一/          ← 放图片
├── 空军/          ← 放图片
├── 阿迪/          ← 放图片
├── 彪马/          ← 放图片
├── lv/            ← 放图片
└── wans/          ← 放图片
"""
import os, re
from pathlib import Path

IMAGES_DIR = "images"
INDEX_FILE = "index.html"

# 分类显示名称映射
CATEGORY_NAMES = {
    "乔一": "乔一",
    "空军": "空军",
    "小空军": "小空军",
    "开拓者": "开拓者",
    "阿迪": "Adidas",
    "彪马": "Puma",
    "lv": "LV",
    "wans": "Wans"
}

# Nike子分类（这些分类属于Nike品牌）
NIKE_CATEGORIES = ["乔一", "空军", "小空军", "开拓者", "高帮"]

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
    扫描 images 目录，返回分类结构和图片数据（扁平结构）
    返回格式：{
        'categories': [(category, display_name), ...],
        'shoes': [...]
    }
    """
    categories = []  # [(分类名, 显示名), ...]
    shoes = []
    shoe_id = 1

    images_path = Path(IMAGES_DIR)
    if not images_path.exists():
        print("[ERR] images 目录不存在！")
        return categories, shoes

    # 扫描扁平目录结构
    for category_folder in images_path.iterdir():
        if not category_folder.is_dir():
            continue

        category_name = category_folder.name
        display_name = CATEGORY_NAMES.get(category_name, category_name)

        # 扫描该分类下的图片
        seen = {}
        for ext in IMAGE_EXTENSIONS:
            for f in category_folder.glob(f"*{ext}"):
                key = f.name.lower()
                if key not in seen:
                    seen[key] = f

        files = sorted(seen.values())
        if files:
            categories.append((category_name, display_name))
            print(f"[INFO] {category_name}: {len(files)} 张图片")

            for idx, f in enumerate(files, 1):
                shoe_name, shoe_price = parse_filename(f.name)
                shoes.append({
                    "id": shoe_id,
                    "name": shoe_name,
                    "category": category_name,
                    "categoryDisplay": display_name,
                    "imgIndex": idx,
                    "price": shoe_price,
                    "image": f"{IMAGES_DIR}/{category_name}/{f.name}"
                })
                shoe_id += 1

    return categories, shoes

def generate_nav_html(categories):
    """
    根据目录结构生成导航HTML
    """
    nav_buttons = []

    # 全部按钮
    nav_buttons.append('<button class="nav-btn active" data-category="all">全部</button>')

    # Nike下拉菜单
    nike_cats = [(c, d) for c, d in categories if c in NIKE_CATEGORIES]
    if nike_cats:
        children = ",".join([c for c, d in nike_cats])
        nav_buttons.append(f'''<div class="nav-dropdown">
          <button class="nav-btn nav-dropbtn" data-category="nike" data-children="{children}">
            Nike <span class="nav-arrow">▼</span>
          </button>
          <div class="nav-dropdown-content">''')

        for cat, display in nike_cats:
            nav_buttons.append(f'<button class="nav-btn" data-category="{cat}">{display}</button>')

        nav_buttons.append('</div>')
        nav_buttons.append('</div>')

    # 其他分类（阿迪、彪马、lv、wans等）
    for cat, display in categories:
        if cat in NIKE_CATEGORIES:
            continue
        nav_buttons.append(f'<button class="nav-btn" data-category="{cat}">{display}</button>')

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
    print("自动更新鞋款展示数据（扁平目录结构）")
    print("=" * 50)
    categories, shoes = scan_directory()
    if not shoes:
        print("\n[ERR] 无数据！")
        print("请在 images 目录下创建分类文件夹并放入图片")
        print("\n目录结构示例：")
        print("  images/乔一/黑紫脚趾-129元.jpg")
        print("  images/空军/白空军-159元.jpg")
    else:
        update_index_html(categories, shoes)
        print("\n完成！请提交到 GitHub 部署")
