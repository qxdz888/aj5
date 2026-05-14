#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动更新球鞋展示数据
扫描 images 目录结构，自动生成导航菜单和图片数据

【全自动识别】
- 自动扫描 images/ 下所有文件夹
- 如果文件夹有子文件夹 → 生成下拉菜单（如 nike/乔一/）
- 如果文件夹直接放图片 → 生成单个按钮（如 puma/）
- 无需手动配置，添加/删除文件夹后直接运行即可

使用说明：
1. 在 images/ 目录下创建品牌文件夹
2. 如果品牌有多个分类，创建子文件夹
3. 把图片放到对应位置，文件名格式：款式-价格元.jpg
4. 运行此脚本，自动更新 index.html

目录结构示例：
images/
├── nike/           ← 有子文件夹，生成下拉菜单
│   ├── 乔一/       ← 放图片
│   └── 空军/       ← 放图片
├── adidas/         ← 有子文件夹，生成下拉菜单
│   ├── 德训/       ← 放图片
│   └── 贝壳头/     ← 放图片
├── puma/           ← 直接放图片，生成单个按钮
└── wans/           ← 直接放图片，生成单个按钮
"""
import os, re
from pathlib import Path

IMAGES_DIR = "images"
INDEX_FILE = "index.html"

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

            # 计算特惠价（固定129元）
            special_price = "129元"

            return shoe_name, price, special_price

    return name_without_ext, "面议", ""

def scan_directory():
    """
    自动扫描 images 目录，返回分类结构和图片数据
    全自动识别所有品牌文件夹，无需手动配置

    返回格式：
    brands_with_subs: {品牌文件夹名: [子分类列表]}
    standalone_brands: [品牌文件夹名列表]  # 直接放图片的
    shoes: [商品数据列表]
    """
    brands_with_subs = {}  # {品牌: [子分类]}
    standalone_brands = []  # [品牌]
    shoes = []
    shoe_id = 1

    images_path = Path(IMAGES_DIR)

    if not images_path.exists():
        print(f"[ERR] {IMAGES_DIR} 目录不存在！")
        return brands_with_subs, standalone_brands, shoes

    # 扫描 images/ 下的所有文件夹
    for brand_folder in sorted(images_path.iterdir()):
        if not brand_folder.is_dir():
            continue

        brand_name = brand_folder.name

        # 检查是否有子文件夹
        subfolders = sorted([f for f in brand_folder.iterdir() if f.is_dir()])

        if subfolders:
            # 有子文件夹 → 作为"品牌-子分类"结构
            brands_with_subs[brand_name] = []
            print(f"[扫描] {brand_name}/ (有{len(subfolders)}个子分类)")

            for subfolder in subfolders:
                subcategory = subfolder.name
                brands_with_subs[brand_name].append(subcategory)

                # 扫描该子分类下的图片
                seen = {}
                for ext in IMAGE_EXTENSIONS:
                    for f in subfolder.glob(f"*{ext}"):
                        key = f.name.lower()
                        if key not in seen:
                            seen[key] = f

                files = sorted(seen.values(), key=lambda f: f.stat().st_mtime, reverse=True)
                if files:
                    print(f"  [INFO] {brand_name}/{subcategory}: {len(files)} 张图片")

                    for idx, f in enumerate(files, 1):
                        shoe_name, shoe_price, special_price = parse_filename(f.name)
                        shoes.append({
                            "id": shoe_id,
                            "name": shoe_name,
                            "category": subcategory,
                            "imgIndex": idx,
                            "price": shoe_price,
                            "special_price": special_price,
                            "image": f"{IMAGES_DIR}/{brand_name}/{subcategory}/{f.name}"
                        })
                        shoe_id += 1

        else:
            # 没有子文件夹 → 作为独立品牌（图片直接在品牌文件夹下）
            standalone_brands.append(brand_name)
            print(f"[扫描] {brand_name}/ (独立品牌，直接放图片)")

            # 扫描该文件夹下的图片
            seen = {}
            for ext in IMAGE_EXTENSIONS:
                for f in brand_folder.glob(f"*{ext}"):
                    key = f.name.lower()
                    if key not in seen:
                        seen[key] = f

            files = sorted(seen.values(), key=lambda f: f.stat().st_mtime, reverse=True)
            if files:
                display_name = brand_name.upper() if brand_name == "lv" else brand_name.capitalize()
                print(f"  [INFO] {brand_name}: {len(files)} 张图片")

                for idx, f in enumerate(files, 1):
                    shoe_name, shoe_price, special_price = parse_filename(f.name)
                    shoes.append({
                        "id": shoe_id,
                        "name": shoe_name,
                        "category": display_name,
                        "imgIndex": idx,
                        "price": shoe_price,
                        "special_price": special_price,
                        "image": f"{IMAGES_DIR}/{brand_name}/{f.name}"
                    })
                    shoe_id += 1

    return brands_with_subs, standalone_brands, shoes

def generate_nav_html(brands_with_subs, standalone_brands):
    """
    根据扫描结果自动生成导航HTML
    """
    nav_buttons = []

    # 全部按钮
    nav_buttons.append('<button class="nav-btn active" data-category="all">全部</button>')

    # 有子分类的品牌 → 下拉菜单
    for brand_folder, subcategories in brands_with_subs.items():
        if not subcategories:
            continue

        # 品牌显示名（首字母大写）
        brand_display = brand_folder.capitalize()

        children = ",".join(subcategories)
        nav_buttons.append(f'''<div class="nav-dropdown">
          <button class="nav-btn nav-dropbtn" data-category="{brand_folder}" data-children="{children}">
            {brand_display} <span class="nav-arrow">▼</span>
          </button>
          <div class="nav-dropdown-content">''')

        for sub in subcategories:
            nav_buttons.append(f'<button class="nav-btn" data-category="{sub}">{sub}</button>')

        nav_buttons.append('</div>')
        nav_buttons.append('</div>')

    # 独立品牌 → 单个按钮
    for brand_folder in standalone_brands:
        # 检查是否有图片
        brand_path = Path(IMAGES_DIR) / brand_folder
        has_images = False
        for ext in IMAGE_EXTENSIONS:
            if list(brand_path.glob(f"*{ext}")):
                has_images = True
                break

        if has_images:
            display_name = brand_folder.upper() if brand_folder == "lv" else brand_folder.capitalize()
            nav_buttons.append(f'<button class="nav-btn" data-category="{display_name}">{display_name}</button>')

    return "\n        ".join(nav_buttons)

def update_index_html(brands_with_subs, standalone_brands, shoes):
    """更新 index.html 中的导航和shoes数据"""
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 生成新的导航HTML
    new_nav = generate_nav_html(brands_with_subs, standalone_brands)

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
        f'  {{ id: {s["id"]}, name: "{s["name"]}", category: "{s["category"]}", imgIndex: {s["imgIndex"]}, price: "{s["price"]}", specialPrice: "{s.get("special_price", "")}", image: "{s["image"]}" }}'
        for s in shoes
    ) + "\n];"

    # 替换shoes数据
    content = re.sub(r'const shoes = \[.*?\];', js, content, flags=re.DOTALL)

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[OK] 已更新 {len(shoes)} 个商品")
    print(f"[OK] 导航品牌：{len(brands_with_subs)} 个下拉菜单 + {len(standalone_brands)} 个独立按钮")
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("自动更新鞋款展示数据")
    print("=" * 50)
    print("【全自动模式】扫描 images/ 下所有文件夹...\n")

    brands_with_subs, standalone_brands, shoes = scan_directory()

    if not shoes:
        print("\n[ERR] 无数据！")
        print("请在 images 目录下创建品牌文件夹并放入图片")
        print("\n目录结构示例：")
        print("  images/nike/乔一/黑紫脚趾-129元.jpg  ← 有子分类")
        print("  images/puma/休闲鞋-169元.jpg          ← 无子分类")
    else:
        print(f"\n扫描完成：{len(brands_with_subs)} 个品牌(有子分类) + {len(standalone_brands)} 个独立品牌")
        update_index_html(brands_with_subs, standalone_brands, shoes)
        print("\n完成！请提交到 GitHub 部署")
