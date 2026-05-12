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
CATEGORIES = [
    ("涔斾竴", "涔斾竴"),
    ("绌哄啗", "绌哄啗"),
    ("灏忕┖鍐?, "灏忕┖鍐?),
    ("寮€鎷撹€?, "寮€鎷撹€?),
    ("闃胯开", "闃胯开"),
    ("褰┈", "褰┈"),
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
            print(f"鈿狅笍  Category directory not found: {category_path}")
            continue
        
        # Get all image files in this category
        image_files = []
        for ext in IMAGE_EXTENSIONS:
            image_files.extend(category_path.glob(f"*{ext}"))
        
        # Sort images by filename
        image_files.sort()
        
        if not image_files:
            print(f"鈿狅笍  No images found in category: {category_en}")
            continue
        
        print(f"馃搧 Category '{category_en}': found {len(image_files)} images")
        
        # Create shoe entries for each image
        for img_index, img_path in enumerate(image_files, start=1):
            shoe = {
                "id": shoe_id,
                "name": f"{category_cn} #{img_index}",
                "category": category_cn,
                "imgIndex": img_index,
                "price": "闈㈣",
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
        print("鈿狅笍  No changes made to index.html (pattern not found or no change)")
        return False
    
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"鉁?Updated index.html with {len(shoes_js.split(chr(10)))} shoes")
    return True

def main():
    print("馃殌 Starting shoes gallery update...")
    
    # Scan images
    shoes = scan_images()
    
    if not shoes:
        print("鉂?No shoes data generated. Exiting.")
        return
    
    print(f"馃搳 Generated {len(shoes)} shoe entries")
    
    # Generate JS
    shoes_js = generate_shoes_js(shoes)
    
    # Update HTML
    success = update_index_html(shoes_js)
    
    if success:
        print("鉁?Gallery update complete!")
    else:
        print("鈿狅笍  Gallery update incomplete")

if __name__ == "__main__":
    main()
