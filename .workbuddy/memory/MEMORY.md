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
- **节日模式与运费规则（2026-10-17 上线，老板定）**：
  - **FESTIVALS 表 7 节日每年自动生效**：元旦 1/1-1/3、年货节 1/15-2/15、劳动节 5/1-5/5、618 6/1-6/20、国庆 10/1-10/7、双11 11/1-11/11、双12 12/1-12/12；`isPromoNow()` 按页面当前年份构造区间（一次配置永久有效）；实际特惠区间 = 节日 + 节前5天 + 节后1天
  - `body.festival-mode` 节日皮肤由 `resolveUiMode()` 驱动：localStorage `aj5_ui_mode` = auto（默认，跟随时间）/daily/festival；**URL 参数 `?mode=` 优先**（预览用）；`startUiModeGuard()` 每 60s 轮询，跨节日界限自动切+重渲染
  - **currentPromo 机制**：运费与价格特惠跟随当前生效 UI 模式（`applyUiMode` 时更新），手动/预览开节日也全套联动；非aj 节日价 = 原价−10，aj 恒129+节日标签
  - **运费双规则 `getShippingText(isPromo)`**：日常「运费 7 元 · 两双以上 10 元 封顶」/ 节日「单双运费 7 元 · 两双以上包邮」；节日态详情页运费加 `.promo` 琥珀高亮
  - 时序坑：hash 直开详情页先于 initUiMode 执行会用旧特惠状态 → initUiMode 里 modal 激活时按新模式重开一次（已修）
  - **每节日一版 UI（2026-10-17 老板定）**：CSS 令牌体系 `--f-*` 上加 `body.festival-mode.festival-<key>` 7 套覆盖块（元旦玫红金/年货节灯笼红金/劳动节橙/618亮红/国庆国旗红+荣誉金/双11天猫红/双12淘宝橙），banner 全套变量化 `--f-banner-*`（背景渐变/流光/标题渐变字）；FESTIVALS 表每项带 emoji/desc，applyUiMode 挂 `festival-<key>` class + 横幅三件套（emoji 独立 span 不走渐变字，否则被 text-fill-color 裁掉）；`previewFestivalKey()` 给手动/预览选应季主题（默认 cny）；guard 比对「节日 key」而非布尔（双11→双12 要重挂）；**`?fest=<key>` 强制指定节日主题预览**（如 `?fest=double11`），daily 偏好优先
  - **节日特惠价覆盖特惠价（2026-10-17）**：priceHTML 节日期用 promoLabel（「双11狂欢价」等）当 label 替代「特惠价」字样，不并排两个价标签（删了 price-promo-tag 小标签及 CSS）；效果：节日 aj「零售价169元 双11狂欢价129元」/ 日常 aj「零售价169元 特惠价129元」/ 非aj 节日「零售价159元 双11狂欢价149元」
  - 副站 520aj 轻量节日化：7 主题 banner 令牌 + #festivalBanner（nav 后 margin-top:70px 避让 fixed navbar，节日时 .banner margin-top 清零）；FESTIVALS_520 带 emoji/desc/promoLabel，isPromoNow520 返回 {active,festival}；IIFE initFestivalTheme520 + 60s 守护；支持 ?fest=
- **价格与详情页规则（2026-10-14 上线，老板确认）**：
  - 零售价 = 图片文件名后缀（`8033冰蓝红-189.webp` → name=8033冰蓝红, price=189元），由 parse_filename 拆解
  - 特惠价规则收敛在**前端** `calcPrice()`：`topCategory==='aj'` 恒 129 元（双行展示：零售价划线+特惠价红字）；非 aj（潮ng/潮rez/鸿b/自z）只显示零售价；节日特惠期非aj减10元的逻辑保留
  - 数据层 `special_price` 已清空（update_gallery.py 不再写死129），副站 priceHTML 按同样规则独立实现
  - 详情页 = 点图全屏（左大图深色区 + 右浅色信息面板 #f6f6f7/#1f2329，严禁黑配灰）；含名称/零售价/特惠价/运费7元/退换货说明「退换货运费买家承担！」/客服区（主站有二维码）
  - hash 路由 `#p-商品id` 可刷新/分享直达详情页
  - 列表卡片同步双行价格；layout-shelf/list 浅色布局的 `.price-plain` 必须补 var(--v-price) 覆盖（否则白字白底）
- **新款/热销角标规则（2026-10-14 上线，老板确认：不要滞销，只要新款+热销）**：
  - 新款 = 销售软件 goods.**create_at** 最新30个线上在售款式；**热销（2026-10-14 晚改口径）= 近30天有销量（sale_items JOIN sales，s.in_out=1 且 opt_date≥now-30d）且总销量≥20双，按总销量降序取30款**（口径对齐桌面 `滞销分析报表.py`；实测恰好30款候选）；关联键 (goods.name, sale_price) ↔ 网站 (name, price)
  - 生成器 `gen_badges.py` → `badges.json`（{name|price: new/hot}）；`update_gallery.apply_badges()` 与 **sync.py scan_local 两条链路都要合并**（sync.py 有独立 build，只在 update_gallery 加会被洗掉）
  - 已删除 sync.py scan_local 的 mtime isNew 逻辑（转图时间≠上架时间，口径错误）
  - 前端：卡片右上角 absolute（`.card-badge--new` 蓝 #1677ff / `.card-badge--topsell` 红 #f53f3f）；详情页名称后 static；函数 newBadge()/hotBadge()，副站同构
  - 副站数据自动跟主站 manifest（fetch aj5.netlify.app/manifest.json），无需单独生成
  - **首页新款优先（2026-10-14）**：`sort_new_first()` 把 badge=new 整批前置（只改顺序不改 id）；build_inline 也必须让新款整批先入选首屏80件，否则"每分类前3+补足"会把新款打散
  - **补货脚本已集成角标自动更新（2026-10-14 晚）**：`auto_sync()` 第2步跑 `gen_badges.py`（scan+build 之后），badges.json 内容有变则再 build 一次合入，且角标变化会强制触发同步（无新图也推）；`_run_py()`/`_badges_dict()` 为新增辅助函数；以后老板双击补货脚本 = 图库→角标→网站全自动
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
  - ⚠️ **sync.py main() 多命令 bug（2026-10-14 晚修复）**：原 main() 只取 `args[0]`，`sync.py deploy push cleanup verify` 实际**只跑 deploy**，push/cleanup/verify 全被静默跳过（auto_sync 第3步就是这个四命令调用 → 角标刷新后 push 从未执行，commit 停留旧口径）→ 已改为 for 循环遍历 args 依次执行；**教训：验证"已推送"不能只看 deploy 退出码，要 `git log` 核对 commit 内容**
  - sync.py 的 `parse_filename` 曾写死 `special_price="129元"`（与 update_gallery 口径不一致，2026-10-14 晚清空）；前端 calcPrice 不读 special_price，特惠价按 topCategory 决定，清了不影响显示

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
