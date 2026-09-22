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
from urllib.parse import quote

# 图片走国内 CDN：CloudBase 静态托管默认域名（免备案 + 国内节点，实测 0.5s vs jsDelivr 3.17s）
CDN_BASE = "https://workbuddy-d5g0sqo2r36ca45b3-1253831416.tcloudbaseapp.com"
# 回退源：CloudBase 免费环境万一到期/超额度，前端自动切回 jsDelivr（慢但不会白图）
FALLBACK_BASE = "https://cdn.jsdelivr.net/gh/qxdz888/aj5@main"

def cdn_url(rel):
    """相对路径 -> 国内 CDN 绝对地址（中文路径做 percent-encode）"""
    if not rel:
        return ""
    if rel.startswith('http'):
        return rel
    return CDN_BASE + '/' + quote(rel, safe='/')

IMAGES_DIR = "images"
INDEX_FILE = "index.html"

# 首屏内联策略：每个分类先取前几张（保证切任何分类都有内容），再按序补足到 INLINE_TOTAL
INLINE_PER_CATEGORY = 3
INLINE_TOTAL = 80

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.JPG', '.JPEG', '.PNG', '.WEBP'}

def thumb_path(image_rel):
    """images/分类/文件.jpg -> thumbs/分类/文件.webp（列表用缩略图，弹窗才加载原图）"""
    rel = image_rel.split('/', 1)[1] if image_rel.startswith('images/') else image_rel
    stem = rel.rsplit('.', 1)[0]
    return 'thumbs/' + stem + '.webp'

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
    自动扫描 images 目录，返回两级分类结构和图片数据
    支持两级：大分类(top) / 小分类(sub)
      images/<大分类>/<小分类>/款式.webp   → top + sub
      images/<大分类>/款式.webp            → top + sub=""(直接挂大类)
    全自动识别，无需手动配置。

    返回格式：
    brands_with_subs: {大分类: [小分类列表]}   # 带下拉菜单
    standalone_brands: [大分类列表]            # 无小类，直接放图
    shoes: [商品数据列表]  (每条含 topCategory / subCategory)
    """
    brands_with_subs = {}  # {大分类: [小分类]}
    standalone_brands = []  # [大分类]
    shoes = []
    shoe_id = 1

    images_path = Path(IMAGES_DIR)

    if not images_path.exists():
        print(f"[ERR] {IMAGES_DIR} 目录不存在！")
        return brands_with_subs, standalone_brands, shoes

    # 一级文件夹 = 大分类(top)
    for top_folder in sorted(images_path.iterdir()):
        if not top_folder.is_dir():
            continue

        top_name = top_folder.name

        # 大分类下的子文件夹 = 小分类(sub)
        subfolders = sorted([f for f in top_folder.iterdir() if f.is_dir()])

        if subfolders:
            # 有子文件夹 → 大分类带下拉（小分类）
            brands_with_subs[top_name] = []
            print(f"[扫描] {top_name}/ (有{len(subfolders)}个子分类)")

            # 1) 扫描各小分类下的图片
            for subfolder in subfolders:
                subcat = subfolder.name
                brands_with_subs[top_name].append(subcat)

                seen = {}
                for ext in IMAGE_EXTENSIONS:
                    for f in subfolder.glob(f"*{ext}"):
                        key = f.name.lower()
                        if key not in seen:
                            seen[key] = f

                files = sorted(seen.values(), key=lambda f: f.stat().st_mtime, reverse=True)
                if files:
                    print(f"  [INFO] {top_name}/{subcat}: {len(files)} 张图片")

                for idx, f in enumerate(files, 1):
                    shoe_name, shoe_price, special_price = parse_filename(f.name)
                    shoes.append({
                        "id": shoe_id,
                        "name": shoe_name,
                        "category": subcat,
                        "topCategory": top_name,
                        "subCategory": subcat,
                        "imgIndex": idx,
                        "price": shoe_price,
                        "special_price": special_price,
                        "image": f"{IMAGES_DIR}/{top_name}/{subcat}/{f.name}",
                        "thumb": thumb_path(f"{IMAGES_DIR}/{top_name}/{subcat}/{f.name}")
                    })
                    shoe_id += 1

            # 2) 关键修复：大分类目录下【直接放的图】也要扫进来（sub 为空串）
            #    scan_directory 走"有子文件夹"分支时，原来会漏掉这些直接挂大类的图
            seen = {}
            for ext in IMAGE_EXTENSIONS:
                for f in top_folder.glob(f"*{ext}"):
                    key = f.name.lower()
                    if key not in seen:
                        seen[key] = f

            files = sorted(seen.values(), key=lambda f: f.stat().st_mtime, reverse=True)
            if files:
                print(f"  [INFO] {top_name}/(直接挂图): {len(files)} 张图片")
            for idx, f in enumerate(files, 1):
                shoe_name, shoe_price, special_price = parse_filename(f.name)
                shoes.append({
                    "id": shoe_id,
                    "name": shoe_name,
                    "category": top_name,
                    "topCategory": top_name,
                    "subCategory": "",
                    "imgIndex": idx,
                    "price": shoe_price,
                    "special_price": special_price,
                    "image": f"{IMAGES_DIR}/{top_name}/{f.name}",
                    "thumb": thumb_path(f"{IMAGES_DIR}/{top_name}/{f.name}")
                })
                shoe_id += 1

        else:
            # 没有子文件夹 → 独立大分类（图片直接在目录下，sub 为空串）
            standalone_brands.append(top_name)
            print(f"[扫描] {top_name}/ (独立大分类，直接放图片)")

            seen = {}
            for ext in IMAGE_EXTENSIONS:
                for f in top_folder.glob(f"*{ext}"):
                    key = f.name.lower()
                    if key not in seen:
                        seen[key] = f

            files = sorted(seen.values(), key=lambda f: f.stat().st_mtime, reverse=True)
            if files:
                print(f"  [INFO] {top_name}: {len(files)} 张图片")

            for idx, f in enumerate(files, 1):
                shoe_name, shoe_price, special_price = parse_filename(f.name)
                shoes.append({
                    "id": shoe_id,
                    "name": shoe_name,
                    "category": top_name,
                    "topCategory": top_name,
                    "subCategory": "",
                    "imgIndex": idx,
                    "price": shoe_price,
                    "special_price": special_price,
                    "image": f"{IMAGES_DIR}/{top_name}/{f.name}",
                    "thumb": thumb_path(f"{IMAGES_DIR}/{top_name}/{f.name}")
                })
                shoe_id += 1

    return brands_with_subs, standalone_brands, shoes

def generate_nav_html(brands_with_subs, standalone_brands):
    """
    根据扫描结果自动生成两级导航 HTML
    主导航 = 大分类(top)，带 data-top；有子分类时带下拉，子分类按钮带 data-top+data-sub
    """
    nav_buttons = []

    # 全部按钮（保留，兼容旧逻辑；加 data-top="all"）
    nav_buttons.append('<button class="nav-btn active" data-top="all" data-category="all">全部</button>')

    # 大分类（有子分类）→ 主导航 + 下拉子分类
    for top, subcategories in brands_with_subs.items():
        if not subcategories:
            continue

        top_display = top  # 主导航显示大分类名（原样）
        children = ",".join(subcategories)
        nav_buttons.append(f'''<div class="nav-dropdown">
      <button class="nav-btn nav-dropbtn" data-top="{top}" data-children="{children}">
        {top_display} <span class="nav-arrow">▼</span>
      </button>
      <div class="nav-dropdown-content">''')

        for sub in subcategories:
            nav_buttons.append(f'<button class="nav-btn" data-top="{top}" data-sub="{sub}">{sub}</button>')

        nav_buttons.append('</div>')
        nav_buttons.append('</div>')

    # 独立大分类（无小类，直接挂图）→ 单个按钮
    for top in standalone_brands:
        # 检查是否有图片
        top_path = Path(IMAGES_DIR) / top
        has_images = False
        for ext in IMAGE_EXTENSIONS:
            if list(top_path.glob(f"*{ext}")):
                has_images = True
                break

        if has_images:
            nav_buttons.append(f'<button class="nav-btn" data-top="{top}">{top}</button>')

    return "\n        ".join(nav_buttons)

LAZY_START = "<!-- AUTO_LAZY_START -->"
LAZY_END = "<!-- AUTO_LAZY_END -->"

LAZY_BLOCK = LAZY_START + """
    /* 首屏只内联部分数据（体积更小、渲染更快），全量数据后台静默加载 */
    let allLoaded = false;
    async function loadAllShoes() {
      try {
        const res = await fetch('manifest.json?t=' + Date.now());
        const data = await res.json();
        const known = new Set(shoes.map(s => s.id));
        const strip = u => (u || '').replace(/^https?:\\/\\/aj5\\.netlify\\.app\\//, '');
        const add = (data.shoes || [])
          .filter(s => !known.has(s.id))
          .map(s => Object.assign({}, s, {
            image: strip(s.image),
            thumb: strip(s.thumb)
          }));
        if (add.length) shoes.push(...add);
        allLoaded = true;
        if (currentSearchTerm) {
          performSearch(searchInput.value);
        } else if (currentCategory !== 'all') {
          renderGallery(currentCategory);
        } else {
          const box = document.getElementById('loadMoreContainer');
          if (box) box.style.display = displayCount < filteredShoes.length ? 'block' : 'none';
        }
        console.log('[aj5] 全量数据就绪：' + shoes.length + ' 件');
      } catch (e) {
        console.warn('[aj5] 全量数据加载失败，仅显示首屏数据', e);
      }
    }
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', loadAllShoes);
    } else {
      setTimeout(loadAllShoes, 0);
    }
    """ + LAZY_END

def build_inline(shoes):
    """首屏内联数据：每大分类前 N 张（保证切换任意分类都有内容）+ 按序补足"""
    picked, seen = [], set()
    by_cat = {}
    for s in shoes:
        by_cat.setdefault(s["topCategory"], []).append(s)
    for cat in sorted(by_cat):
        for s in by_cat[cat][:INLINE_PER_CATEGORY]:
            if s["id"] not in seen:
                picked.append(s)
                seen.add(s["id"])
    for s in shoes:
        if len(picked) >= INLINE_TOTAL:
            break
        if s["id"] not in seen:
            picked.append(s)
            seen.add(s["id"])
    return picked

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

    # 生成 shoes 数据：仅内联首屏部分（其余后台从 manifest.json 加载）
    inline = build_inline(shoes)
    js = "const shoes = [\n" + ",\n".join(
        f'  {{ id: {s["id"]}, name: "{s["name"]}", category: "{s["category"]}", topCategory: "{s["topCategory"]}", subCategory: "{s["subCategory"]}", imgIndex: {s["imgIndex"]}, price: "{s["price"]}", specialPrice: "{s.get("special_price", "")}", image: "{cdn_url(s["image"])}", thumb: "{cdn_url(s.get("thumb", ""))}" }}'
        for s in inline
    ) + "\n];"

    # 替换shoes数据
    content = re.sub(r'const shoes = \[.*?\];', js, content, flags=re.DOTALL)

    # 注入/更新后台全量加载逻辑（幂等，重复运行不会叠加）
    ls, le = content.find(LAZY_START), content.find(LAZY_END)
    if ls != -1 and le != -1:
        content = content[:ls] + LAZY_BLOCK + content[le + len(LAZY_END):]
    else:
        pos = content.find(js)
        if pos == -1:
            print("[WARN] 未定位到内联 shoes 数据，跳过懒加载注入")
        else:
            content = content[:pos + len(js)] + "\n\n    " + LAZY_BLOCK + content[pos + len(js):]

    # head 预取 manifest.json（只加一次）
    if 'rel="prefetch" href="manifest.json"' not in content:
        content = content.replace(
            '</head>',
            '  <link rel="prefetch" href="manifest.json">\n</head>', 1
        )

    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    import os
    print(f"[OK] 首屏内联 {len(inline)} 件（HTML {os.path.getsize(INDEX_FILE)/1024:.0f}KB），全量 {len(shoes)} 件后台加载")

    # 同时生成 manifest.json（供 520aj 等子站自动同步图片）
    import json
    manifest = {
        "generated_at": __import__('datetime').datetime.now().isoformat(),
        "base_url": CDN_BASE,
        "shoes": shoes
    }
    # 把 image 字段改成完整 URL
    for s in manifest["shoes"]:
        s["image"] = cdn_url(s["image"])
        if s.get("thumb"):
            s["thumb"] = cdn_url(s["thumb"])

    with open("manifest.json", 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[OK] 已生成 manifest.json（{len(shoes)} 个商品）")

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
