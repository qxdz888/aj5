#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto-update shoes gallery data based on images in images/ directory
"""

import os
import re
from pathlib import Path

# Configuration
IMAGES_DIR = "images"
INDEX_FILE = "index.html"

# Category display names and order
# Using Unicode escapes to avoid encoding issues on Linux runners
CATEGORIES = [
    ("\u4e54\u4e00", "\u4e54\u4e00"),           # 涔斾竴
    ("\u7a7a\u519b", "\u7a7a\u519b"),           # 绌哄啗
    ("\u5c0f\u7a7a\u519b", "\u5c0f\u7a7a\u519b"), # 灏忕┖鍐?    ("\u5f00\u62d3\u8005", "\u5f00\u62d3\u8005"), # 寮€鎷撹€?    ("\u963f\u8fea", "\u963f\u8fea"),             # 闃胯开
    ("\u5f6a\u9a6c", "\u5f6a\u9a6c"),             # 褰┈
    ("wans", "wans"),
    ("lv", "lv"),
]

# Supported image extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.JPG', '.JPEG', '.PNG', '.WEBP'}

def scan_images():
    """Scan images directory and return shoes data"""
    shoes = []
    shoe_id = 1
    
    for category_en, category_cn in CATEGORIES:
        category_path = Path(IMAGES_DIR) / category_en
        
        if not category_path.exists():
            print(f"[WARN] Category directory not found: {category_path}")
            continue
        
        # Get all image files in this category
        image_files = []
        for ext in IMAGE_EXTENSIONS:
            image_files.extend(category_path.glob(f"*{ext}"))
        
        # Sort images by filename
        image_files.sort()
        
        if not image_files:
            print(f"[WARN] No images found in category: {category_en}")
            continue
        
        print(f"[INFO] Category '{category_en}': found {len(image_files)} images")
        
        # Create shoe entries for each image
        for img_index, img_path in enumerate(image_files, start=1):
            shoe = {
                "id": shoe_id,
                "name": f"{category_cn} #{img_index}",
                "category": category_cn,
                "imgIndex": img_index,
                "price": "\u9762\u8bae",  # 闈㈣
                "image": f"{IMAGES_DIR}/{category_en}/{img_path.name}"
            }
            shoes.append(shoe)
            shoe_id += 1
    
    return shoes

def generate_shoes_js(shoes):
    """Generate JavaScript shoes array"""
    lines = ["const shoes = ["]
    
    for i, shoe in enumerate(shoes):
        line = f"  {{ id: {shoe['id']}, name: \"{shoe['name']}\", category: \"{shoe['category']}\", imgIndex: {shoe['imgIndex']}, price: \"{shoe['price']}\", image: \"{shoe['image']}\" }}"
        if i < len(shoes) - 1:
            line += ","
        lines.append(line)
    
    lines.append("];")
    return "\n".join(lines)

def update_index_html(shoes_js):
    """Update index.html with new shoes data"""
    with open(INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace the shoes array using regex
    pattern = r'const shoes = \[.*?\];'
    replacement = shoes_js
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    if new_content == content:
        print("[WARN] No changes made to index.html (pattern not found or no change)")
        return False
    
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"[SUCCESS] Updated index.html with {len(shoes_js.split(chr(10)))} shoes")
    return True

def main():
    print("[INFO] Starting shoes gallery update...")
    
    # Scan images
    shoes = scan_images()
    
    if not shoes:
        print("[ERROR] No shoes data generated. Exiting.")
        return
    
    print(f"[INFO] Generated {len(shoes)} shoe entries")
    
    # Generate JS
    shoes_js = generate_shoes_js(shoes)
    
    # Update HTML
    success = update_index_html(shoes_js)
    
    if success:
        print("[SUCCESS] Gallery update complete!")
    else:
        print("[WARN] Gallery update incomplete")

if __name__ == "__main__":
    main()
