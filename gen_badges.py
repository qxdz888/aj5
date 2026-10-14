# -*- coding: utf-8 -*-
"""
生成商品角标 badges.json（新款/热销）
数据源：销售软件 clothing.db
  - 新款：goods.create_at 最新的 30 个线上在售款式
  - 热销：sale_items 累计销量（SUM qty）最高的 40 个线上在售款式
输出：badges.json  {"<名称>|<价格整数>": "new"|"hot", ...}
由 update_gallery.py 在 build manifest 时合并进每项商品数据。
"""
import json
import sqlite3
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = r'D:\zgzn-common\Programs\clothing-13638000210-1\data\clothing.db'
MANIFEST = BASE / 'manifest.json'
BADGES = BASE / 'badges.json'
NEW_N, HOT_N = 30, 40


def main():
    if not MANIFEST.exists():
        print('[ERR] manifest.json 不存在，先跑 update_gallery.py')
        return
    shoes = json.load(open(MANIFEST, encoding='utf-8'))['shoes']

    # 线上商品 (name, price_int) -> id；price 形如 "189元"
    online = {}
    for s in shoes:
        p = s['price'].replace('元', '')
        online[(s['name'], int(p))] = s['id'] if p.isdigit() else None

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # 按 name 聚合：最新 create_at（仅未删除记录）、库存合计
    cur.execute("SELECT name, create_at, cur_stock, is_deleted FROM goods WHERE name IS NOT NULL")
    name_ctime, name_stock = {}, defaultdict(float)
    for name, ctime, stock, deleted in cur.fetchall():
        name_stock[name] += stock or 0
        if not deleted and ctime and ctime > name_ctime.get(name, ''):
            name_ctime[name] = ctime

    # 按 name 聚合累计销量（含已删商品的历史单，避免丢销量）
    cur.execute("""SELECT g.name, SUM(si.qty) FROM sale_items si
                   JOIN goods g ON g.fingerprint = si.good_fingerprint
                   WHERE si.is_deleted = 0 GROUP BY g.name""")
    sales = {n: q or 0 for n, q in cur.fetchall() if n}
    conn.close()

    # 新款：create_at 最新 30 款（线上在售）
    new_rank = sorted(
        ((name_ctime[n], n, p) for (n, p) in online if n in name_ctime),
        reverse=True)[:NEW_N]

    # 热销：累计销量前 40 款（线上在售）
    hot_rank = sorted(
        ((sales.get(n, 0), n, p) for (n, p) in online),
        reverse=True)[:HOT_N]

    badges = {}
    for _, n, p in new_rank:
        badges[f'{n}|{p}'] = 'new'
    for _, n, p in hot_rank:
        badges.setdefault(f'{n}|{p}', 'hot')  # 新款优先，不覆盖

    out = {
        'generated_at': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M'),
        'new_count': NEW_N,
        'hot_count': HOT_N,
        'badges': badges,
    }
    json.dump(out, open(BADGES, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    n_new = sum(1 for v in badges.values() if v == 'new')
    n_hot = sum(1 for v in badges.values() if v == 'hot')
    print(f'[OK] badges.json：新款 {n_new} + 热销 {n_hot} = {len(badges)} 款')
    for t, n, p in new_rank[:5]:
        print(f'  新款 {t[:10]} {n}-{p}')
    top = sorted(hot_rank, key=lambda x: -x[0])[:5]
    for q, n, p in top:
        print(f'  热销 {q:g}双 {n}-{p}')


if __name__ == '__main__':
    main()
