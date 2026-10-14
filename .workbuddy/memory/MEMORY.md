# 项目长期笔记

## 仓库分支约定
- 主站 aj5：分支 main
- 副站 520aj：分支 **master**（github.com:qxdz888/520aj.git），push 用 git push origin master，勿用 main

## 图片 CDN 约定（2026-09-20 起改用国内图床）
- 站点图片走**国内图床**：`https://workbuddy-d5g0sqo2r36ca45b3-1253831416.tcloudbaseapp.com/<相对路径>`（CloudBase 国内 CDN，免备案）
- 由 update_gallery.py 的 `cdn_url()` 统一生成（中文路径 percent-encode），不要手改 URL
  - `CDN_BASE` = 国内图床（主源），`FALLBACK_BASE` = jsDelivr（回退）
- 前端 `imgFallback()` 兜底：图片加载失败自动把主源前缀换成 jsDelivr，每张图只回退一次（卡片 img 的 onerror + 弹窗 modalImage.onerror）
- **老站地址不变**（aj5.netlify.app / 520aj.netlify.app），只换图片源；缩略图实测 0.36s vs jsDelivr 2.42s，提速 6.8 倍
- ⚠️ 图片现在存两处：GitHub（备份）+ CloudBase（供图），**加新图必须两边都更新**，否则网站裂图
- 换图统一入口：`python sync.py`（扫描图库→转webp/缩略图→build manifest/index→增量deploy CloudBase→push GitHub/Netlify→cleanup→verify 一条龙）
- 本地放图目录：`Desktop\图库\<大分类>\<小分类>\`（原图 jpg/png 即可），sync.py 自动转 webp + 生成 400px 缩略图
- **图库两级结构（2026-10-13 定型，老板确认 adidas 归 aj）**：`图库\aj\<子分类>\`（12 类：312/adidas/lv/nk高帮/puma/wans/乔一/亚瑟/小空军/开拓者/空军/运动款，240张）；`图库\自z\<回力|皮鞋>\`（自z 直接17张+两子类4张）；潮ng/潮rez/鸿b 保持一级平铺。共 336 张，与 `images/` 结构一一对应
- 单步可拆：`sync.py scan|build|deploy|push|cleanup|verify|status`
- **价格与详情页规则（2026-10-14 上线，老板确认）**：
  - 零售价 = 图片文件名后缀（`8033冰蓝红-189.webp` → name=8033冰蓝红, price=189元），由 parse_filename 拆解
  - 特惠价规则收敛在**前端** `calcPrice()`：`topCategory==='aj'` 恒 129 元（双行展示：零售价划线+特惠价红字）；非 aj（潮ng/潮rez/鸿b/自z）只显示零售价；节日特惠期非aj减10元的逻辑保留
  - 数据层 `special_price` 已清空（update_gallery.py 不再写死129），副站 priceHTML 按同样规则独立实现
  - 详情页 = 点图全屏（左大图深色区 + 右浅色信息面板 #f6f6f7/#1f2329，严禁黑配灰）；含名称/零售价/特惠价/运费7元/退换货说明「退换货运费买家承担！」/客服区（主站有二维码）
  - hash 路由 `#p-商品id` 可刷新/分享直达详情页
  - 列表卡片同步双行价格；layout-shelf/list 浅色布局的 `.price-plain` 必须补 var(--v-price) 覆盖（否则白字白底）
- **新款/热销角标规则（2026-10-14 上线，老板确认：不要滞销，只要新款+热销）**：
  - 新款 = 销售软件 goods.**create_at** 最新30个线上在售款式；热销 = sale_items 累计销量前40款；关联键 (goods.name, sale_price) ↔ 网站 (name, price)
  - 生成器 `gen_badges.py` → `badges.json`（{name|price: new/hot}）；`update_gallery.apply_badges()` 与 **sync.py scan_local 两条链路都要合并**（sync.py 有独立 build，只在 update_gallery 加会被洗掉）
  - 已删除 sync.py scan_local 的 mtime isNew 逻辑（转图时间≠上架时间，口径错误）
  - 前端：卡片右上角 absolute（`.card-badge--new` 蓝 #1677ff / `.card-badge--topsell` 红 #f53f3f）；详情页名称后 static；函数 newBadge()/hotBadge()，副站同构
  - 副站数据自动跟主站 manifest（fetch aj5.netlify.app/manifest.json），无需单独生成
- **补货脚本一键全链路**（老板的 `Desktop\补货脚本最终版.py`）：`__main__` 已串成 `sync_gallery()` → `main()` → `auto_sync()`
  - `sync_gallery()`：销售软件 DB(clothing.db)+productImg(421张) → `Desktop\图库`（增量复制 + 下架/改价旧图移回收站，不删除）；**分类映射**：软件分类名 → `图库\aj\<分类>\`（12个aj子类）/ `图库\自z\<分类>\`（回力皮鞋）/ 其余一级平铺，由 `gallery_subdir()` 统一处理
  - `main()`：读图库按款式加尺码文字导出到 `Desktop\日期\`（补货）
  - `auto_sync()`：图库→网站自动同步（**修复后顺序**：scan→build→status判定→有新增/变更才 deploy+push+cleanup+verify；全程写日志 `桌面\网站同步日志.txt`；末尾 `input()` 暂停防窗口秒关）
  - 数据流：销售软件 → 图库 → 网站；**补货只读取图库**，不是推网站触发点（老板 2026-10-13 纠正）
  - 修过 `sync_gallery` 两处 bug：缺 `import sqlite3`；回收判断用2元组查3元组集合会误删全部图库（dry-run 拦截）
  - 修过 `auto_sync` 致命逻辑：旧版先 `status`(比 images/) 再决定，但新图还在【图库】未进 images/ → 误判 0 新增跳过 → 新图永不上传（2026-10-13 修）
  - 图库首次从95款补齐到336款（=软件有效图数）；之后纯增量；2026-10-13 又发现并部署 10 款 backlog（336→346）
  - ⚠️ 历史乌龙（2026-10-13）：曾误以为"9-19 把导航改平铺了"，实际线上导航/图片路径一直是 aj 两级，乱的只是桌面图库平铺+空壳；已迁移对齐
  - 现环境 managed venv 已装 Pillow，可在 WorkBuddy 直接跑 `sync.py` 全流程（不用等老板双击）
  - ⚠️ 同步推送机制（2026-10-13 修正）：`sync.py` 的 `push_netlify()` 已改为**直接用本地 git 命令行**（`git -C BASE add 网站资产 + commit + push origin main`），不再用 `git_push_helper.incremental_push`（dulwich 独立 clone 推送，会漏提交 index.html 且吞异常）；同时**已禁用 `.github/workflows/auto-update.yml` 的自动触发**（`on:` 仅 `workflow_dispatch`），否则每次 push 被它重跑 `update_gallery.py` 只 `git add index.html` 覆盖正确版本 → 死循环

## 国内部署包（CloudBase）
- 用 `build_cloudbase_package.py` 生成 `dist-cloudbase.zip`（图片改回相对路径，全站自包含）
- 上传到腾讯云 CloudBase 静态托管，用**默认域名**（`xxx.tcloudbaseapp.com`）免备案 + 国内CDN + 免费（1GB存储/5GB流量月）
- 更新图片流程（现用 `sync.py` 取代手动打包）：`sync.py deploy` 增量推 CloudBase，`sync.py push` 推 GitHub/Netlify；`build_cloudbase_package.py` 仅作全站自包含备份用
- 老板的域名是平台二级域名，**无法备案**，绑自定义域名走国内节点这条路不可用

## CloudBase 续期机制
- **无法自动化续期**：0元续6个月是控制台营销活动，必须人工发社交平台帖子+传截图+AI验证，无API可用（CLI `tcb env renew` 是付费的）
- 半自动方案：桌面 `CloudBase到期续期包.md`（步骤+现成文案，第六节表格已填到期信息） + automation 到期提醒
- **查到期日不用进控制台**：已登录的 CLI 直接 `tcb env list`，输出表含 Expiration time（2026-09-24 实测可用）
- **当前到期：2027-03-20 23:59:59**（环境 workbuddy-d5g0sqo2r36ca45b3，2026-09-20 开通，体验版 6 个月）
  - 可续期窗口：2027-02-18 ~ 2027-03-20（仅到期前 1 个月内）
  - 提醒已设两档：D-30 `e03918c5`（2027-02-18 09:00）、D-7 `fdc4626f`（2027-03-13 09:00）
  - 续期成功后要更新 md 表格 + 重设下一轮两档提醒
- 免费环境不支持自动续费和按量付费 → 永不自动扣费；到期不续则站停（数据仍在，续了恢复）

## CloudBase 远程部署工具链（已装好）
- CLI：`C:/Users/Administrator.DESKTOP-K1RSGDC/.workbuddy/binaries/node/workspace/node_modules/@cloudbase/cli/bin/tcb`（v3.8.3），用 managed node 直接跑
- 登录：`tcb login --cloudbase-api-key <key> -e <envId>`（环境级 API Key，控制台「环境管理 → API Key 配置 → 服务端」创建）
- 上传：`tcb hosting deploy dist-cloudbase/ -e <envId> --safe --verify`
- 打包：`python build_cloudbase_package.py`（生成 dist-cloudbase.zip，图片改回相对路径自包含）
- 以后换图流程：update_gallery.py → build_cloudbase_package.py → hosting deploy（有密钥则我全程代劳）

## 国内站已上线（2026-09-20）
- 环境 ID：`workbuddy-d5g0sqo2r36ca45b3`（免费 6 个月）
- **默认域名：https://workbuddy-d5g0sqo2r36ca45b3-1253831416.tcloudbaseapp.com/**（免备案，直接可用）
- 部署经验：约 8 分钟/674 文件；并行上传常报 `socket hang up`，**CLI 会自动转串行重试补齐，别中断、别降并发**，建议后台跑
- 刚部署完访问可能短暂 404（CDN 未同步），等几分钟自愈；验证务必带 `Cache-Control: no-cache`
- 到期日待老板确认后，把 automation `e03918c5` 改成 D-30 / D-7 两档提醒
- 实测（2026-09-20，贵州电信）：CloudBase 首页 **0.50s** vs Netlify 主站 3.32s / 副站 2.95s / jsDelivr 图片 3.17s → 国内站快约 6 倍
- 老站（aj5.netlify.app / 520aj.netlify.app）实测仍全部 200，继续保留当备份，不删
- **现兼作两站图床**：老站图片全部指向它（老地址不变），所以 CloudBase 到期会影响老站图片——已有 jsDelivr 回退兜底，不会白图
