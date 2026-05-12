#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
恢复图片目录结构
从之前的shoes数据恢复图片到扁平目录
"""
import os, re
from pathlib import Path
import shutil

# 工作目录
WORK_DIR = Path("C:/Users/Administrator.DESKTOP-K1RSGDC/WorkBuddy/2026-05-08-task-4")
PRODUCT_IMG = WORK_DIR / "productImg"
IMAGES_DIR = WORK_DIR / "images"

# 从git历史提取之前的shoes数据
import subprocess

def get_old_shoes_data():
    """获取之前保存的shoes数据"""
    cmd = ['git', 'show', '93e5587^:index.html']
    result = subprocess.run(cmd, cwd=WORK_DIR, capture_output=True, text=True)
    content = result.stdout

    # 提取所有图片路径
    pattern = r'"(images/[^"]+)"'
    paths = re.findall(pattern, content)
    return paths

def restore_images():
    """恢复图片到扁平目录"""
    old_paths = get_old_shoes_data()
    print(f"找到 {len(old_paths)} 条图片记录")

    restored = 0
    skipped = 0

    for old_path in old_paths:
        # old_path: images/乔一/1732096675823.jpeg
        parts = old_path.split('/')
        if len(parts) < 3:
            continue

        category = parts[1]
        filename = '/'.join(parts[2:])  # 可能包含子路径

        src = PRODUCT_IMG / filename
        dst = IMAGES_DIR / category / filename

        if src.exists():
            # 确保目标目录存在
            dst.parent.mkdir(parents=True, exist_ok=True)

            # 如果目标不存在，复制
            if not dst.exists():
                shutil.copy2(src, dst)
                restored += 1
            else:
                skipped += 1
        else:
            # 可能是新格式的路径（品牌/分类/文件名）
            # 尝试在images目录中找
            legacy_path = IMAGES_DIR / category / Path(filename).name
            if legacy_path.exists():
                # 已经恢复了
                skipped += 1
            else:
                print(f"  找不到: {src}")

    print(f"\n恢复完成: {restored} 个文件已复制，{skipped} 个已存在")

if __name__ == "__main__":
    restore_images()
