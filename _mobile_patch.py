#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
移动端电商版式补丁（幂等 · 可重放）
=====================================
用途：把 index.html 改造成「手机微信浏览器 + 电商结构」：
  1) CSS  · 移动端令牌 + ≤768px 骨架 + 2 列大图 + 底部固定栏 + 底部弹层 + 弹窗优化
  2) HTML · 底部 4 入口（首页/分类/搜索/联系）+ 二级分类底部弹层 #subSheet
  3) JS   · 一级分类点击→底部弹层二级；底部 4 入口功能；底部栏手机端常驻；补齐 copyWechat

注意：
  · 本补丁只动 CSS/HTML/JS 三个锚点，不碰 const shoes 数据段，可安全在 sync.py build 之后运行。
  · 幂等：已打过补丁则跳过（检测 <style> 内是否已有 '--m-bg' 令牌）。
  · 与 update_gallery.py / sync.py 的 AUTO_NAV 段兼容（导航由它们生成，本补丁只读取 data-children）。
"""
import io, re, sys, shutil
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent
INDEX = BASE / "index.html"

MARK_CSS = "/* ==== MOBILE-ECO PATCH CSS ==== */"
MARK_HTML = "<!-- ==== MOBILE-ECO PATCH HTML ==== -->"
MARK_JS = "// ==== MOBILE-ECO PATCH JS ==== */"


CSS_BLOCK = MARK_CSS + r"""
    /* ============================================================
       12. 移动端电商版式（脚本补丁注入）
       ============================================================ */

    /* ---- 12.1 设计令牌 ---- */
    :root {
      --m-bg:        #f5f6f8;
      --m-surface:   #ffffff;
      --m-text:      #1b1b1f;
      --m-text-sub:  #8a8a93;
      --m-line:      #ececf0;
      --m-accent:    #ff4d4f;
      --m-bar:       rgba(255, 255, 255, 0.96);
      --m-shadow:    0 2px 12px rgba(0, 0, 0, 0.08);
    }
    /* 节日模式令牌（由 body.festival-mode 驱动） */
    body.festival-mode {
      --m-bg:        #1a0508;
      --m-surface:   #2a0d12;
      --m-text:      #f7e9d0;
      --m-text-sub:  #c9a97a;
      --m-line:      rgba(232, 196, 106, 0.22);
      --m-accent:    #e8c46a;
      --m-bar:       rgba(26, 6, 9, 0.97);
      --m-shadow:    0 2px 12px rgba(0, 0, 0, 0.5);
    }

    /* ---- 12.2 二级分类底部弹层（基础样式，桌面端由尾部规则隐藏） ---- */
    #subSheet { display: block; }
    body.sheet-locked { overflow: hidden !important; }
    .sheet-mask {
      position: fixed; inset: 0;
      background: rgba(0, 0, 0, 0.45);
      opacity: 0; visibility: hidden;
      transition: opacity 0.22s ease, visibility 0.22s;
      z-index: 300;
    }
    .sheet-mask.show { opacity: 1; visibility: visible; }
    .sheet-panel {
      position: fixed; left: 0; right: 0; bottom: 0;
      background: var(--m-surface);
      border-radius: 16px 16px 0 0;
      padding: 14px 14px calc(16px + env(safe-area-inset-bottom, 0px));
      transform: translateY(102%);
      transition: transform 0.26s cubic-bezier(0.32, 0.72, 0.3, 1);
      z-index: 301;
      max-height: 62vh; overflow-y: auto;
      -webkit-overflow-scrolling: touch;
    }
    .sheet-panel.show { transform: translateY(0); }
    .sheet-handle {
      width: 36px; height: 4px; border-radius: 2px;
      background: var(--m-line); margin: 0 auto 12px;
    }
    .sheet-title {
      font-size: 14px; font-weight: 700; color: var(--m-text);
      margin-bottom: 12px;
      display: flex; align-items: center; justify-content: space-between;
    }
    .sheet-title .sheet-close {
      font-size: 20px; line-height: 1; color: var(--m-text-sub);
      background: none; border: none; cursor: pointer; padding: 0 4px;
    }
    .sheet-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .sheet-item {
      padding: 11px 6px; border-radius: 10px;
      border: 1px solid var(--m-line); background: transparent;
      color: var(--m-text); font-size: 13px; cursor: pointer;
      text-align: center; white-space: nowrap;
      overflow: hidden; text-overflow: ellipsis;
      -webkit-tap-highlight-color: transparent; min-height: 40px;
    }
    .sheet-item.active {
      background: var(--m-accent); border-color: var(--m-accent);
      color: #fff; font-weight: 600;
    }
    body.festival-mode .sheet-item.active { color: #1a0508; }

    /* 联系客服弹层内容 */
    .contact-sheet {
      grid-column: 1 / -1;
      display: flex; flex-direction: column;
      align-items: center; gap: 10px; padding: 4px 0 6px;
    }
    .contact-sheet-qr {
      width: 168px; height: 168px; object-fit: contain;
      border-radius: 12px; background: #fff; padding: 8px;
      box-shadow: var(--m-shadow);
    }
    .contact-sheet-tip { font-size: 12px; color: var(--m-text-sub); margin: 0; }
    .contact-sheet-id {
      font-size: 17px; font-weight: 700; color: var(--m-text);
      letter-spacing: 0.5px; margin: 0;
    }
    .contact-sheet-copy {
      margin-top: 2px; padding: 11px 34px; border-radius: 999px;
      border: none; background: var(--m-accent); color: #fff;
      font-size: 14px; font-weight: 600; cursor: pointer;
      -webkit-tap-highlight-color: transparent;
    }
    body.festival-mode .contact-sheet-copy { color: #1a0508; }

    .bb-mobile { display: none !important; }

    /* ---- 12.3 移动端整体骨架（≤768px 生效） ---- */
    @media (max-width: 768px) {
      body { background: var(--m-bg) !important; color: var(--m-text) !important; }

      .nav-content { padding: 8px 10px 0 !important; }
      .nav-top-row { display: flex; align-items: center; gap: 8px; }
      .logo { font-size: 15px !important; letter-spacing: 0.5px !important; }

      .search-container { flex: 1; }
      .search-input {
        width: 100% !important;
        height: 36px !important;
        border-radius: 999px !important;
        background: var(--m-surface) !important;
        border: 1px solid var(--m-line) !important;
        color: var(--m-text) !important;
        font-size: 14px !important;
        padding: 0 34px 0 14px !important;
      }
      .search-input::placeholder { color: var(--m-text-sub) !important; }
      .search-icon { color: var(--m-text-sub) !important; }

      /* 一级分类横向滑动 */
      .nav-bottom-row {
        margin: 8px -10px 0 !important;
        padding: 0 10px 8px !important;
        overflow-x: auto !important;
        overflow-y: visible !important;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
      }
      .nav-bottom-row::-webkit-scrollbar { display: none; }
      .nav-links { display: flex !important; flex-wrap: nowrap !important; gap: 8px !important; }
      .nav-btn {
        flex: 0 0 auto !important;
        height: 32px !important;
        padding: 0 14px !important;
        border-radius: 999px !important;
        background: var(--m-surface) !important;
        border: 1px solid var(--m-line) !important;
        color: var(--m-text) !important;
        font-size: 13px !important;
        white-space: nowrap !important;
      }
      .nav-btn.active {
        background: var(--m-accent) !important;
        border-color: var(--m-accent) !important;
        color: #fff !important;
        font-weight: 600;
      }
      body.festival-mode .nav-btn.active { color: #1a0508 !important; }
      .nav-arrow { font-size: 9px; opacity: 0.6; }
      .nav-dropdown { position: static !important; }
      .nav-dropdown-content { display: none !important; }   /* 手机端不用桌面下拉 */

      /* 主题切换按钮：移到右下角、缩小 */
      #uiModeToggle {
        top: auto !important;
        right: 12px !important;
        bottom: 68px !important;
        height: 32px !important;
        padding: 0 12px !important;
        font-size: 12px !important;
        border-radius: 999px !important;
        z-index: 195 !important;
      }

      #festivalBanner { font-size: 12px !important; }
      .banner { padding: 18px 14px !important; }
      .banner-title { font-size: 20px !important; }
      .banner-subtitle { font-size: 13px !important; }

      .section-header { padding: 12px 12px 6px !important; }
      .section-title { font-size: 16px !important; color: var(--m-text) !important; }

      /* 2 列大图（电商主流） */
      .gallery {
        display: grid !important;
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 10px !important;
        padding: 0 10px 16px !important;
      }
      .card {
        background: var(--m-surface) !important;
        border: none !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: var(--m-shadow) !important;
        margin: 0 !important;
        cursor: pointer;
      }
      .card img {
        width: 100% !important;
        aspect-ratio: 1 / 1;
        object-fit: cover !important;
        display: block;
      }
      .card-info, .card-body { padding: 8px 10px 10px !important; }
      .card-name {
        font-size: 13px !important;
        color: var(--m-text) !important;
        line-height: 1.35;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .card-category { font-size: 11px !important; color: var(--m-text-sub) !important; }
      .card-price {
        font-size: 16px !important;
        color: var(--m-accent) !important;
        font-weight: 700;
      }

      /* 底部固定导航栏（像小程序） */
      .bottom-bar {
        position: fixed !important;
        left: 0 !important; right: 0 !important; bottom: 0 !important; top: auto !important;
        height: 56px;
        display: flex !important;
        align-items: stretch;
        background: var(--m-bar) !important;
        border-top: 1px solid var(--m-line) !important;
        border-radius: 0 !important;
        backdrop-filter: blur(12px);
        box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.08);
        padding: 0 0 env(safe-area-inset-bottom, 0px) !important;
        z-index: 190;
        transform: none !important;
        transition: transform 0.25s ease;
      }
      .bottom-bar.hidden { transform: translateY(100%) !important; }
      .bottom-bar-item {
        flex: 1;
        display: flex !important;
        flex-direction: column;
        align-items: center; justify-content: center;
        gap: 2px;
        font-size: 11px !important;
        color: var(--m-text-sub) !important;
        background: transparent !important;
        border: none !important;
        cursor: pointer;
        -webkit-tap-highlight-color: transparent;
        padding: 0 !important;
        border-radius: 0 !important;
      }
      .bottom-bar-item.active { color: var(--m-accent) !important; font-weight: 600; }
      .bottom-bar-item .bb-icon { font-size: 17px; line-height: 1; }
      .bottom-bar-item .bb-label { font-size: 10px; line-height: 1; }
      .bottom-bar-recruitment { display: none !important; }   /* 手机端隐藏招商入口 */
      .bb-mobile { display: flex !important; }

      /* 底部弹层：手机端启用 */
      #subSheet { display: block !important; }

      /* 弹窗（大图）手机优化 */
      .modal-content {
        max-width: 100% !important; width: 100% !important;
        border-radius: 16px !important;
        max-height: 92vh; overflow-y: auto;
      }
      .modal-image { max-height: 52vh !important; object-fit: contain !important; }
      .modal-name { font-size: 17px !important; }
      .modal-price { font-size: 20px !important; }
      .modal-close {
        width: 34px !important; height: 34px !important;
        font-size: 22px !important; line-height: 32px !important;
      }

      .load-more-btn { border-radius: 999px !important; padding: 11px 30px !important; font-size: 14px !important; }
      .load-more-container { padding: 18px 12px 84px !important; }

      /* 给底部栏留出空间 */
      body { padding-bottom: 64px !important; }
    }

    /* ---- 12.4 桌面端：隐藏移动端专属元素 ---- */
    @media (min-width: 769px) {
      #subSheet { display: none !important; }
      .bb-mobile { display: none !important; }
    }

    /* ---- 12.5 超小屏微调 ---- */
    @media (max-width: 360px) {
      .gallery { gap: 8px !important; padding: 0 8px 70px !important; }
      .nav-content { padding: 8px 8px 0 !important; }
      .nav-bottom-row { margin: 8px -8px 0 !important; padding: 0 8px 8px !important; }
      .card-name { font-size: 12px !important; }
    }
"""

HTML_BLOCK = MARK_HTML + r"""
  <!-- ============================
       B. 移动端底部 4 入口（CSS 控制仅手机显示）
       ============================ -->
  <div id="subSheet">
    <div class="sheet-mask" id="sheetMask"></div>
    <div class="sheet-panel" id="sheetPanel" role="dialog" aria-modal="true" aria-label="选择子分类">
      <div class="sheet-handle"></div>
      <div class="sheet-title">
        <span id="sheetTitle">选择分类</span>
        <button class="sheet-close" type="button" id="sheetClose" aria-label="关闭">&times;</button>
      </div>
      <div class="sheet-grid" id="sheetGrid"></div>
    </div>
  </div>
"""

BB_BUTTONS = r"""
    <!-- 移动端 4 入口 -->
    <button class="bottom-bar-item bb-mobile" type="button" data-bb="home" id="bbHome">
      <span class="bb-icon">🏠</span><span class="bb-label">首页</span>
    </button>
    <button class="bottom-bar-item bb-mobile" type="button" data-bb="cate" id="bbCate">
      <span class="bb-icon">🗂</span><span class="bb-label">分类</span>
    </button>
    <button class="bottom-bar-item bb-mobile" type="button" data-bb="search" id="bbSearch">
      <span class="bb-icon">🔍</span><span class="bb-label">搜索</span>
    </button>
    <button class="bottom-bar-item bb-mobile" type="button" data-bb="contact" id="bbContact">
      <span class="bb-icon">💬</span><span class="bb-label">联系</span>
    </button>
"""

JS_BLOCK = r"""
    /* ============================================================
       13. 移动端电商交互（脚本补丁注入）
       ============================================================
       · 手机（≤768px）：点一级分类 → 底部弹层出二级；底部 4 入口可用；底部栏常驻
       · 桌面（>768px）：完全沿用原有下拉逻辑，本段自动旁路
       ============================================================ */
    (function initMobileEcommerce() {
      var mq = window.matchMedia('(max-width: 768px)');
      var sheet      = document.getElementById('subSheet');
      var sheetMask  = document.getElementById('sheetMask');
      var sheetPanel = document.getElementById('sheetPanel');
      var sheetTitle = document.getElementById('sheetTitle');
      var sheetClose = document.getElementById('sheetClose');
      var sheetGrid  = document.getElementById('sheetGrid');
      var bottomBarEl = document.getElementById('bottomBar');
      if (!sheet || !sheetGrid) return;

      var openFlag = false;

      function escapeHtml(s) {
        return String(s == null ? '' : s)
          .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
      }

      function openSheet(top, label, children) {
        sheetTitle.textContent = label || '选择分类';
        var subs = String(children || '').split(',').map(function (x) { return x.trim(); }).filter(Boolean);
        var cur = (typeof currentSub !== 'undefined') ? currentSub : '';
        var html = '<button class="sheet-item' + (cur ? '' : ' active') + '" type="button"'
                 + ' data-top="' + top + '" data-sub="">全部</button>';
        html += subs.map(function (s) {
          return '<button class="sheet-item' + (cur === s ? ' active' : '') + '" type="button"'
               + ' data-top="' + top + '" data-sub="' + s + '">' + escapeHtml(s) + '</button>';
        }).join('');
        sheetGrid.innerHTML = html;
        if (sheetMask) sheetMask.classList.add('show');
        if (sheetPanel) sheetPanel.classList.add('show');
        sheet.classList.add('open');
        document.body.classList.add('sheet-locked');
        openFlag = true;
      }

      function closeSheet() {
        if (sheetMask) sheetMask.classList.remove('show');
        if (sheetPanel) sheetPanel.classList.remove('show');
        sheet.classList.remove('open');
        document.body.classList.remove('sheet-locked');
        openFlag = false;
      }

      /* 弹层内点击二级项 → 切换分类 + 关弹层 */
      sheetGrid.addEventListener('click', function (e) {
        var item = e.target.closest('.sheet-item');
        if (!item) return;
        var top = item.dataset.top;
        var sub = item.dataset.sub || '';
        var label = sheetTitle.textContent || top;
        closeSheet();
        switchCategory(top, sub, sub ? sub : label);
        var g = document.getElementById('gallery');
        if (g) setTimeout(function () { g.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 60);
      });

      if (sheetMask) sheetMask.addEventListener('click', closeSheet);
      if (sheetClose) sheetClose.addEventListener('click', closeSheet);
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && openFlag) closeSheet();
      });

      /* 移动端：一级分类点击改为开弹层（捕获阶段抢先处理） */
      var navLinks = document.querySelector('.nav-links');
      if (navLinks) {
        navLinks.addEventListener('click', function (e) {
          if (!mq.matches) return;
          var btn = e.target.closest('.nav-btn');
          if (!btn) return;
          if (btn.dataset.top === 'all') return;      // "全部" 交给原逻辑
          var children = btn.dataset.children;
          if (children) {
            e.stopPropagation(); e.preventDefault();
            var label = btn.textContent.replace('▼', '').trim();
            openSheet(btn.dataset.top, label, children);
          } else if (openFlag) {
            closeSheet();
          }
        }, true);
      }

      /* 底部 4 入口 */
      var bbHome = document.getElementById('bbHome');
      var bbCate = document.getElementById('bbCate');
      var bbSearch = document.getElementById('bbSearch');
      var bbContact = document.getElementById('bbContact');

      function setActiveBb(el) {
        [bbHome, bbCate, bbSearch, bbContact].forEach(function (b) {
          if (b) b.classList.toggle('active', b === el);
        });
      }

      if (bbHome) bbHome.addEventListener('click', function () {
        setActiveBb(bbHome); closeSheet();
        switchCategory('all');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });

      if (bbCate) bbCate.addEventListener('click', function () {
        setActiveBb(bbCate);
        var target = document.querySelector('.nav-btn.active[data-top]:not([data-top="all"])');
        if (!target || !target.dataset.children) {
          target = document.querySelector('.nav-btn[data-children]');
        }
        if (target && target.dataset.children) {
          var label = target.textContent.replace('▼', '').trim();
          openSheet(target.dataset.top, label, target.dataset.children);
        } else {
          var nav = document.querySelector('.nav-bottom-row') || document.querySelector('.navbar');
          if (nav) nav.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      });

      if (bbSearch) bbSearch.addEventListener('click', function () {
        setActiveBb(bbSearch); closeSheet();
        var nav = document.querySelector('.navbar');
        if (nav) nav.scrollIntoView({ behavior: 'smooth', block: 'start' });
        var si = document.getElementById('searchInput');
        if (si) setTimeout(function () {
          try { si.focus({ preventScroll: true }); } catch (err) { si.focus(); }
        }, 260);
      });

      if (bbContact) bbContact.addEventListener('click', function () {
        setActiveBb(bbContact); closeSheet();
        openContactSheet();
      });

      function openContactSheet() {
        var el = document.getElementById('wechatId');
        var wechat = (el && el.textContent) ? el.textContent.trim() : 'xdq880406';
        sheetTitle.textContent = '联系客服';
        sheetGrid.innerHTML =
          '<div class="contact-sheet">' +
            '<img class="contact-sheet-qr" src="wechat-qr.png" alt="微信二维码"' +
            ' onerror="this.style.display=\'none\'">' +
            '<p class="contact-sheet-tip">扫码添加微信，或复制微信号</p>' +
            '<p class="contact-sheet-id">' + escapeHtml(wechat) + '</p>' +
            '<button class="contact-sheet-copy" type="button" id="contactSheetCopy">复制微信号</button>' +
          '</div>';
        if (sheetMask) sheetMask.classList.add('show');
        if (sheetPanel) sheetPanel.classList.add('show');
        sheet.classList.add('open');
        document.body.classList.add('sheet-locked');
        openFlag = true;
        var copyBtn = document.getElementById('contactSheetCopy');
        if (copyBtn) copyBtn.addEventListener('click', function () {
          copyWechat();
          copyBtn.textContent = '已复制 ✓';
          setTimeout(function () { copyBtn.textContent = '复制微信号'; }, 1600);
        });
      }

      /* 补齐原页面缺失的 copyWechat 实现（onclick="copyWechat()" 一直在引用它） */
      if (typeof window.copyWechat !== 'function') {
        window.copyWechat = function () {
          var el = document.getElementById('wechatId');
          var text = (el && el.textContent) ? el.textContent.trim() : 'xdq880406';
          var done = function () {
            var btn = document.querySelector('.modal-copy-btn');
            if (btn) {
              if (!btn.dataset.orig) btn.dataset.orig = btn.innerHTML;
              btn.innerHTML = '已复制 ✓';
              setTimeout(function () { btn.innerHTML = btn.dataset.orig; }, 1600);
            }
          };
          var fallback = function (t) {
            var ta = document.createElement('textarea');
            ta.value = t; ta.style.position = 'fixed'; ta.style.opacity = '0';
            document.body.appendChild(ta); ta.select();
            try { document.execCommand('copy'); } catch (e) {}
            document.body.removeChild(ta);
          };
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(done).catch(function () { fallback(text); done(); });
          } else { fallback(text); done(); }
        };
      }

      /* 底部栏：手机端常驻，桌面端保留原滚动显隐 */
      function syncBottomBar() {
        if (!bottomBarEl) return;
        if (mq.matches) {
          bottomBarEl.classList.add('show');
          bottomBarEl.classList.remove('hidden');
        } else {
          bottomBarEl.classList.remove('show');
          bottomBarEl.classList.remove('hidden');
        }
      }
      syncBottomBar();
      if (mq.addEventListener) mq.addEventListener('change', syncBottomBar);
      else if (mq.addListener) mq.addListener(syncBottomBar);
      window.addEventListener('resize', syncBottomBar);
      window.addEventListener('orientationchange', syncBottomBar);

      window.__aj5Mobile = { openSheet: openSheet, closeSheet: closeSheet, syncBottomBar: syncBottomBar };
      console.log('[aj5] 移动端电商交互已就绪（≤768px 生效）');
    })();
"""


def already_patched(html):
    return '--m-bg' in html and 'initMobileEcommerce' in html and 'id="subSheet"' in html


def patch():
    if not INDEX.exists():
        print(f"[!!] 找不到 {INDEX}")
        return False
    html = INDEX.read_text(encoding='utf-8')

    if already_patched(html):
        print("[✓] index.html 已是移动端版式，跳过（幂等）")
        return True

    # 备份
    bk = BASE / "_sync_backup" / f"index_before_mobile_{datetime.now():%Y%m%d_%H%M%S}"
    bk.mkdir(parents=True, exist_ok=True)
    shutil.copy2(INDEX, bk / "index.html")
    print(f"[✓] 已备份 → {bk / 'index.html'}")

    changed = []

    # ⓪ 结构修复：原始 HTML 的 .bottom-bar-recruitment 缺 </div>，
    #    会导致 4 个按钮被嵌进它（而它移动端 display:none → 按钮全消失）。
    #    这里先补齐闭合，幂等。
    anchor = '<span>招商与售后</span>'
    ai = html.find(anchor)
    if ai > 0:
        after = ai + len(anchor)
        if not html[after:after + 120].lstrip().startswith('</div>'):
            html = html[:after] + '\n    </div>' + html[after:]
            changed.append("补recruitment闭合")

    # ① CSS：插到 </style> 之前
    if '--m-bg' not in html:
        i = html.find('</style>')
        if i < 0:
            print("[!!] 找不到 </style>，CSS 注入失败")
            return False
        html = html[:i] + CSS_BLOCK + "\n  " + html[i:]
        changed.append("CSS")

    # ② HTML：修破损的 recruitment div（原始 HTML 缺 </div>），再平级插 4 入口
    if 'id="bbHome"' not in html:
        # 锚点：<span>招商与售后</span> 之后应闭合它所在的 .bottom-bar-recruitment
        anchor = '<span>招商与售后</span>'
        ai = html.find(anchor)
        if ai > 0:
            after = ai + len(anchor)
            # 看紧跟其后是不是已经闭合了
            nxt = html[after:after + 80].lstrip()
            if not nxt.startswith('</div>'):
                html = html[:after] + '\n    </div>' + html[after:]
            # 现在按钮插在 recruitment div 之后、bottomBar 收尾 </div> 之前
            k = html.find('id="bottomBar"')
            close = html.find('</div>', html.find('</div>', k) + 6) if k > 0 else -1
            # 更稳：找 bottomBar 起始后，第一个「独立成行的 </div>」（bottomBar 的收尾）
            seg = html[html.find('>', k) + 1:]
            mc = re.search(r'\n\s*</div>', seg)
            if mc:
                pos = html.find('>', k) + 1 + mc.start()
                html = html[:pos] + BB_BUTTONS + html[pos:]
                changed.append("底部4入口")
            else:
                print("[!] 找不到 bottomBar 收尾，跳过 4 入口")
        else:
            print("[!] 找不到「招商与售后」锚点，跳过 4 入口")

    if 'id="subSheet"' not in html:
        # 插到 <script> 之前
        k = html.find('<script>')
        if k > 0:
            html = html[:k] + HTML_BLOCK + "\n  " + html[k:]
            changed.append("subSheet 弹层")
        else:
            print("[!] 找不到 <script>，弹层 HTML 注入失败")

    # ③ JS：插到 </script> 之前
    if 'initMobileEcommerce' not in html:
        k = html.rfind('</script>')
        if k > 0:
            html = html[:k] + JS_BLOCK + "\n  " + html[k:]
            changed.append("移动端JS")
        else:
            print("[!] 找不到 </script>，JS 注入失败")

    INDEX.write_text(html, encoding='utf-8')
    print(f"[✓] 已注入: {', '.join(changed)}")
    print(f"[✓] 体积: {len(html.encode('utf-8'))} bytes")
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("  移动端电商版式补丁")
    print("=" * 60)
    patch()
