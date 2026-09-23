#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
 一口价鞋款站点 · 统一同步脚本  sync.py
=============================================================================
 一条命令跑完全流程：

     python sync.py              # 全流程（默认）
     python sync.py scan         # 只整理图库 → images/ + thumbs/
     python sync.py build        # 只重建 manifest.json + index.html 数据
     python sync.py deploy       # 只增量推送 CloudBase
     python sync.py push         # 只增量推送 Netlify(GitHub)
     python sync.py cleanup      # 只清理线上冗余旧路径
     python sync.py verify       # 只做线上核验
     python sync.py status       # 只显示增量概览（不落地任何改动）

【核心原则 —— 增量，绝不重传】
  以「线上真实清单」为唯一基准（tcb hosting list --json 带 eTag/md5）：
    · 线上没有的  → 上传
    · 线上有但 md5 不同 → 上传（覆盖）
    · 线上有且 md5 相同 → 跳过
  本地同时维护 .sync_state.json 做校验与断点续传。

【标准路径（与 manifest.json / index.html 完全一致）】
  images/<大分类>/<小分类>/<文件名>      （有大分类又无小分类时：images/<大分类>/<文件名>）
  thumbs/<大分类>/<小分类>/<文件名>.webp

【安全】
  · 所有破坏性操作（删线上文件、清本地目录）先备份、先 dry-run、再执行
  · 上传/删除失败自动重试 3 次并记录
=============================================================================
"""
import os, sys, io, re, json, time, shutil, hashlib, subprocess, urllib.parse, urllib.request
from pathlib import Path
from datetime import datetime

# ─────────────────────────── 路径与常量 ───────────────────────────
BASE       = Path(r"C:\Users\Administrator.DESKTOP-K1RSGDC\WorkBuddy\2026-05-08-task-4")
GALLERY    = Path(r"C:\Users\Administrator.DESKTOP-K1RSGDC\Desktop\图库")
GALLERY_RC = Path(r"C:\Users\Administrator.DESKTOP-K1RSGDC\Desktop\图库_回收")

IMAGES_DIR = BASE / "images"
THUMBS_DIR = BASE / "thumbs"
INDEX_FILE = BASE / "index.html"
MANIFEST   = BASE / "manifest.json"
STATE_FILE = BASE / ".sync_state.json"
BACKUP_DIR = BASE / "_sync_backup"

CDN_BASE      = "https://workbuddy-d5g0sqo2r36ca45b3-1253831416.tcloudbaseapp.com"
FALLBACK_BASE = "https://cdn.jsdelivr.net/gh/qxdz888/aj5@main"
CB_ENV        = "workbuddy-d5g0sqo2r36ca45b3"

NODE     = r"C:\Users\Administrator.DESKTOP-K1RSGDC\.workbuddy\binaries\node\versions\22.12.0\node.exe"
TCB      = r"C:\Users\Administrator.DESKTOP-K1RSGDC\.workbuddy\binaries\node\workspace\node_modules\.bin\tcb.cmd"
NODE_WS  = r"C:\Users\Administrator.DESKTOP-K1RSGDC\.workbuddy\binaries\node\workspace"

GIT_REPO = "git@github.com:qxdz888/aj5.git"   # 必须用 SSH：本环境 HTTPS 走本地代理会 502
GIT_BRANCH = "main"
CLONE_DIR = BASE / "_sync_clone"

IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}
THUMB_W = 400          # 缩略图宽度
THUMB_QUALITY = 72

# ─────────────────────────── 小工具 ───────────────────────────
def log(msg, kind="•"):
    print(f"[{kind}] {msg}", flush=True)

def hr(title=""):
    print("\n" + "=" * 72)
    if title:
        print("  " + title)
        print("=" * 72)

def md5_file(p, chunk=1 << 20):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def run(cmd, cwd=None, timeout=1800, quiet=False):
    """执行外部命令，返回 (rc, out, err)（超时也会安全返回，不抛异常）"""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired as e:
        if not quiet:
            log(f"命令超时({timeout}s): {' '.join(map(str, cmd))[:120]}", "!!")
        return 124, (e.stdout or '') if isinstance(e.stdout, str) else '', \
                    (e.stderr or '') if isinstance(e.stderr, str) else 'timeout'
    except Exception as e:
        if not quiet:
            log(f"命令异常: {e}", "!!")
        return 125, '', str(e)
    if not quiet and r.returncode != 0:
        log(f"命令失败 rc={r.returncode}: {' '.join(map(str, cmd))[:120]}", "!!")
        if r.stderr:
            print(r.stderr[-1500:])
    return r.returncode, r.stdout or '', r.stderr or ''

def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {"pushed_netlify": {}, "last_run": None}

def save_state(st):
    st["last_run"] = datetime.now().isoformat(timespec='seconds')
    STATE_FILE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding='utf-8')

def backup(paths, tag):
    """把要动的东西先备份到 _sync_backup/<tag>/"""
    if not paths:
        return None
    dst = BACKUP_DIR / tag
    dst.mkdir(parents=True, exist_ok=True)
    for p in paths:
        p = Path(p)
        if not p.exists():
            continue
        t = dst / p.name
        if p.is_dir():
            if t.exists():
                shutil.rmtree(t, ignore_errors=True)
            shutil.copytree(p, t)
        else:
            shutil.copy2(p, t)
    log(f"已备份 {len(paths)} 项 → {dst}", "✓")
    return dst


# ═════════════════════════ 1. SCAN：图库 → images/ + thumbs/ ═════════════════════════
def gallery_iter():
    """
    遍历桌面图库，产出 (rel_dir, filename, abs_path)
    rel_dir 形如 'aj/乔一' 或 '潮ng'（无小分类）
    跳过 _回收 / 隐藏目录 / 非图片
    """
    if not GALLERY.exists():
        log(f"图库目录不存在：{GALLERY}", "!!")
        return
    for top in sorted(GALLERY.iterdir()):
        if not top.is_dir() or top.name.startswith(('.', '_')):
            continue
        subs = [d for d in sorted(top.iterdir()) if d.is_dir() and not d.name.startswith(('.', '_'))]
        direct = [f for f in sorted(top.iterdir())
                  if f.is_file() and f.suffix.lower() in IMAGE_EXT and not f.name.startswith('.')]
        if subs:
            # 有子目录：子目录里的图 + 大目录下直接挂的图
            for sub in subs:
                for f in sorted(sub.iterdir()):
                    if f.is_file() and f.suffix.lower() in IMAGE_EXT and not f.name.startswith('.'):
                        yield (f"{top.name}/{sub.name}", f.name, f)
            for f in direct:
                yield (top.name, f.name, f)
        else:
            for f in direct:
                yield (top.name, f.name, f)


def sync_files_to_local():
    """
    把桌面图库的图 增量同步到 BASE/images（统一转 .webp），再据此生成 BASE/thumbs。
    · 图库是 .jpg 原图 → images/ 存 .webp（网站只用 webp，体积小一半）
    · 只处理「缺失」或「源文件更新」的，未变的一律跳过（不重传、不重编码）
    """
    hr("① SCAN · 图库 → images/(.webp) + thumbs/")
    from PIL import Image

    IMAGES_DIR.mkdir(exist_ok=True)
    THUMBS_DIR.mkdir(exist_ok=True)

    added = updated = skipped = 0
    added_th = 0
    total = 0

    for rel_dir, fname, src in gallery_iter():
        total += 1
        stem = Path(fname).stem
        # 目标原图统一 .webp
        dst_img = IMAGES_DIR / rel_dir / (stem + '.webp')
        dst_img.parent.mkdir(parents=True, exist_ok=True)

        # 源图未变（目标存在且 mtime 不比源旧）→ 跳过
        if dst_img.exists() and dst_img.stat().st_mtime >= src.stat().st_mtime:
            skipped += 1
        else:
            existed = dst_img.exists()
            try:
                with Image.open(src) as im:
                    if im.mode == 'RGBA':
                        bg = Image.new('RGB', im.size, (255, 255, 255))
                        bg.paste(im, mask=im.split()[-1])
                        im = bg
                    elif im.mode != 'RGB':
                        im = im.convert('RGB')
                    # 原图限制最长边 1200，兼顾清晰与体积
                    if max(im.size) > 1200:
                        r = 1200 / max(im.size)
                        im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
                    im.save(dst_img, 'WEBP', quality=88, method=4)
            except Exception as e:
                log(f"原图转换失败 {src.name}: {e}", "!!")
                continue
            if existed:
                updated += 1
            else:
                added += 1
            # 原图变了 → 缩略图必须重生
            try:
                os.utime(dst_img, (src.stat().st_atime, src.stat().st_mtime))
            except Exception:
                pass

        # 缩略图：thumbs/<rel_dir>/<stem>.webp
        dst_th = THUMBS_DIR / rel_dir / (stem + '.webp')
        dst_th.parent.mkdir(parents=True, exist_ok=True)
        if (not dst_th.exists()) or dst_th.stat().st_mtime < dst_img.stat().st_mtime:
            try:
                with Image.open(dst_img) as im:
                    if im.mode != 'RGB':
                        im = im.convert('RGB')
                    if im.width > THUMB_W:
                        h = int(im.height * THUMB_W / im.width)
                        im = im.resize((THUMB_W, h), Image.LANCZOS)
                    im.save(dst_th, 'WEBP', quality=THUMB_QUALITY, method=4)
                os.utime(dst_th, (dst_img.stat().st_atime, dst_img.stat().st_mtime))
                added_th += 1
            except Exception as e:
                log(f"缩略图失败 {src.name}: {e}", "!!")

    log(f"图库共 {total} 张 → 新增 {added}，更新 {updated}，未变跳过 {skipped}", "✓")
    log(f"缩略图生成/更新 {added_th} 张", "✓")
    return total


# ═════════════════════════ 2. BUILD：扫描本地 → manifest + index ═════════════════════════
def scan_local():
    """扫描 LOCAL images/，返回 (brands_with_subs, standalone_brands, shoes)
    注意：images/ 里统一只保留 .webp，若出现同名其它格式会重复计数，故按 stem 去重并优先 webp。
    """
    brands_with_subs, standalone_brands, shoes = {}, [], []
    sid = 1
    if not IMAGES_DIR.exists():
        return brands_with_subs, standalone_brands, shoes

    def collect(files):
        # 按 stem 去重：优先 .webp，其次按扩展名优先级
        prio = {'.webp': 0, '.jpg': 1, '.jpeg': 2, '.png': 3}
        best = {}
        for f in files:
            if f.suffix.lower() not in IMAGE_EXT or f.name.startswith('.'):
                continue
            stem = f.stem
            p = prio.get(f.suffix.lower(), 9)
            if stem not in best or p < best[stem][0]:
                best[stem] = (p, f)
        return sorted([v[1] for v in best.values()],
                      key=lambda x: x.stat().st_mtime, reverse=True)

    for top in sorted(IMAGES_DIR.iterdir()):
        if not top.is_dir() or top.name.startswith('.'):
            continue
        subs = sorted([d for d in top.iterdir() if d.is_dir() and not d.name.startswith('.')])
        if subs:
            brands_with_subs[top.name] = []
            for sub in subs:
                files = collect(list(sub.iterdir()))
                if not files:
                    continue
                brands_with_subs[top.name].append(sub.name)
                for f in files:
                    shoes.append(mk_shoe(sid, top.name, sub.name, f))
                    sid += 1
            for f in collect(list(top.iterdir())):
                shoes.append(mk_shoe(sid, top.name, "", f))
                sid += 1
            if not brands_with_subs[top.name]:
                del brands_with_subs[top.name]
        else:
            files = collect(list(top.iterdir()))
            if not files:
                continue
            standalone_brands.append(top.name)
            for f in files:
                shoes.append(mk_shoe(sid, top.name, "", f))
                sid += 1
    # 新款标识：最近修改的 30 款打 isNew（卡片"新款"角标用）
    newest = sorted(shoes, key=lambda s: s.get('mtime', 0), reverse=True)[:30]
    for s in newest:
        s['isNew'] = True
    for s in shoes:
        s.pop('mtime', None)
    return brands_with_subs, standalone_brands, shoes


def parse_filename(filename):
    stem = Path(filename).stem
    for pat in (r'^(.+?)[-_](\d+元)$', r'^(.+?)[-_](\d+)$',
                r'^(.+?)\s+(\d+元)$', r'^(.+?)\s+(\d+)$'):
        m = re.match(pat, stem)
        if m:
            price_raw = m.group(2)
            price = f"{price_raw}元" if price_raw.isdigit() else price_raw
            return m.group(1).strip(), price, "129元"
    return stem, "面议", ""


def mk_shoe(sid, top, sub, f):
    rel = f"{top}/{sub}/{f.name}" if sub else f"{top}/{f.name}"
    name, price, sp = parse_filename(f.name)
    thumb_rel = ("thumbs/" + rel[len(""):]).rsplit('.', 1)[0] + '.webp'
    return {
        "id": sid,
        "name": name,
        "category": sub if sub else top,
        "topCategory": top,
        "subCategory": sub,
        "imgIndex": sid,
        "price": price,
        "special_price": sp,
        "image": cdn_url("images/" + rel),
        "thumb": cdn_url(thumb_rel if thumb_rel.startswith('thumbs/') else 'thumbs/' + rel.rsplit('.', 1)[0] + '.webp'),
        "mtime": f.stat().st_mtime,
    }


def cdn_url(rel):
    if rel.startswith('http'):
        return rel
    return CDN_BASE + '/' + urllib.parse.quote(rel, safe='/')


def build_manifest_and_index():
    hr("② BUILD · 重建 manifest.json + index.html 数据")
    bws, standalone, shoes = scan_local()
    log(f"扫描得到 {len(shoes)} 件商品，{len(bws)} 个大分类（含子类），{len(standalone)} 个独立大分类")

    # manifest.json
    manifest = {
        "generated": datetime.now().isoformat(timespec='seconds'),
        "count": len(shoes),
        "categories": {k: v for k, v in bws.items()},
        "standalone": standalone,
        "shoes": shoes,
    }
    backup([MANIFEST], "manifest_before_build")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    log(f"manifest.json 已写（{len(shoes)} 件）", "✓")

    # index.html：替换 const shoes = [...] 和 导航段
    html = INDEX_FILE.read_text(encoding='utf-8')
    backup([INDEX_FILE], "index_before_build")

    nav = build_nav_html(bws, standalone)
    html = re.sub(r'(<!-- AUTO_NAV_START -->)(.*?)(<!-- AUTO_NAV_END -->)',
                  lambda m: m.group(1) + "\n" + nav + "\n" + m.group(3),
                  html, flags=re.S)

    inline = build_inline(shoes)
    shoes_js = "const shoes = " + json.dumps(inline, ensure_ascii=False, indent=2) + ";"
    html2, n = re.subn(r'const shoes = \[.*?\];', shoes_js, html, count=1, flags=re.S)
    if n == 0:
        log("未找到 const shoes = [...] 段，跳过内联替换", "!!")
    else:
        html = html2

    INDEX_FILE.write_text(html, encoding='utf-8')
    log(f"index.html 已更新（导航 {len(bws) + len(standalone) + 1} 项，内联 {len(inline)} 件）", "✓")

    # 移动端电商版式补丁（幂等；确保 build 不会把移动端改造冲掉）
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("mp", BASE / "_mobile_patch.py")
        mp = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mp)
        mp.patch()
    except Exception as e:
        log(f"移动端补丁注入异常：{e}", "!!")

    # 版式轴补丁（货架版 / 清单版 + 外观设置；幂等，必须在 _mobile_patch 之后）
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("uv", BASE / "_ui_variants_patch.py")
        uv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(uv)
        uv.patch()
    except Exception as e:
        log(f"版式补丁注入异常：{e}", "!!")

    return shoes


def build_nav_html(bws, standalone):
    out = ['<button class="nav-btn active" data-top="all" data-category="all">全部</button>']
    for top, subs in bws.items():
        if not subs:
            continue
        children = ",".join(subs)
        out.append(f'''<div class="nav-dropdown">
      <button class="nav-btn nav-dropbtn" data-top="{top}" data-children="{children}">
        {top} <span class="nav-arrow">▼</span>
      </button>
      <div class="nav-dropdown-content">''')
        for s in subs:
            out.append(f'<button class="nav-btn" data-top="{top}" data-sub="{s}">{s}</button>')
        out.append('</div>')
        out.append('</div>')
    for top in standalone:
        out.append(f'<button class="nav-btn" data-top="{top}">{top}</button>')
    return "\n        ".join(out)


def build_inline(shoes):
    """首屏内联：每分类前 3 张 + 补足到 80（与 update_gallery.py 策略一致）"""
    per_cat, total = 3, 80
    by_cat, picked, seen = {}, [], set()
    for s in shoes:
        key = s['topCategory'] + '/' + s['subCategory']
        by_cat.setdefault(key, []).append(s)
    for key, arr in by_cat.items():
        for s in arr[:per_cat]:
            if s['id'] not in seen:
                picked.append(s); seen.add(s['id'])
    # 新款优先进入首屏内联
    for s in shoes:
        if s.get('isNew') and s['id'] not in seen:
            picked.append(s); seen.add(s['id'])
    for s in shoes:
        if len(picked) >= total:
            break
        if s['id'] not in seen:
            picked.append(s); seen.add(s['id'])
    return picked


# ═════════════════════════ 3. DEPLOY：增量推 CloudBase ═════════════════════════
def cb_list_json(prefix=""):
    """拉线上清单，返回 {unquoted_key: {eTag, size}}"""
    cmd = [TCB, "hosting", "list", "--json", "-e", CB_ENV]
    if prefix:
        cmd.insert(3, prefix)
    rc, out, err = run(cmd, cwd=str(BASE), timeout=600, quiet=True)
    if rc != 0 or not out.strip():
        log(f"拉线上清单失败（prefix={prefix!r}）: {err[:300]}", "!!")
        return {}
    try:
        d = json.loads(out[out.find('{'):])
    except Exception as e:
        log(f"解析线上清单 JSON 失败: {e}", "!!")
        return {}
    res = {}
    for it in d.get('data', []):
        k = urllib.parse.unquote(it['key'].lstrip('/'))
        res[k] = {"eTag": it.get('eTag', '').strip('"'), "size": int(it.get('size', 0) or 0)}
    return res


def local_assets():
    """本地待部署资产：{rel_key: (abs_path, md5)}（含 images/ thumbs/ 及静态文件）"""
    out = {}
    for root, prefix in ((IMAGES_DIR, 'images'), (THUMBS_DIR, 'thumbs')):
        if not root.exists():
            continue
        for r, _, fs in os.walk(root):
            for f in fs:
                p = Path(r) / f
                rel = prefix + '/' + p.relative_to(root).as_posix()
                out[rel] = (p, md5_file(p))
    # 站点静态文件
    for f in ("index.html", "manifest.json", "recruitment.html", "wechat-qr.png",
              "wechat-icon.png", "netlify.toml"):
        p = BASE / f
        if p.exists():
            out[f] = (p, md5_file(p))
    return out


def deploy_cloudbase(dry=False):
    hr("③ DEPLOY · 增量推送 CloudBase")
    log("拉取线上清单…")
    online = cb_list_json()
    if not online:
        log("线上清单为空或拉取失败，中止部署以避免全量重传", "!!")
        return False
    log(f"线上现有 {len(online)} 个文件")

    local = local_assets()
    log(f"本地资产 {len(local)} 个")

    to_upload, unchanged = [], 0
    for k, (p, m) in local.items():
        o = online.get(k)
        if o is None or o['eTag'] != m:
            to_upload.append((k, p))
        else:
            unchanged += 1

    log(f"需上传 {len(to_upload)} 个，未变跳过 {unchanged} 个")
    if dry:
        for k, _ in to_upload[:40]:
            log("  + " + k)
        if len(to_upload) > 40:
            log(f"  … 还有 {len(to_upload) - 40} 个")
        return True
    if not to_upload:
        log("无需上传，已是最新", "✓")
        return True

    # 按「目录批次」分组上传（tcb hosting deploy 对单目录很快；逐文件也行）
    groups = {}
    for k, p in to_upload:
        parts = k.split('/')
        grp = '/'.join(parts[:-1]) if len(parts) > 1 else ''
        groups.setdefault(grp, []).append((k, p))

    ok = fail = 0
    for grp, items in sorted(groups.items()):
        # 逐文件 deploy（tcb 支持单文件），失败重试
        for k, p in items:
            cloud = '/' + k
            done = False
            for attempt in range(3):
                rc, out, err = run([TCB, "hosting", "deploy", str(p), cloud, "-e", CB_ENV],
                                   cwd=str(BASE), timeout=180, quiet=True)
                if rc == 0 and 'error' not in (out + err).lower():
                    done = True
                    break
                time.sleep(1.2)
            if done:
                ok += 1
            else:
                fail += 1
                log(f"上传失败: {k}", "!!")
        if ok and ok % 25 == 0:
            log(f"  已上传 {ok}/{len(to_upload)}…")
    log(f"CloudBase 上传完成：成功 {ok}，失败 {fail}", "✓" if fail == 0 else "!!")
    return fail == 0


# ═════════════════════════ 4. PUSH：增量推 Netlify(GitHub) ═════════════════════════
def push_netlify():
    hr("④ PUSH · 增量提交到 Netlify（GitHub）")
    import importlib.util, sys as _s
    mod_path = BASE / "git_push_helper.py"
    if not mod_path.exists():
        log("未找到 git_push_helper.py，跳过 Netlify 推送", "!!")
        return False
    spec = importlib.util.spec_from_file_location("gph", mod_path)
    gph = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gph)
    return gph.incremental_push(BASE, CLONE_DIR, GIT_REPO, GIT_BRANCH,
                                subdirs=["images", "thumbs", ".github/workflows"],
                                files=["index.html", "manifest.json", "netlify.toml",
                                       "update_gallery.py", ".gitignore",
                                       "_mobile_patch.py", "_ui_variants_patch.py",
                                       "sync.py", "git_push_helper.py"])


# ═════════════════════════ 5. CLEANUP：清理线上冗余旧路径 ═════════════════════════
def redundant_keys(online):
    """
    以 manifest 真实需求的路径为白名单，线上的其余 images/thumbs 内容全部算冗余。
    白名单 = manifest 里所有 image / thumb 的 key（unquote 后）。
    __auth/（CloudBase 自管）与站点核心文件不在清理范围。
    """
    need = set()
    if MANIFEST.exists():
        try:
            for s in json.loads(MANIFEST.read_text(encoding='utf-8'))['shoes']:
                for f in ('image', 'thumb'):
                    u = s.get(f) or ''
                    if 'tcloudbaseapp.com/' in u:
                        need.add(urllib.parse.unquote(u.split('tcloudbaseapp.com/', 1)[1]))
        except Exception as e:
            log(f"读取 manifest 白名单失败：{e}", "!!")

    keep_top = {"__auth", "index.html", "manifest.json", "recruitment.html",
                "netlify.toml", "wechat-qr.png", "wechat-icon.png", "cloud-admin"}
    out = []
    for k in online:
        top = k.split('/')[0]
        if top == "__auth" or k in keep_top or top in keep_top:
            continue
        if k.startswith(('images/', 'thumbs/')):
            if k not in need:
                out.append(k)
        else:
            # 其他任意顶层目录/散文件（旧路径残留，如 aj/...、自z/...）
            out.append(k)
    return out


def cleanup_cloudbase(dry=False):
    hr("⑤ CLEANUP · 清理线上冗余旧路径")
    online = cb_list_json()
    if not online:
        log("拉不到线上清单，跳过", "!!")
        return

    redundant = redundant_keys(online)
    log(f"发现冗余 {len(redundant)} 个（不在 manifest 白名单内的旧路径）")
    for k in redundant[:30]:
        log("  - " + k)
    if len(redundant) > 30:
        log(f"  … 还有 {len(redundant) - 30} 个")

    if dry:
        log("（DRY RUN，未执行删除）")
        return
    if not redundant:
        log("无冗余，跳过", "✓")
        return

    # 备份待删清单
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    list_file = BACKUP_DIR / f"cleanup_list_{datetime.now():%Y%m%d_%H%M%S}.json"
    list_file.write_text(json.dumps(redundant, ensure_ascii=False, indent=2), encoding='utf-8')

    # 并发删除（tcb 单次约 1.5-5s，串行 900+ 个要 1 小时）。
    # 注意：并发过高会被 CloudBase 限流报「请求超时」，实测 5 线程较稳，
    # 失败的自动进第二轮补删队列。
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _del(k):
        for _ in range(3):
            rc, out, err = run([TCB, "hosting", "delete", "/" + k, "-e", CB_ENV],
                               cwd=str(BASE), timeout=120, quiet=True)
            if rc == 0:
                return True
            time.sleep(0.5)
        return False

    def _sweep(targets, workers, label):
        got = lost = 0
        n = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_del, k): k for k in targets}
            for f in as_completed(futs):
                k = futs[f]
                n += 1
                if f.result():
                    got += 1
                else:
                    lost += 1
                if n % 100 == 0:
                    log(f"  [{label}] 已删除 {got}/{len(targets)}…")
        return got, lost

    ok, fail = _sweep(redundant, 5, "第1轮")
    log(f"第1轮：删除 {ok}，失败 {fail}")

    # 失败补删（重新拉线上清单，只对仍存在的重试）
    if fail:
        log("拉取线上清单，准备补删…")
        still = set(cb_list_json().keys())
        pending = [k for k in redundant if k in still]
        if pending:
            log(f"第2轮补删 {len(pending)} 个…")
            g2, f2 = _sweep(pending, 4, "第2轮")
            ok += g2
            fail = f2
            log(f"第2轮：删除 {g2}，失败 {f2}")
        else:
            fail = 0
            log("线上已无残留，补删无需执行")

    log(f"清理完成：删除 {ok}，失败 {fail}", "✓" if fail == 0 else "!!")
    log(f"待删清单已备份：{list_file.name}")


# ═════════════════════════ 6. VERIFY：线上核验 ═════════════════════════
def verify_online(sample_all=True, workers=6):
    hr("⑥ VERIFY · 线上核验")
    from concurrent.futures import ThreadPoolExecutor

    shoes = json.loads(MANIFEST.read_text(encoding='utf-8'))['shoes']
    urls = []
    for s in shoes:
        urls.append(s['image'])
        urls.append(s['thumb'])
    urls = list(dict.fromkeys(urls))
    log(f"待核验 {len(urls)} 个 URL（{len(shoes)} 件商品 × 原图+缩略图）")

    def probe(u):
        for _ in range(3):
            try:
                req = urllib.request.Request(u, method='HEAD',
                                             headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as r:
                    if r.status == 200:
                        return (u, 200, '')
                    return (u, r.status, '')
            except urllib.error.HTTPError as e:
                if e.code == 403:  # 有些 CDN 不支持 HEAD，退回 GET
                    try:
                        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=15) as r:
                            r.read(64)
                            return (u, r.status, '')
                    except Exception as e2:
                        return (u, 'ERR', str(e2)[:80])
                return (u, e.code, str(e)[:80])
            except Exception as e:
                time.sleep(0.6)
                last = str(e)[:80]
        return (u, 'ERR', last)

    bad = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for i, (u, code, err) in enumerate(ex.map(probe, urls), 1):
            if code != 200:
                bad.append((u, code, err))
            if i % 100 == 0:
                log(f"  已核验 {i}/{len(urls)}…")

    log(f"核验完成：{len(urls) - len(bad)}/{len(urls)} 通过", "✓" if not bad else "!!")
    if bad:
        for u, c, e in bad[:20]:
            log(f"  ✗ {c} {u}", "!!")
    # 站点核心文件
    for f in ("index.html", "manifest.json"):
        u = f"{CDN_BASE}/{f}"
        _, code, _ = probe(u)
        log(f"  {f} → {code}")
    return not bad


# ═════════════════════════ 7. STATUS：增量概览 ═════════════════════════
def status():
    hr("STATUS · 增量概览（不改动任何东西）")
    online = cb_list_json()
    local = local_assets()
    if not online:
        log("无法拉取线上清单", "!!")
        return
    new = [k for k in local if k not in online]
    changed = [k for k in local if k in online and online[k]['eTag'] != local[k][1]]
    same = len(local) - len(new) - len(changed)
    log(f"本地资产 {len(local)} 个 ／ 线上 {len(online)} 个")
    log(f"  新增待传 : {len(new)}")
    log(f"  已变更   : {len(changed)}")
    log(f"  一致跳过 : {same}")
    stale = redundant_keys(online)
    log(f"  线上冗余 : {len(stale)}")
    for k in new[:10]:
        log("  + " + k)
    for k in changed[:10]:
        log("  ~ " + k)
    for k in stale[:10]:
        log("  - " + k)


# ═════════════════════════ 中控 ═════════════════════════
def main():
    t0 = time.time()
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry' in sys.argv or '--dry-run' in sys.argv
    cmd = args[0] if args else 'all'

    hr(f"一口价鞋款站点 · 统一同步脚本   [{cmd}]" + ("  (DRY RUN)" if dry else ""))
    log(f"项目目录: {BASE}")
    log(f"图库目录: {GALLERY}")

    if cmd == 'status':
        status()
    elif cmd == 'scan':
        sync_files_to_local()
    elif cmd == 'build':
        build_manifest_and_index()
    elif cmd == 'deploy':
        deploy_cloudbase(dry=dry)
    elif cmd == 'push':
        push_netlify()
    elif cmd == 'cleanup':
        cleanup_cloudbase(dry=dry)
    elif cmd == 'verify':
        verify_online()
    elif cmd == 'all':
        sync_files_to_local()
        build_manifest_and_index()
        deploy_cloudbase(dry=dry)
        push_netlify()
        cleanup_cloudbase(dry=dry)
        verify_online()
    else:
        print(__doc__)
        return

    hr(f"完成，用时 {time.time() - t0:.1f}s")


if __name__ == '__main__':
    main()
