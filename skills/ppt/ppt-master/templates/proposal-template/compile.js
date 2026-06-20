/* ============================================================================
 * 立项报告 PPT 模板 — 基于共享布局库
 *
 * 使用方法:
 *   1. 复制此目录到项目工作目录
 *   2. 修改下方 CONFIG 和各 slide 函数中的文本内容
 *   3. 运行: node compile.js
 *
 * 依赖: ../../lib/pptx-render-fix.js + ../../lib/pptx-layouts.js
 * ========================================================================== */

var path = require("path");
var fs = require("fs");
var PptxGenJS = require("pptxgenjs");
var fix = require("../../lib/pptx-render-fix");
var layouts = require("../../lib/pptx-layouts");

/* ======================== 项目配置（修改这里） ======================== */
var CONFIG = {
  projectName: "XX会员系统立项方案",
  subtitle: "以会员资产沉淀为核心，重建停车、营销与商户协同能力",
  clientName: "XX商业管理有限公司",
  reportDept: "立项汇报",
  date: "2026年6月",
  outputPath: "./output/proposal.pptx",
  coverTags: ["会员沉淀", "停车联动", "美团抖音打通"],
};

var pptx = new PptxGenJS();
pptx.layout = "LAYOUT_WIDE";
pptx.author = "蓝联科技";
pptx.company = "蓝联科技";
pptx.title = CONFIG.projectName;
pptx.lang = "zh-CN";
pptx.theme = { headFontFace: "Microsoft YaHei", bodyFontFace: "Microsoft YaHei", lang: "zh-CN" };

fix.patchPresentation(pptx);
var L = layouts.createLayouts(pptx);
var C = L.C;

/* ======================== Slide 1: 封面 ======================== */
function slide01Cover() {
  var s = pptx.addSlide();
  L.addBg(s, C.deep);
  s.addShape(pptx.ShapeType.rect, { x: 9.75, y: -0.1, w: 4.1, h: 7.9, fill: { color: C.teal, transparency: 82 }, rotate: -7 });
  s.addShape(pptx.ShapeType.rect, { x: 11.05, y: 0.2, w: 1.2, h: 6.4, fill: { color: C.amber, transparency: 76 }, rotate: -7 });
  s.addText(CONFIG.projectName, { x: 0.78, y: 1.1, w: 7.8, h: 0.72, fontFace: "Microsoft YaHei", fontSize: 27, bold: true, color: C.white, margin: 0 });
  s.addText(CONFIG.subtitle, { x: 0.82, y: 2.02, w: 6.4, h: 0.48, fontFace: "Microsoft YaHei", fontSize: 15, color: "D6E2EA", margin: 0 });
  CONFIG.coverTags.forEach(function (t, i) {
    L.addSectionLabel(s, 0.84 + i * 1.45, 2.78, 1.16, t, i === 1 ? "teal" : i === 2 ? "amber" : "blue");
  });
  s.addText(CONFIG.reportDept, { x: 9.65, y: 1.24, w: 2.15, h: 0.24, fontFace: "Microsoft YaHei", fontSize: 11, bold: true, color: C.white, align: "center", fill: { color: "2C4E69", transparency: 8 }, line: { color: "88A8BB", pt: 0.8 }, radius: 0.1, margin: 0.02 });
  L.addCard(s, { x: 0.8, y: 3.45, w: 3.3, h: 1.68, title: "本次立项重点", body: ["先上线1个试点项目", "3个月完成3个项目上线", "首年预算30万元"], fill: "17314A", line: "3A5671", accent: C.coral, titleSize: 16, bodySize: 11.2 });
  L.addCard(s, { x: 4.35, y: 3.45, w: 3.15, h: 1.68, title: "目标导向", body: ["把停车做成会员入口", "把活动做成会员资产", "把平台券做成商场工具"], fill: "17314A", line: "3A5671", accent: C.teal, titleSize: 16, bodySize: 11.2 });
  s.addText("汇报部门：" + CONFIG.reportDept, { x: 0.84, y: 6.4, w: 2.2, h: 0.2, fontFace: "Microsoft YaHei", fontSize: 11, color: "D6E2EA", margin: 0 });
  s.addText("汇报对象：公司管理层", { x: 0.84, y: 6.68, w: 2.8, h: 0.2, fontFace: "Microsoft YaHei", fontSize: 11, color: "D6E2EA", margin: 0 });
  s.addText(CONFIG.date, { x: 10.75, y: 6.82, w: 1.5, h: 0.2, fontFace: "Microsoft YaHei", fontSize: 11, color: "D6E2EA", align: "right", margin: 0 });
}

/* ======================== Slide 2: 管理层摘要 ======================== */
function slide02Summary() {
  var s = pptx.addSlide();
  L.addBg(s, C.paper);
  L.addTopBand(s, "一页结论", "管理层摘要", 2);
  L.addMetricCard(s, 0.7, 1.82, 3.8, 1.65, { main: C.blue, soft: C.blueSoft, bg: C.white }, "3件事", "本次立项要解决", "沉淀会员资产、打通停车消费、掌握营销主导权");
  L.addMetricCard(s, 4.78, 1.82, 3.8, 1.65, { main: C.teal, soft: C.tealSoft, bg: C.white }, "3个月", "实施节奏", "先试点、后复制，3个月完成3个项目上线");
  L.addMetricCard(s, 8.86, 1.82, 3.8, 1.65, { main: C.amber, soft: C.amberSoft, bg: C.white }, "30万元", "首年预算", "首年3个项目统一建设，次年维护3万元/年");
  L.addCard(s, { x: 0.7, y: 4.02, w: 5.75, h: 2.02, title: "为什么这件事现在必须做", body: ["本地头部项目已形成更高会员服务预期", "停车、活动、商户营销数据仍未形成自有资产", "商场需要通过统一平台券重建营销主导权"], accent: C.coral });
  L.addCard(s, { x: 6.72, y: 4.02, w: 5.95, h: 2.02, title: "本次建议直接拍板的事项", body: ["同意启动会员系统项目，一期打通美团/抖音本地生活", "同意首期纳入停车、券、活动核销、平台API对接核心能力", "同意采用分阶段上线与分阶段验收方式"], accent: C.blue });
}

/* ======================== Slide 3: 立项必要性 ======================== */
function slide03Urgency() {
  var s = pptx.addSlide();
  L.addBg(s, C.white);
  L.addTopBand(s, "为什么现在必须做", "立项必要性", 3);
  L.addCard(s, { x: 0.72, y: 1.82, w: 3.9, h: 3.9, title: "如果不做", body: ["活动、停车、消费带来的用户无法沉淀为会员资产", "停车仍停留在服务能力层面，没有形成经营入口", "商户以自投平台营销为由争取减租，商场主导权偏弱", "与福州本地头部项目相比，体验差距将继续扩大"], accent: C.red });
  L.addCard(s, { x: 4.86, y: 1.82, w: 3.9, h: 3.9, title: "如果现在做", body: ["先把高频停车场景转成会员入口", "先把平台流量回收到商场自有会员池", "先把联合营销规则建立起来，再谈长期协同"], accent: C.teal });
  L.addCard(s, { x: 9.0, y: 1.82, w: 3.6, h: 3.9, title: "IT部判断", body: ["必要性明确", "业务价值明确", "可先试点后复制", "预算和风险可控"], accent: C.amber });
  L.addBottomStatement(s, "会员系统不是补一个工具，而是在补未来经营所需的数字化底座", "coral");
}

/* ======================== Slide 4: 对标分析 ======================== */
function slide04Benchmark() {
  var s = pptx.addSlide();
  L.addBg(s, C.paper);
  L.addTopBand(s, "本地市场已经有参照", "对标分析", 4);
  L.addCard(s, { x: 0.72, y: 1.82, w: 3.8, h: 3.95, title: "福州万象城", body: ["统一会员入口承接积分、停车、活动、品牌信息", "停车收费、线上缴费、会员绑定车牌等能力成熟", "让顾客对会员+停车+权益形成明确预期"], accent: C.blue });
  L.addSectionLabel(s, 1.82, 5.96, 1.55, "统一入口参照", "blue");
  L.addCard(s, { x: 4.78, y: 1.82, w: 3.8, h: 3.95, title: "福州东二环泰禾", body: ["可见自助积分、线上领券、积分兑礼、智慧停车能力", "小程序已成为会员经营阵地，而非信息展示页", "为本地消费者建立了成熟数字化体验参照"], accent: C.teal });
  L.addSectionLabel(s, 5.88, 5.96, 1.55, "本地运营参照", "teal");
  L.addCard(s, { x: 8.84, y: 1.82, w: 3.8, h: 3.95, title: "行业头部项目", body: ["华润、大悦城、龙湖、万达均把会员系统作为经营底盘", "趋势已从活动管理升级到会员资产经营", "会员系统已成为商业项目基础设施而非可选项"], accent: C.amber });
  L.addSectionLabel(s, 9.94, 5.96, 1.55, "行业方向参照", "amber");
  L.addBottomStatement(s, "对标不是照搬，而是说明福州市场已进入更高会员经营阶段", "blue");
}

/* ======================== Slide 5: 建设蓝图 ======================== */
function slide05Blueprint() {
  var s = pptx.addSlide();
  L.addBg(s, C.white);
  L.addTopBand(s, "会员系统建设蓝图", "建设范围", 5);
  var boxes = [
    ["会员底座层", "注册 / 等级 / 标签 / 资产"],
    ["权益积分层", "积分规则 / 自助积分 / 兑礼"],
    ["停车联动层", "车牌绑定 / 权益 / 订单"],
    ["营销工具层", "优惠券 / 券包 / 美团抖音API对接"],
    ["活动运营层", "发布 / 报名 / 签到 / 核销"],
    ["会员前端阵地层", "小程序首页 / 会员中心 / 领券"],
    ["复盘分析层", "会员 / 活动 / 消费 / 优惠"]
  ];
  boxes.forEach(function (b, i) {
    var row = i < 4 ? 0 : 1;
    var col = i < 4 ? i : i - 4;
    var x = 0.8 + col * 3.05;
    var y = row === 0 ? 2.0 : 4.18;
    var tone = i % 3 === 0 ? C.blue : i % 3 === 1 ? C.teal : C.amber;
    var soft = i % 3 === 0 ? C.blueSoft : i % 3 === 1 ? C.tealSoft : C.amberSoft;
    s.addShape(pptx.ShapeType.roundRect, { x: x, y: y, w: 2.75, h: 1.45, rectRadius: 0.08, line: { color: tone, pt: 1.2 }, fill: { color: soft } });
    s.addText(b[0], { x: x + 0.18, y: y + 0.24, w: 2.38, h: 0.26, fontFace: "Microsoft YaHei", fontSize: 15, bold: true, color: C.ink, align: "center", margin: 0 });
    s.addText(b[1], { x: x + 0.16, y: y + 0.76, w: 2.42, h: 0.26, fontFace: "Microsoft YaHei", fontSize: 10.5, color: C.inkSoft, align: "center", margin: 0 });
    if (row === 0) { s.addShape(pptx.ShapeType.chevron, { x: x + 2.8, y: y + 0.55, w: 0.16, h: 0.26, fill: { color: tone } }); }
  });
  L.addCard(s, { x: 9.82, y: 4.18, w: 2.58, h: 1.45, title: "建设原则", body: "先核心闭环，先试点复制，先抓高频场景，再逐步扩展。", accent: C.coral, titleSize: 15, bodySize: 10.6 });
  L.addBottomStatement(s, "一期重点不是做全，而是先把会员、停车、券、活动四条链路跑通", "teal");
}

/* ======================== Slide 6: 核心闭环 1/4 — 停车 ======================== */
function slide06Parking() {
  var s = pptx.addSlide();
  L.addBg(s, C.paper);
  L.addTopBand(s, "核心闭环 1/4  把停车从配套服务变成会员经营入口", "核心场景", 6);
  s.addText("先抓住高频到店场景，再建立会员识别与复购链路", { x: 0.74, y: 1.65, w: 6.0, h: 0.22, fontFace: "Microsoft YaHei", fontSize: 12, color: C.inkSoft, margin: 0 });
  L.addFlowDiagram(s, { x: 0.72, y: 2.0, w: 7.0, h: 4.22, title: "到店停车闭环", tone: C.blue, soft: C.blueSoft, footerTags: ["高频入口", "感知最强", "易于拉新"], steps: [
    { icon: "P", title: "到店停车", desc: "顾客进入停车场" },
    { icon: "卡", title: "绑定车牌", desc: "会员身份与车辆关联" },
    { icon: "购", title: "场内消费", desc: "消费行为进入会员体系" },
    { icon: "券", title: "触发权益", desc: "等级积分消费联动减免" },
    { icon: "付", title: "线上缴费", desc: "减免与支付一体完成" },
    { icon: "数", title: "沉淀数据", desc: "形成到店与复购记录" }
  ]});
  L.addThreeExplainCards(s, { x: 8.0, y: 2.02, w: 4.62, cardH: 1.22, accent: C.blue, cards: [
    { title: "为什么要做", body: ["停车是顾客感知最强的高频场景", "与会员挂钩后才能形成复购抓手"] },
    { title: "怎么做", body: ["会员注册后绑定车牌", "消费、等级、积分联动停车权益"] },
    { title: "有什么价值", body: ["提升会员注册率和车牌绑定率", "形成到店-消费-识别-复购闭环"] }
  ]});
  L.addBottomStatement(s, "停车不是成本项，而是最适合会员运营的高频入口", "blue");
}

/* ======================== Slide 7: 核心闭环 2/4 — 平台券 ======================== */
function slide07Coupon() {
  var s = pptx.addSlide();
  L.addBg(s, C.white);
  L.addTopBand(s, '核心闭环 2/4  打通美团/抖音本地生活，重建商场营销主导权', "核心场景", 7);
  s.addText("一期重点打通美团本地生活与抖音生活服务，由商场统一掌握平台券与营销节奏", { x: 0.74, y: 1.65, w: 11.0, h: 0.22, fontFace: "Microsoft YaHei", fontSize: 12, color: C.inkSoft, margin: 0 });
  L.addFlowDiagram(s, { x: 0.72, y: 2.0, w: 7.0, h: 4.22, title: "美团/抖音平台券联合营销闭环", tone: C.coral, soft: C.coralSoft, footerTags: ["美团打通", "抖音打通", "统一核销"], steps: [
    { icon: "配", title: "统一配置券", desc: "商场统一设计平台券与组合券" },
    { icon: "美", title: "美团投放", desc: "美团本地生活API统一投放核销" },
    { icon: "抖", title: "抖音投放", desc: "抖音生活服务API统一投放核销" },
    { icon: "到", title: "顾客到店", desc: "领券后到店消费，商户核销" },
    { icon: "回", title: "数据回流", desc: "核销效果回流会员系统沉淀" },
    { icon: "盘", title: "统一复盘", desc: "评估平台ROI和商户贡献" }
  ]});
  L.addThreeExplainCards(s, { x: 8.0, y: 2.02, w: 4.62, cardH: 1.22, accent: C.coral, cards: [
    { title: "为什么要做", body: ["商户自投美团/抖音营销后常以此争取租金让渡", "平台流量不回流会员系统只能形成一次性交易"] },
    { title: "怎么做", body: ["一期打通美团本地生活+抖音生活服务API", "商场统一配置券、统一编号、统一核销、统一复盘"] },
    { title: "有什么价值", body: ["商场重新掌握营销工具和话语权", "把减租谈判转向联合经营"] }
  ]});
  L.addBottomStatement(s, "商场出工具、商户得销量、美团抖音流量回流会员池", "coral");
}

/* ======================== Slide 8: 核心闭环 3/4 — 活动 ======================== */
function slide08Activity() {
  var s = pptx.addSlide();
  L.addBg(s, C.paper);
  L.addTopBand(s, '核心闭环 3/4  让活动从热闹一次变成沉淀一次会员资产', "核心场景", 8);
  s.addText("把活动执行流程标准化，把活动结果数据化", { x: 0.74, y: 1.65, w: 6.0, h: 0.22, fontFace: "Microsoft YaHei", fontSize: 12, color: C.inkSoft, margin: 0 });
  L.addFlowDiagram(s, { x: 0.72, y: 2.0, w: 7.0, h: 4.22, title: "会员活动运营闭环", tone: C.teal, soft: C.tealSoft, footerTags: ["可追踪", "可复用", "可沉淀"], steps: [
    { icon: "发", title: "活动发布", desc: "活动统一在线发布" },
    { icon: "报", title: "会员报名", desc: "会员在线报名和预约" },
    { icon: "筛", title: "资格校验", desc: "等级积分消费门槛校验" },
    { icon: "签", title: "现场签到", desc: "到场扫码签到" },
    { icon: "销", title: "活动核销", desc: "参与状态与履约状态沉淀" },
    { icon: "标", title: "参与标签", desc: "活动后自动形成标签和召回名单" }
  ]});
  L.addThreeExplainCards(s, { x: 8.0, y: 2.02, w: 4.62, cardH: 1.22, accent: C.teal, cards: [
    { title: "为什么要做", body: ["传统活动重执行轻沉淀，做完就结束", "很难识别哪些会员真正值得继续运营"] },
    { title: "怎么做", body: ["活动统一在线发布和报名", "现场扫码签到核销并沉淀参与标签"] },
    { title: "有什么价值", body: ["降低活动执行与统计成本", "让活动从一次性动作变成持续经营动作"] }
  ]});
  L.addBottomStatement(s, "每一场活动都应该留下会员资产，而不只是现场热度", "teal");
}

/* ======================== Slide 9: 核心闭环 4/4 — 积分 ======================== */
function slide09Points() {
  var s = pptx.addSlide();
  L.addBg(s, C.white);
  L.addTopBand(s, '核心闭环 4/4  让消费有回报，让积分可经营', "核心场景", 9);
  s.addText("把消费记录转化为会员成长和持续复购", { x: 0.74, y: 1.65, w: 6.0, h: 0.22, fontFace: "Microsoft YaHei", fontSize: 12, color: C.inkSoft, margin: 0 });
  L.addFlowDiagram(s, { x: 0.72, y: 2.0, w: 7.0, h: 4.22, title: "积分经营闭环", tone: C.amber, soft: C.amberSoft, footerTags: ["降低人工", "增强感知", "促进复购"], steps: [
    { icon: "购", title: "顾客消费", desc: "消费行为发生" },
    { icon: "票", title: "上传小票", desc: "自助积分或自动积分" },
    { icon: "分", title: "积分入账", desc: "形成会员成长记录" },
    { icon: "兑", title: "积分兑礼", desc: "礼品、停车、活动资格" },
    { icon: "活", title: "会员活跃", desc: "增强权益感知和参与度" },
    { icon: "返", title: "再次消费", desc: "形成新的到店和复购循环" }
  ]});
  L.addThreeExplainCards(s, { x: 8.0, y: 2.02, w: 4.62, cardH: 1.22, accent: C.amber, cards: [
    { title: "为什么要做", body: ["消费有积分是顾客最易理解的会员机制", "自助积分还能减少服务台人工压力"] },
    { title: "怎么做", body: ["支持小票自助积分和规则审核", "支持兑换礼品、停车优惠和活动资格"] },
    { title: "有什么价值", body: ["提升会员活跃率和复购率", "把消费转化为可持续经营的会员资产"] }
  ]});
  L.addBottomStatement(s, "积分不是赠品，而是会员留存和复购的经营工具", "amber");
}

/* ======================== Slide 10: 实施计划 ======================== */
function slide10Plan() {
  var s = pptx.addSlide();
  L.addBg(s, C.paper);
  L.addTopBand(s, "实施计划", "先试点后复制", 10);
  s.addText('建议采用1个项目试点+2个项目复制的推进方式，3个月完成3个项目上线', { x: 0.74, y: 1.66, w: 8.4, h: 0.22, fontFace: "Microsoft YaHei", fontSize: 12, color: C.inkSoft, margin: 0 });
  var stages = [
    { x: 0.8, title: "第1个月", color: C.blue, fill: C.blueSoft, items: ["规则确认", "蓝图设计", "试点项目上线"] },
    { x: 4.33, title: "第2个月", color: C.teal, fill: C.tealSoft, items: ["试点运行", "问题优化", "复制准备"] },
    { x: 7.86, title: "第3个月", color: C.amber, fill: C.amberSoft, items: ["后续2个项目上线", "三项目统一复盘", "形成二期清单"] }
  ];
  stages.forEach(function (st, i) {
    s.addShape(pptx.ShapeType.roundRect, { x: st.x, y: 2.15, w: 2.95, h: 2.62, rectRadius: 0.08, line: { color: st.color, pt: 1.2 }, fill: { color: st.fill } });
    s.addText(st.title, { x: st.x + 0.2, y: 2.34, w: 2.55, h: 0.32, fontFace: "Microsoft YaHei", fontSize: 18, bold: true, color: st.color, align: "center", margin: 0 });
    L.addBulletList(s, st.items, st.x + 0.24, 2.95, 2.35, { fontSize: 12, gap: 0.5, bullet: st.color, color: C.inkSoft });
    if (i < stages.length - 1) { s.addShape(pptx.ShapeType.chevron, { x: st.x + 3.12, y: 3.18, w: 0.26, h: 0.45, fill: { color: C.coral } }); }
  });
  L.addCard(s, { x: 0.8, y: 4.98, w: 5.85, h: 1.9, title: "首期关键里程碑", body: ["试点项目上线", "试点项目复盘", "后续2个项目上线", "三项目首轮复盘"], accent: C.coral, titleSize: 15, bodySize: 10.5 });
  L.addCard(s, { x: 6.9, y: 4.98, w: 5.7, h: 1.9, title: "实施原则", body: ["先高频场景，后复杂玩法", "先验证核心价值，再扩大范围", "阶段验收、阶段复盘、阶段复制"], accent: C.blue, titleSize: 15, bodySize: 10.5 });
}

/* ======================== Slide 11: 预算 ======================== */
function slide11Budget() {
  var s = pptx.addSlide();
  L.addBg(s, C.white);
  L.addTopBand(s, "预算建议", "首年30万元", 11);
  L.addMetricCard(s, 0.75, 1.88, 3.0, 1.5, { main: C.blue, soft: C.blueSoft, bg: C.paper }, "10万元", "单项目首年投入", "按单项目建设成本口径测算");
  L.addMetricCard(s, 3.98, 1.88, 3.0, 1.5, { main: C.teal, soft: C.tealSoft, bg: C.paper }, "3个", "首年上线项目数", "先试点后复制，3个月完成上线");
  L.addMetricCard(s, 7.21, 1.88, 2.95, 1.5, { main: C.amber, soft: C.amberSoft, bg: C.paper }, "30万元", "首年总预算", "适用于本次立项审批");
  L.addMetricCard(s, 10.38, 1.88, 2.2, 1.5, { main: C.coral, soft: C.coralSoft, bg: C.paper }, "3万元/年", "次年维护费", "3个项目每年统一维护");
  L.addCard(s, { x: 0.75, y: 3.84, w: 5.9, h: 2.0, title: "预算口径说明", body: ["首年按1个项目10万元测算，3个项目共30万元", "次年按1个项目1万元/年维护测算，3个项目共3万元/年", "后续若新增高级玩法或新增项目，再单独申请预算"], accent: C.blue });
  L.addCard(s, { x: 6.9, y: 3.84, w: 5.7, h: 2.0, title: "成本控制建议", body: ["首期只做会员、停车、券、活动、基础复盘核心能力", "先用试点项目验证，再复制到后续项目", "采用阶段验收、阶段付款，确保投入与结果挂钩"], accent: C.teal });
  L.addCard(s, { x: 0.75, y: 5.92, w: 11.85, h: 0.78, title: "管理层可直接理解为", body: "今年先花30万元，把3个项目会员底座和核心闭环搭起来；明年进入稳定运营阶段，维护费控制在3万元/年。", accent: C.amber, titleSize: 13, bodySize: 10.5 });
}

/* ======================== Slide 12: 风险 ======================== */
function slide12Risk() {
  var s = pptx.addSlide();
  L.addBg(s, C.paper);
  L.addTopBand(s, "实施风险与应对", "风险可控", 12);
  var riskCards = [
    { x: 0.76, y: 1.88, w: 3.0, h: 1.82, title: "规则不统一", accent: C.red, body: ["影响：需求反复、开发返工", "应对：先书面确认五类规则"] },
    { x: 3.98, y: 1.88, w: 3.0, h: 1.82, title: "接口不确定", accent: C.blue, body: ["影响：关键场景延期", "应对：立项初期摸底停车、支付接口"] },
    { x: 7.2, y: 1.88, w: 3.0, h: 1.82, title: "范围失控", accent: C.amber, body: ["影响：周期失控、预算超支", "应对：一期只做核心闭环"] },
    { x: 10.42, y: 1.88, w: 2.2, h: 1.82, title: "使用不足", accent: C.teal, body: ["影响：仍沿用旧流程", "应对：先选试点跑通"] }
  ];
  riskCards.forEach(function (rc) { L.addCard(s, rc); });
  L.addCard(s, { x: 0.76, y: 4.08, w: 5.95, h: 1.8, title: "数据质量与安全", body: ["风险：历史会员数据质量不高，存在安全要求", "应对：上线前清洗主数据，建立唯一标识，IT统筹权限和备份"], accent: C.purple });
  L.addCard(s, { x: 6.95, y: 4.08, w: 5.65, h: 1.8, title: "总体判断", body: ["本项目风险主要集中在规则、接口和组织协同，而不是系统本身", "采用先试点、后复制、阶段验收的方式，可将风险控制在可管理范围内"], accent: C.coral });
  L.addBottomStatement(s, "项目风险可控，关键在于先统一规则、先抓接口、先跑试点", "coral");
}

/* ======================== Slide 13: 决策建议 ======================== */
function slide13Decision() {
  var s = pptx.addSlide();
  L.addBg(s, C.deep2);
  s.addText("建议管理层本次拍板事项", { x: 0.86, y: 0.96, w: 6.2, h: 0.48, fontFace: "Microsoft YaHei", fontSize: 25, bold: true, color: C.white, margin: 0 });
  s.addText("本次立项的核心，不是上一个小程序，而是为未来经营补齐会员底座", { x: 0.88, y: 1.64, w: 7.2, h: 0.28, fontFace: "Microsoft YaHei", fontSize: 13, color: "D8E5EC", margin: 0 });
  var items = [
    "同意启动福州正祥会员系统项目",
    "同意按1个项目试点+2个项目复制方式推进",
    "同意一期纳入会员、停车、券、活动、美团抖音API对接核心能力",
    "同意首年预算30万元，次年维护费3万元/年",
    "同意由业务部门与IT部门联合推进，按阶段验收复盘"
  ];
  items.forEach(function (item, i) {
    var y = 2.38 + i * 0.73;
    s.addShape(pptx.ShapeType.roundRect, { x: 0.9, y: y, w: 8.15, h: 0.5, rectRadius: 0.06, line: { color: "36516A", pt: 1 }, fill: { color: "17314A" } });
    s.addShape(pptx.ShapeType.ellipse, { x: 1.08, y: y + 0.12, w: 0.24, h: 0.24, fill: { color: C.amber } });
    s.addText(String(i + 1), { x: 1.12, y: y + 0.155, w: 0.16, h: 0.12, fontFace: "Microsoft YaHei", fontSize: 8.5, bold: true, color: C.deep, align: "center", margin: 0 });
    s.addText(item, { x: 1.5, y: y + 0.12, w: 7.25, h: 0.18, fontFace: "Microsoft YaHei", fontSize: 13, color: C.white, margin: 0 });
  });
  L.addCard(s, { x: 9.35, y: 1.56, w: 3.0, h: 3.0, title: "一句话结论", body: "建议立即立项。先抓停车和平台券两个经营抓手，先用一个试点项目把会员闭环跑通，再在3个月内完成3个项目落地。", fill: "F5F8FA", line: "C9D5DE", accent: C.coral, titleSize: 17, bodySize: 12 });
  L.addSectionLabel(s, 9.74, 4.98, 2.24, "建议立即立项", "amber");
  s.addText("立项汇报  |  13", { x: 11.2, y: 7.0, w: 1.2, h: 0.18, fontFace: "Microsoft YaHei", fontSize: 9, color: "D8E5EC", align: "right", margin: 0 });
}

/* ======================== 编译输出 ======================== */
slide01Cover(); slide02Summary(); slide03Urgency(); slide04Benchmark(); slide05Blueprint();
slide06Parking(); slide07Coupon(); slide08Activity(); slide09Points();
slide10Plan(); slide11Budget(); slide12Risk(); slide13Decision();

var outDir = path.dirname(CONFIG.outputPath);
if (!fs.existsSync(outDir)) { fs.mkdirSync(outDir, { recursive: true }); }

pptx.writeFile({ fileName: CONFIG.outputPath }).then(function () {
  console.log("OK: " + CONFIG.outputPath);
}).catch(function (err) {
  console.error("FAIL:", err);
  process.exit(1);
});
