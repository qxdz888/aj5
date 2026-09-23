# -*- coding: utf-8 -*-
"""
移动端「两套新日常版式」幂等补丁
=================================
在 _mobile_patch.py 之后执行，为 aj5 球鞋站增加：

  主题轴（已有，不动）  : 日常 / 节日        -> body.festival-mode
  版式轴（本补丁新增）  : 标准 / 货架 / 清单  -> body.layout-std|layout-shelf|layout-list

设计规格：ai/memory-bank/design/mobile-ui-variants-spec.md

纠偏记录（评审拦下的两处规格缺陷）：
  1) 规格把清单版价格硬编码为近黑 #111418 —— 节日暗红底上会变黑字看不见。
     已改为节日下 --v-price: var(--m-text)、--v-promo: var(--m-accent)。
  2) 规格把货架版 --v-accent 硬编码墨黑 —— 节日金主题被顶掉。
     已补 body.layout-*.festival-mode 的令牌让位规则。

范围控制（刻意不做，避免蔓延）：
  · 分组吸顶标题（P1）
  · 搜索筛选 chips（P1）
  · 行内询价按钮（P1）
"""
import re
import shutil
from datetime import datetime
from pathlib import Path

BASE = Path(r"C:\Users\Administrator.DESKTOP-K1RSGDC\WorkBuddy\2026-05-08-task-4")
INDEX = BASE / "index.html"
BACKUP = BASE / "_sync_backup"

MARK_CSS = "/* ==== UI-VARIANTS PATCH CSS START ==== */"
MARK_CSS_END = "/* ==== UI-VARIANTS PATCH CSS END ==== */"
MARK_HTML = "<!-- ==== UI-VARIANTS PATCH HTML START ==== -->"
MARK_HTML_END = "<!-- ==== UI-VARIANTS PATCH HTML END ==== -->"
MARK_SORT = "<!-- ==== UI-VARIANTS SORTBAR START ==== -->"
MARK_SORT_END = "<!-- ==== UI-VARIANTS SORTBAR END ==== -->"
MARK_JS = "/* ==== UI-VARIANTS PATCH JS START ==== */"
MARK_JS_END = "/* ==== UI-VARIANTS PATCH JS END ==== */"


def already_patched(html: str) -> bool:
    return ("--v-page" in html) and ('id="uiVarSheet"' in html) and ("initUiVariants" in html)


def _replace_region(html: str, start_mark: str, end_mark: str, new_block: str):
    """有旧块就整段替换，没有就返回 None 让调用方走插入逻辑（保证幂等且可迭代）"""
    i = html.find(start_mark)
    if i < 0:
        return None
    j = html.find(end_mark, i)
    if j < 0:
        return None
    j += len(end_mark)
    if html[i:j] == new_block:
        return html  # 内容一致，无需改
    return html[:i] + new_block + html[j:]


# ═════════════════════════════════ CSS ═════════════════════════════════
CSS_BLOCK = MARK_CSS + r"""
    /* ============================================================
       13. 版式轴（脚本补丁注入）：标准 / 货架 / 清单
           --m-*  由主题决定（日常/节日），勿在本段修改
           --v-*  由版式决定，仅 layout-shelf / layout-list 定义
       ============================================================ */

    /* ---- 13.1 微信浏览器底座 ---- */
    html {
      -webkit-text-size-adjust: 100%;
      text-size-adjust: 100%;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Helvetica Neue",
                   "Hiragino Sans GB", "Microsoft YaHei", "Source Han Sans SC",
                   "Noto Sans CJK SC", sans-serif;
      overscroll-behavior-y: contain;
      -webkit-tap-highlight-color: transparent;
      /* 刻意不写 user-select:none —— 顾客需要长按保存鞋子图 */
    }
    body.sheet-locked { overscroll-behavior: contain; }
    .card-price, .card-badge { font-variant-numeric: tabular-nums; }

    /* 可选节点：默认全隐藏，只在对应版式里打开（保证标准版零回归） */
    .card-badge { display: none; }
    #sortBar    { display: none; }

    /* ---- 13.2 版式共享令牌 ---- */
    body.layout-shelf, body.layout-list {
      --v-media: #f0f1f4;
    }

    /* ============================================================
       13.3 版式 B · 货架版  body.layout-shelf
            主打「逛 + 快速决策」：冷灰底 + 白圆角大卡 + 橙价
       ============================================================ */
    body.layout-shelf {
      --v-page:     #f5f5f7;
      --v-card:     #ffffff;
      --v-text:     #16181d;
      --v-text-sub: #8a8f99;
      --v-line:     #eceef2;
      --v-accent:   #16181d;
      --v-price:    #e05200;   /* 电商橙；对白底对比度 3.91（#ff6a00 仅 2.87 偏浅，已校正） */
      --v-was:      #9aa0aa;
      --v-shadow:   0 1px 2px rgba(16, 24, 40, .04), 0 6px 16px rgba(16, 24, 40, .06);
    }
    /* 节日主题下让位给 --m-*（否则墨黑/橙 与暗红金 打架） */
    body.layout-shelf.festival-mode {
      --v-page:     var(--m-bg);
      --v-card:     var(--m-surface);
      --v-text:     var(--m-text);
      --v-text-sub: var(--m-text-sub);
      --v-line:     var(--m-line);
      --v-accent:   var(--m-accent);
      --v-price:    var(--m-accent);
      --v-was:      var(--m-text-sub);
    }

    @media (max-width: 768px) {
      body.layout-shelf {
        background: var(--v-page) !important;
        padding-bottom: calc(56px + env(safe-area-inset-bottom, 0px)) !important;
      }
      /* navbar 已改为 sticky（占文档流），清掉原 fixed 时代的 banner 占位，消除顶部双份空隙（P1） */
      body.layout-shelf .banner { margin-top: 0 !important; }
      body.layout-shelf .page-content { padding-top: 0 !important; }

      /* 顶部：粘顶 + 不透明底（微信安卓 X5 不支持 backdrop-filter） */
      body.layout-shelf .navbar {
        position: sticky !important;
        top: 0; left: 0; right: 0;
        padding: 0 12px !important;
        background: var(--v-card) !important;
        border-bottom: 1px solid var(--v-line) !important;
        box-shadow: 0 1px 2px rgba(16, 24, 40, .04) !important;
        -webkit-backdrop-filter: none !important;
        backdrop-filter: none !important;
        z-index: 100;
      }
      body.layout-shelf .nav-content { padding: 8px 0 0 !important; }
      body.layout-shelf .logo {
        font-size: 13px !important;
        letter-spacing: .5px !important;
        color: var(--v-text) !important;
        background: none !important;
        -webkit-text-fill-color: currentColor !important;
        background-clip: border-box !important;
      }
      body.layout-shelf .search-container { flex: 1 1 auto; min-width: 0; }
      body.layout-shelf .search-input {
        width: 100% !important;
        height: 38px !important;
        border-radius: 999px !important;
        background: #f2f3f5 !important;
        border: 1px solid transparent !important;
        color: var(--v-text) !important;
        font-size: 14px !important;
        padding: 0 14px 0 36px !important;
      }
      body.layout-shelf .search-input::placeholder { color: var(--v-text-sub) !important; }
      body.layout-shelf .search-input:focus { background: #fff !important; border-color: var(--v-accent) !important; }
      body.layout-shelf .search-icon {
        left: 12px !important; right: auto !important;
        color: var(--v-text-sub) !important; font-size: 15px !important;
      }

      /* 一级分类：横滑胶囊 */
      body.layout-shelf .nav-bottom-row {
        margin: 8px -12px 0 !important;
        padding: 0 12px 8px !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
      }
      body.layout-shelf .nav-bottom-row::-webkit-scrollbar { display: none; }
      body.layout-shelf .nav-links { display: flex !important; flex-wrap: nowrap !important; gap: 8px !important; }
      body.layout-shelf .nav-btn {
        position: relative;
        flex: 0 0 auto !important;
        height: 34px !important;
        padding: 0 14px !important;
        border-radius: 999px !important;
        background: var(--v-card) !important;
        border: 1px solid var(--v-line) !important;
        color: var(--v-text) !important;
        font-size: 13px !important;
        white-space: nowrap !important;
      }
      body.layout-shelf .nav-btn::after {
        content: ''; position: absolute; left: 0; right: 0; top: -5px; bottom: -5px;
      }
      body.layout-shelf .nav-btn.active {
        background: var(--v-accent) !important;
        border-color: var(--v-accent) !important;
        color: #fff !important;
        font-weight: 600;
      }
      body.layout-shelf.festival-mode .nav-btn.active { color: #1a0508 !important; }
      body.layout-shelf .nav-arrow { font-size: 9px; opacity: .55; }
      body.layout-shelf .nav-dropdown { position: static !important; }
      body.layout-shelf .nav-dropdown-content { display: none !important; }

      /* 网格与卡片 */
      body.layout-shelf .gallery {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 10px !important;
        padding: 10px 12px 16px !important;
      }
      body.layout-shelf .card {
        display: block !important;
        position: relative;
        background: var(--v-card) !important;
        border: none !important;
        border-radius: 16px !important;
        box-shadow: var(--v-shadow) !important;
        overflow: hidden !important;
        transform: none !important;
      }
      body.layout-shelf .card:active { background: #fafbfc; }
      body.layout-shelf .card-image {
        width: 100% !important;
        aspect-ratio: 1 / 1;
        height: auto !important;
        object-fit: cover !important;
        display: block;
        background: var(--v-media);
      }
      @supports not (aspect-ratio: 1 / 1) {
        body.layout-shelf .card-image { height: 0 !important; padding-top: 100%; }
      }
      body.layout-shelf .card-info { padding: 10px 10px 11px !important; }
      body.layout-shelf .card-name {
        font-size: 13px !important;
        line-height: 1.35 !important;
        font-weight: 600;
        color: var(--v-text) !important;
        min-height: 36px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      body.layout-shelf .card-price {
        display: block !important;
        margin-top: 6px !important;
        font-size: 18px !important;
        font-weight: 800;
        line-height: 1.15;
        color: var(--v-price) !important;
      }
      body.layout-shelf .card-price .special-price {
        font-size: 18px !important; font-weight: 800; color: var(--v-price) !important;
      }
      body.layout-shelf .card-price .price-origin,
      body.layout-shelf .card-price .original-price {
        display: block !important;
        font-size: 12px !important; font-weight: 400;
        color: var(--v-was) !important; margin: 0 0 2px 0 !important;
      }
      body.layout-shelf .card-category {
        display: block !important;
        margin: 3px 0 0 !important;
        padding: 0 !important;
        background: none !important;
        border: none !important;
        font-size: 11px !important;
        line-height: 14px !important;
        color: var(--v-text-sub) !important;
      }

      /* 角标 chip */
      body.layout-shelf .card-badge {
        display: inline-flex !important;
        align-items: center;
        position: absolute; left: 8px; top: 8px; z-index: 2;
        height: 18px; padding: 0 6px;
        border-radius: 4px;
        font-size: 10px; font-weight: 600; line-height: 1;
      }
      body.layout-shelf .card-badge--fixed { color: #16181d; background: rgba(22, 24, 29, .09); }
      body.layout-shelf .card-badge--hot   { color: #e05200; background: rgba(224, 82, 0, .13); }
      body.layout-shelf.festival-mode .card-badge--fixed { color: var(--m-accent); background: rgba(232, 196, 106, .15); }
      body.layout-shelf.festival-mode .card-badge--hot   { color: var(--m-accent); background: rgba(232, 196, 106, .15); }

      /* 底部栏 */
      body.layout-shelf .bottom-bar {
        position: fixed !important;
        left: 0; right: 0; bottom: 0; top: auto !important;
        height: 56px;
        display: flex !important;
        align-items: stretch;
        background: rgba(255, 255, 255, .98) !important;
        border-top: 1px solid var(--v-line) !important;
        border-radius: 0 !important;
        box-shadow: 0 -1px 0 rgba(16, 24, 40, .04) !important;
        -webkit-backdrop-filter: none !important;
        backdrop-filter: none !important;
        padding: 0 0 env(safe-area-inset-bottom, 0px) !important;
        z-index: 190;
        transform: none !important;
      }
      body.layout-shelf.festival-mode .bottom-bar {
        background: rgba(26, 6, 9, .98) !important;
      }
      body.layout-shelf .bottom-bar-recruitment { display: none !important; }
      /* :not() 排除招商入口：否则与上一条同为 (0,2,0)+!important，按声明顺序 flex 会盖掉 none（P1） */
      body.layout-shelf .bottom-bar-item:not(.bottom-bar-recruitment) {
        flex: 1; min-width: 44px; min-height: 44px;
        display: flex !important;
        flex-direction: column; align-items: center; justify-content: center;
        gap: 2px;
        color: var(--v-text-sub) !important;
      }
      body.layout-shelf .bottom-bar-item.active { color: var(--v-accent) !important; font-weight: 600; }
      body.layout-shelf .bb-icon  { font-size: 17px; line-height: 1; }
      body.layout-shelf .bb-label { font-size: 10px; line-height: 1; }
    }

    /* ============================================================
       13.4 版式 C · 清单版  body.layout-list
            主打「搜 + 找得快」：深色吸顶 + 单列左图右文
       ============================================================ */
    body.layout-list {
      --v-page:     #ffffff;
      --v-row:      #ffffff;
      --v-text:     #101216;
      --v-text-sub: #8c919b;
      --v-line:     #edeff3;
      --v-accent:   #111418;
      --v-price:    #111418;
      --v-promo:    #e5352b;
      --v-head-bg:  #171a1f;
      --v-head-fg:  #ffffff;
      --v-img:      88px;
      --v-sort-bg:  #f7f8fa;
    }
    /* ★ 纠偏 1：节日主题下深色顶栏让位，价格改亮色，否则黑字看不见 */
    body.layout-list.festival-mode {
      --v-page:     var(--m-bg);
      --v-row:      var(--m-surface);
      --v-text:     var(--m-text);
      --v-text-sub: var(--m-text-sub);
      --v-line:     var(--m-line);
      --v-accent:   var(--m-accent);
      --v-price:    var(--m-text);
      --v-promo:    var(--m-accent);
      --v-head-bg:  var(--m-surface);
      --v-head-fg:  var(--m-text);
      --v-sort-bg:  var(--m-surface);
    }

    @media (max-width: 768px) {
      body.layout-list {
        background: var(--v-page) !important;
        padding-bottom: calc(56px + env(safe-area-inset-bottom, 0px)) !important;
      }
      /* 同上：sticky navbar 占流，清 banner 占位（P1） */
      body.layout-list .banner { margin-top: 0 !important; }
      body.layout-list .page-content { padding-top: 0 !important; }

      /* 深色吸顶区（清单版视觉签名） */
      body.layout-list .navbar {
        position: sticky !important;
        top: 0; left: 0; right: 0;
        padding: 0 14px !important;
        background: var(--v-head-bg) !important;
        border-bottom: none !important;
        -webkit-backdrop-filter: none !important;
        backdrop-filter: none !important;
        z-index: 100;
      }
      body.layout-list .nav-content { padding: 8px 0 0 !important; }
      body.layout-list .logo {
        font-size: 12px !important;
        letter-spacing: .5px !important;
        color: var(--v-head-fg) !important;
        background: none !important;
        -webkit-text-fill-color: currentColor !important;
        background-clip: border-box !important;
      }
      body.layout-list .search-container { flex: 1 1 auto; min-width: 0; }
      body.layout-list .search-input {
        width: 100% !important;
        height: 38px !important;
        border-radius: 999px !important;
        background: rgba(255, 255, 255, .12) !important;
        border: 1px solid rgba(255, 255, 255, .16) !important;
        color: var(--v-head-fg) !important;
        font-size: 14px !important;
        padding: 0 14px 0 36px !important;
      }
      body.layout-list .search-input::placeholder { color: rgba(255, 255, 255, .55) !important; }
      body.layout-list .search-input:focus {
        background: #fff !important;
        color: #101216 !important;
        border-color: #fff !important;
      }
      body.layout-list .search-icon {
        left: 12px !important; right: auto !important;
        color: rgba(255, 255, 255, .6) !important; font-size: 15px !important;
      }
      body.layout-list.festival-mode .search-input {
        background: rgba(255, 255, 255, .08) !important;
        border-color: var(--m-line) !important;
      }

      /* 一级分类：下划线 tab（不是胶囊） */
      body.layout-list .nav-bottom-row {
        margin: 6px -14px 0 !important;
        padding: 0 14px !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
      }
      body.layout-list .nav-bottom-row::-webkit-scrollbar { display: none; }
      body.layout-list .nav-links { display: flex !important; flex-wrap: nowrap !important; gap: 4px !important; }
      body.layout-list .nav-btn {
        position: relative;
        flex: 0 0 auto !important;
        height: 40px !important;
        padding: 0 10px !important;
        border: none !important;
        border-radius: 0 !important;
        background: transparent !important;
        color: rgba(255, 255, 255, .62) !important;
        font-size: 13px !important;
        white-space: nowrap !important;
      }
      body.layout-list.festival-mode .nav-btn { color: rgba(247, 233, 208, .6) !important; }
      body.layout-list .nav-btn::after {
        content: ''; position: absolute; left: 0; right: 0; top: -2px; bottom: -2px;
      }
      body.layout-list .nav-btn.active {
        background: transparent !important;
        color: var(--v-head-fg) !important;
        font-weight: 600;
        box-shadow: inset 0 -3px 0 0 var(--v-head-fg);
      }
      body.layout-list .nav-arrow { font-size: 9px; opacity: .55; }
      body.layout-list .nav-dropdown { position: static !important; }
      body.layout-list .nav-dropdown-content { display: none !important; }

      /* 排序分段条（仅清单版可见） */
      body.layout-list #sortBar {
        display: flex;
        position: sticky;
        top: 94px;
        background: var(--v-sort-bg);
        border-bottom: 1px solid var(--v-line);
        z-index: 99;
      }
      body.layout-list #sortBar .sort-item {
        flex: 1;
        position: relative;
        height: 36px;
        display: flex; align-items: center; justify-content: center;
        background: transparent; border: none;
        font-size: 13px; color: var(--v-text-sub);
        font-family: inherit;
        -webkit-tap-highlight-color: transparent;
      }
      body.layout-list #sortBar .sort-item::after {
        content: ''; position: absolute; left: 0; right: 0; top: -4px; bottom: -4px;
      }
      body.layout-list #sortBar .sort-item.active {
        background: var(--v-row); color: var(--v-accent); font-weight: 600;
      }

      /* 清单容器与行 */
      body.layout-list .gallery {
        display: block !important;
        grid-template-columns: none !important;
        gap: 0 !important;
        padding: 0 !important;
      }
      body.layout-list .card {
        display: flex !important;
        align-items: center;
        /* 旧微信 X5 不认 flex gap；图-文间距改由 .card-image 的 margin-right 兜底（P1） */
        padding: 12px 14px !important;
        margin: 0 !important;
        background: var(--v-row) !important;
        border: none !important;
        border-bottom: 1px solid var(--v-line) !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        transform: none !important;
      }
      body.layout-list .card:active { background: #f5f6f8; }
      body.layout-list.festival-mode .card:active { background: rgba(255, 255, 255, .04); }
      body.layout-list .card-image {
        width: var(--v-img) !important;
        height: var(--v-img) !important;
        flex: 0 0 var(--v-img) !important;
        border-radius: 8px !important;
        object-fit: cover !important;
        display: block;
        margin-right: 12px !important; /* 间距兜底：兼容不认 flex gap 的旧微信 X5（P1） */
        background: var(--v-media);
        aspect-ratio: auto !important;
      }
      body.layout-list .card-info {
        flex: 1 1 auto;
        min-width: 0;
        padding: 0 !important;
      }
      body.layout-list .card-name {
        margin: 0 !important;
        font-size: 14px !important;
        line-height: 20px !important;
        font-weight: 600;
        color: var(--v-text) !important;
        display: -webkit-box;
        -webkit-line-clamp: 1;
        -webkit-box-orient: vertical;
        overflow: hidden;
        white-space: normal;
      }
      body.layout-list .card-price {
        display: flex !important;
        align-items: baseline;
        flex-wrap: wrap;
        gap: 6px;
        margin: 6px 0 0 !important;
        font-size: 20px !important;
        font-weight: 800;
        line-height: 1;
        color: var(--v-price) !important;
      }
      body.layout-list .card-price .price-origin {
        font-size: 20px !important; font-weight: 800; color: var(--v-price) !important;
      }
      body.layout-list .card-price .special-price {
        font-size: 20px !important; font-weight: 800; color: var(--v-promo) !important;
      }
      body.layout-list .card-price .original-price {
        font-size: 12px !important; font-weight: 400; color: var(--v-text-sub) !important;
      }
      body.layout-list .card-category {
        display: block !important;
        margin: 4px 0 0 !important;
        padding: 0 !important;
        background: none !important;
        border: none !important;
        font-size: 12px !important;
        line-height: 16px !important;
        color: var(--v-text-sub) !important;
      }

      /* 底部栏（与货架版一致，保持微信端手感统一） */
      body.layout-list .bottom-bar {
        position: fixed !important;
        left: 0; right: 0; bottom: 0; top: auto !important;
        height: 56px;
        display: flex !important;
        align-items: stretch;
        background: rgba(255, 255, 255, .98) !important;
        border-top: 1px solid var(--v-line) !important;
        border-radius: 0 !important;
        -webkit-backdrop-filter: none !important;
        backdrop-filter: none !important;
        padding: 0 0 env(safe-area-inset-bottom, 0px) !important;
        z-index: 190;
        transform: none !important;
      }
      body.layout-list.festival-mode .bottom-bar { background: rgba(26, 6, 9, .98) !important; }
      body.layout-list .bottom-bar-recruitment { display: none !important; }
      /* 同货架版：:not() 排除招商入口，避免被 flex 规则盖掉（P1） */
      body.layout-list .bottom-bar-item:not(.bottom-bar-recruitment) {
        flex: 1; min-width: 44px; min-height: 44px;
        display: flex !important;
        flex-direction: column; align-items: center; justify-content: center;
        gap: 2px;
        color: var(--v-text-sub) !important;
      }
      body.layout-list .bottom-bar-item.active { color: var(--v-accent) !important; font-weight: 600; }
      body.layout-list .bb-icon  { font-size: 17px; line-height: 1; }
      body.layout-list .bb-label { font-size: 10px; line-height: 1; }
    }

    /* ============================================================
       13.5 外观设置弹层（复用 .sheet-* 类）
       ============================================================ */
    #uiVarSheet .var-group { margin-bottom: 14px; }
    #uiVarSheet .var-group:last-child { margin-bottom: 2px; }
    #uiVarSheet .var-label {
      font-size: 12px; font-weight: 700; letter-spacing: .5px;
      color: var(--m-text-sub); margin-bottom: 8px;
    }
    #uiVarSheet .var-row { display: grid; gap: 8px; }
    #uiVarSheet .var-row--2 { grid-template-columns: repeat(2, 1fr); }
    #uiVarSheet .var-row--3 { grid-template-columns: repeat(3, 1fr); }
    #uiVarSheet .var-opt {
      position: relative;
      min-height: 44px;
      padding: 10px 6px;
      border-radius: 10px;
      border: 1px solid var(--m-line);
      background: transparent;
      color: var(--m-text);
      font-size: 13px;
      font-family: inherit;
      cursor: pointer;
      text-align: center;
      -webkit-tap-highlight-color: transparent;
      display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
    }
    #uiVarSheet .var-opt .var-opt-icon { font-size: 16px; line-height: 1; }
    #uiVarSheet .var-opt.active {
      background: var(--m-accent); border-color: var(--m-accent);
      color: #fff; font-weight: 600;
    }
    body.festival-mode #uiVarSheet .var-opt.active { color: #1a0508; }
    #uiVarSheet .var-hint {
      margin-top: 12px; font-size: 11px; line-height: 1.5; color: var(--m-text-sub);
    }

    /* 手机端：浮动切换按钮让位给底部「外观」入口，避免压住分类行 */
    @media (max-width: 768px) {
      #uiModeToggle { display: none !important; }
    }
    /* 桌面端：底部移动元素一律隐藏（含新增的「外观」入口与排序条/设置弹层） */
    @media (min-width: 769px) {
      #bbLook, #sortBar, #uiVarSheet { display: none !important; }
    }

    /* 软键盘弹出时收起底部栏，避免遮挡输入框（必须放最后，靠源码顺序压过版式规则） */
    @media (max-width: 768px) {
      body.kb-open .bottom-bar { transform: translateY(115%) !important; }
    }
""" + "\n    " + MARK_CSS_END


# ═════════════════════════════════ HTML ═════════════════════════════════
# 排序条单独成块：注入到 <section class="gallery"> 之前（导航之后、列表之上），
# 这样 sticky 吸顶时停在列表顶端，用户一进页面就能看到并排序（P0 修复：原版本被插在 337 张卡片之后）
SORTBAR_BLOCK = MARK_SORT + r"""
  <!-- 清单版排序条（仅 body.layout-list 显示），位于导航之后、列表之前 -->
  <div id="sortBar" role="tablist" aria-label="排序方式">
    <button class="sort-item active" type="button" data-sort="default"    role="tab" aria-selected="true">综合</button>
    <button class="sort-item"        type="button" data-sort="price-asc"  role="tab" aria-selected="false">价格 ↑</button>
    <button class="sort-item"        type="button" data-sort="price-desc" role="tab" aria-selected="false">价格 ↓</button>
  </div>
""" + "\n  " + MARK_SORT_END

HTML_BLOCK = MARK_HTML + r"""
  <!-- 外观设置弹层（主题 + 版式） -->
  <div id="uiVarSheet">
    <div class="sheet-mask" id="varMask"></div>
    <div class="sheet-panel" id="varPanel">
      <div class="sheet-handle"></div>
      <div class="sheet-title">
        <span>外观设置</span>
        <button class="sheet-close" type="button" id="varClose" aria-label="关闭">&times;</button>
      </div>

      <div class="var-group">
        <div class="var-label">主题</div>
        <div class="var-row var-row--3" id="varThemeRow">
          <button class="var-opt" type="button" data-theme="auto"><span class="var-opt-icon">🗓</span>跟随节日</button>
          <button class="var-opt" type="button" data-theme="daily"><span class="var-opt-icon">🌤</span>日常</button>
          <button class="var-opt" type="button" data-theme="festival"><span class="var-opt-icon">🎊</span>节日</button>
        </div>
      </div>

      <div class="var-group">
        <div class="var-label">版式</div>
        <div class="var-row var-row--3" id="varLayoutRow">
          <button class="var-opt" type="button" data-layout="std"><span class="var-opt-icon">▦</span>标准</button>
          <button class="var-opt" type="button" data-layout="shelf"><span class="var-opt-icon">🧱</span>货架</button>
          <button class="var-opt" type="button" data-layout="list"><span class="var-opt-icon">☰</span>清单</button>
        </div>
      </div>

      <div class="var-hint">版式只改布局，价格口径始终按实际日期计算。</div>
    </div>
  </div>
""" + "\n  " + MARK_HTML_END


# ═════════════════════════════════ JS ═════════════════════════════════
JS_BLOCK = MARK_JS + r"""
    /* ============================================================
       14. 版式轴 + 外观设置（脚本补丁注入）
           · 版式存 localStorage.aj5_ui_layout = std | shelf | list
           · 主题沿用既有 localStorage.aj5_ui_mode（auto | daily | festival）
           · 手机端：右上角浮动按钮已隐藏，改由底部「外观」入口打开设置弹层
           ============================================================ */
    (function initUiVariants() {
      var LAYOUT_KEY = 'aj5_ui_layout';
      var LAYOUTS = ['std', 'shelf', 'list'];
      var mqMobile = window.matchMedia('(max-width: 768px)');

      /* ---------- 版式读写 ---------- */
      function getLayout() {
        var v = 'std';
        try { v = localStorage.getItem(LAYOUT_KEY) || 'std'; } catch (e) {}
        return LAYOUTS.indexOf(v) >= 0 ? v : 'std';
      }
      function applyLayout(name) {
        if (LAYOUTS.indexOf(name) < 0) name = 'std';
        LAYOUTS.forEach(function (n) {
          document.body.classList.toggle('layout-' + n, n === name);
        });
        document.body.setAttribute('data-layout', name);
        // 版式切换后重排列表（网格/清单列数变化需要复位分页）
        try { renderGallery(); } catch (e) {}
        // 清单版深色顶栏高度实测后写回，供 #sortBar 的 sticky top 用
        syncSortBarOffset();
      }
      function syncSortBarOffset() {
        var nav = document.querySelector('.navbar');
        var bar = document.getElementById('sortBar');
        if (!nav || !bar) return;
        var h = Math.round(nav.getBoundingClientRect().height);
        if (document.body.classList.contains('layout-list') && h > 0) {
          bar.style.top = h + 'px';
        } else {
          bar.style.top = '';
        }
      }

      /* ---------- 主题读写（复用既有 applyUiMode / isPromoNow） ---------- */
      function getTheme() {
        var v = 'auto';
        try { v = localStorage.getItem(UI_MODE_KEY) || 'auto'; } catch (e) {}
        return (v === 'daily' || v === 'festival') ? v : 'auto';
      }
      function setTheme(v) {
        try { localStorage.setItem(UI_MODE_KEY, v); } catch (e) {}
        var promo = (typeof isPromoNow === 'function') ? isPromoNow() : {};
        var real = (v === 'auto') ? ((promo && promo.active) ? 'festival' : 'daily') : v;
        applyUiMode(real, promo);
        syncThemeRow();
        syncLookIcon();
      }

      /* ---------- 外观弹层 ---------- */
      var varSheet = document.getElementById('uiVarSheet');
      var varMask  = document.getElementById('varMask');
      var varPanel = document.getElementById('varPanel');
      var varClose = document.getElementById('varClose');

      function openVarSheet() {
        if (!varSheet) return;
        syncThemeRow(); syncLayoutRow();
        varSheet.classList.add('open');
        document.body.classList.add('sheet-locked');
        if (varMask)  varMask.classList.add('show');
        if (varPanel) varPanel.classList.add('show');
      }
      function closeVarSheet() {
        if (!varSheet) return;
        varSheet.classList.remove('open');
        document.body.classList.remove('sheet-locked');
        if (varMask)  varMask.classList.remove('show');
        if (varPanel) varPanel.classList.remove('show');
      }
      if (varMask)  varMask.addEventListener('click', closeVarSheet);
      if (varClose) varClose.addEventListener('click', closeVarSheet);

      function syncThemeRow() {
        var cur = getTheme();
        var row = document.getElementById('varThemeRow');
        if (!row) return;
        row.querySelectorAll('.var-opt').forEach(function (b) {
          b.classList.toggle('active', b.dataset.theme === cur);
          b.setAttribute('aria-pressed', String(b.dataset.theme === cur));
        });
      }
      function syncLayoutRow() {
        var cur = getLayout();
        var row = document.getElementById('varLayoutRow');
        if (!row) return;
        row.querySelectorAll('.var-opt').forEach(function (b) {
          b.classList.toggle('active', b.dataset.layout === cur);
          b.setAttribute('aria-pressed', String(b.dataset.layout === cur));
        });
      }

      var themeRow = document.getElementById('varThemeRow');
      if (themeRow) {
        themeRow.addEventListener('click', function (e) {
          var b = e.target.closest('.var-opt');
          if (!b) return;
          setTheme(b.dataset.theme);
        });
      }
      var layoutRow = document.getElementById('varLayoutRow');
      if (layoutRow) {
        layoutRow.addEventListener('click', function (e) {
          var b = e.target.closest('.var-opt');
          if (!b) return;
          var v = b.dataset.layout;
          try { localStorage.setItem(LAYOUT_KEY, v); } catch (er) {}
          applyLayout(v);
          syncLayoutRow();
        });
      }

      /* ---------- 手机端：拦截浮动按钮，改为弹设置层 ---------- */
      document.addEventListener('click', function (e) {
        if (!mqMobile.matches) return;
        var t = e.target.closest && e.target.closest('#uiModeToggle');
        if (!t) return;
        e.preventDefault();
        e.stopPropagation();
        openVarSheet();
      }, true);

      /* ---------- 底部「外观」入口 ---------- */
      var bbLook = document.getElementById('bbLook');
      if (bbLook) {
        bbLook.addEventListener('click', function (e) {
          e.preventDefault();
          openVarSheet();
        });
      }
      function syncLookIcon() {
        if (!bbLook) return;
        var icon = bbLook.querySelector('.bb-icon');
        if (!icon) return;
        var fest = document.body.classList.contains('festival-mode');
        var lay = getLayout();
        icon.textContent = fest ? '🎊' : (lay === 'list' ? '☰' : (lay === 'shelf' ? '🧱' : '🎨'));
      }

      /* ---------- 排序条（清单版） ---------- */
      function priceNum(shoe) {
        try {
          var p = calcPrice(shoe);
          var raw = p.special || p.original || '0';
          return parsePriceValue(raw);
        } catch (e) { return 0; }
      }
      var sortMode = 'default';
      function doSort(mode) {
        sortMode = mode;
        if (mode === 'default') { renderGallery(); return; }
        var arr = filteredShoes.slice();
        arr.sort(function (a, b) {
          var d = priceNum(a) - priceNum(b);
          return mode === 'price-asc' ? d : -d;
        });
        filteredShoes = arr;
        displayCount = 0;
        loadMore(false);
      }
      var sortBar = document.getElementById('sortBar');
      if (sortBar) {
        sortBar.addEventListener('click', function (e) {
          var b = e.target.closest('.sort-item');
          if (!b) return;
          sortBar.querySelectorAll('.sort-item').forEach(function (x) {
            var on = x === b;
            x.classList.toggle('active', on);
            x.setAttribute('aria-selected', String(on));
          });
          doSort(b.dataset.sort);
        });
      }
      // 换了分类/搜索后仍保持当前排序
      var _origRenderGallery = renderGallery;
      renderGallery = function () {
        _origRenderGallery.apply(null, arguments);
        if (sortMode !== 'default') {
          var arr = filteredShoes.slice();
          arr.sort(function (a, b) {
            var d = priceNum(a) - priceNum(b);
            return sortMode === 'price-asc' ? d : -d;
          });
          filteredShoes = arr;
          displayCount = 0;
          loadMore(false);
        }
        syncSortBarOffset();
      };

      /* ---------- 软键盘：收起底部栏 ---------- */
      document.addEventListener('focusin', function (e) {
        var t = e.target;
        if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) {
          document.body.classList.add('kb-open');
        }
      });
      document.addEventListener('focusout', function (e) {
        var t = e.target;
        if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA')) {
          setTimeout(function () { document.body.classList.remove('kb-open'); }, 120);
        }
      });

      /* ---------- 窗口变化时校正 ---------- */
      var _rzT = null;
      window.addEventListener('resize', function () {
        clearTimeout(_rzT);
        _rzT = setTimeout(syncSortBarOffset, 150);
      });

      /* ---------- URL 直达参数（便于手机端分享与回归测试）----------
         ?v=std|shelf|list   ?theme=auto|daily|festival
         ---------------------------------------------------------- */
      var urlLayout = null, urlTheme = null;
      try {
        var sp = new URLSearchParams(location.search);
        var qv = sp.get('v');
        if (qv && LAYOUTS.indexOf(qv) >= 0) urlLayout = qv;
        var qt = sp.get('theme');
        if (qt && ['auto', 'daily', 'festival'].indexOf(qt) >= 0) urlTheme = qt;
      } catch (e) {}
      if (urlLayout) { try { localStorage.setItem(LAYOUT_KEY, urlLayout); } catch (e) {} }

      /* ---------- 打包 applyUiMode：主题一变就刷新「外观」图标 ---------- */
      var _origApplyUiMode = applyUiMode;
      applyUiMode = function () {
        _origApplyUiMode.apply(null, arguments);
        syncLookIcon();
      };

      /* ---------- 启动 ---------- */
      if (urlTheme) setTheme(urlTheme);
      applyLayout(getLayout());
      syncThemeRow();
      syncLayoutRow();
      syncLookIcon();
      syncSortBarOffset();
    })();

    /* 卡片角标：aj 一口价 / 节日特惠（默认隐藏，仅货架版显示） */
    function cardBadge(shoe, price) {
      if (!price) return '';
      if (price.isAj) {
        return '<span class="card-badge card-badge--fixed">一口价</span>';
      }
      if (price.isPromo) {
        return '<span class="card-badge card-badge--hot">节日特惠</span>';
      }
      return '';
    }
""" + "\n  " + MARK_JS_END


def _replace_card_template(html: str):
    """给卡片模板插入角标占位（幂等）"""
    if '${cardBadge(shoe, price)}' in html:
        return html, False
    old = ('<div class="card" data-id="${shoe.id}">\n'
           '          <img class="card-image"')
    new = ('<div class="card" data-id="${shoe.id}">\n'
           '          ${cardBadge(shoe, price)}\n'
           '          <img class="card-image"')
    if old not in html:
        return html, False
    return html.replace(old, new, 1), True


def _fix_viewport(html: str):
    """viewport 补 viewport-fit=cover（幂等）"""
    if 'viewport-fit=cover' in html:
        return html, False
    pat = re.compile(r'<meta\s+name="viewport"\s+content="([^"]*)"\s*>')
    m = pat.search(html)
    if not m:
        return html, False
    content = m.group(1)
    if 'viewport-fit' in content:
        return html, False
    new_content = content.rstrip().rstrip(';') + ', viewport-fit=cover'
    return html[:m.start()] + f'<meta name="viewport" content="{new_content}">' + html[m.end():], True


def _insert_look_button(html: str):
    """在 4 个移动端入口之后追加「外观」入口（幂等）"""
    if 'id="bbLook"' in html:
        return html, False
    anchor = 'id="bbContact"'
    i = html.find(anchor)
    if i < 0:
        return html, False
    j = html.find('</button>', i)
    if j < 0:
        return html, False
    j += len('</button>')
    btn = ('\n    <button class="bottom-bar-item bb-mobile" type="button" id="bbLook"'
           ' aria-label="外观设置">'
           '<span class="bb-icon">🎨</span><span class="bb-label">外观</span></button>')
    return html[:j] + btn + html[j:], True


def patch():
    if not INDEX.exists():
        print(f"[!!] 找不到 {INDEX}")
        return False
    html = INDEX.read_text(encoding='utf-8')

    fresh = not already_patched(html)
    if fresh:
        BACKUP.mkdir(parents=True, exist_ok=True)
        bk = BACKUP / f"index_before_uivariants_{datetime.now():%Y%m%d_%H%M%S}"
        bk.mkdir(parents=True, exist_ok=True)
        shutil.copy2(INDEX, bk / "index.html")
        print(f"[✓] 已备份 → {bk / 'index.html'}")
    else:
        print("[•] 检测到既有补丁，执行原地替换（可迭代，不会堆叠）")

    changed = []

    # ① viewport-fit=cover
    html, ok = _fix_viewport(html)
    if ok:
        changed.append("viewport-fit")

    # ② CSS（有旧块则整段替换，保证迭代安全）
    r = _replace_region(html, MARK_CSS, MARK_CSS_END, CSS_BLOCK)
    if r is not None:
        if r != html:
            changed.append("CSS(替换)")
        html = r
    else:
        k = html.find('</style>')
        if k < 0:
            print("[!!] 找不到 </style>")
            return False
        html = html[:k] + CSS_BLOCK + "\n  " + html[k:]
        changed.append("CSS(新增)")

    # ③ 底部「外观」入口
    html, ok = _insert_look_button(html)
    if ok:
        changed.append("外观入口")

    # ④ HTML：外观弹层（注入到首个 <script> 之前，移动端才可见）
    r = _replace_region(html, MARK_HTML, MARK_HTML_END, HTML_BLOCK)
    if r is not None:
        if r != html:
            changed.append("HTML(替换)")
        html = r
    else:
        k = html.find('<script>')
        if k > 0:
            html = html[:k] + HTML_BLOCK + "\n  " + html[k:]
            changed.append("外观弹层(新增)")
        else:
            print("[!] 找不到 <script>")

    # ④b 排序条（注入到 <section class="gallery"> 之前，确保吸顶在列表上方，而非列表末尾）
    r2 = _replace_region(html, MARK_SORT, MARK_SORT_END, SORTBAR_BLOCK)
    if r2 is not None:
        if r2 != html:
            changed.append("排序条(替换)")
        html = r2
    else:
        k = html.find('<section class="gallery"')
        if k > 0:
            html = html[:k] + SORTBAR_BLOCK + "\n  " + html[k:]
            changed.append("排序条(新增)")
        else:
            print("[!] 找不到 <section class=\"gallery\">")

    # ⑤ 卡片模板插角标
    html, ok = _replace_card_template(html)
    if ok:
        changed.append("卡片角标")

    # ⑥ JS
    r = _replace_region(html, MARK_JS, MARK_JS_END, JS_BLOCK)
    if r is not None:
        if r != html:
            changed.append("JS(替换)")
        html = r
    else:
        k = html.rfind('</script>')
        if k > 0:
            html = html[:k] + JS_BLOCK + "\n  " + html[k:]
            changed.append("JS(版式+外观+排序)(新增)")
        else:
            print("[!] 找不到 </script>")

    INDEX.write_text(html, encoding='utf-8')
    if changed:
        print(f"[✓] 已注入: {', '.join(changed)}")
    else:
        print("[✓] 已是目标内容，无改动")
    print(f"[✓] 体积: {len(html.encode('utf-8'))} bytes")
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("  移动端两套新日常版式补丁")
    print("=" * 60)
    patch()
