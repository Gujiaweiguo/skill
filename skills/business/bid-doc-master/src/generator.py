"""
内容包生成器 — 结构化招标信息 → .word-content.md

根据 bid-doc-master SKILL.md 的技术标推荐章节，结合招标文件提取的结构化信息，
生成可直接交给 word-master 渲染的内容包。
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import TenderInfo


def generate_technical_bid(
    tender: TenderInfo,
    output_path: str,
    bidder: str = "",
    template: str = "bidding-technical",
) -> str:
    """生成技术标内容包

    Args:
        tender: 招标结构化信息
        output_path: 内容包输出路径
        bidder: 投标人名称
        template: word-master 模板名称

    Returns:
        生成的内容包文件路径
    """
    project_name = tender.project_name or "未知项目"
    purchaser = tender.purchaser or "采购人"

    lines = []
    # === YAML Frontmatter ===
    lines.append("---")
    lines.append(f'title: "{project_name}技术方案"')
    lines.append("type: proposal")
    lines.append(f'template: "{template}"')
    lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"project: {project_name}")
    lines.append(f"purchaser: {purchaser}")
    lines.append(f'bidder: "{bidder}"' if bidder else "")
    lines.append("language: zh-CN")
    lines.append("cover:")
    lines.append(f"  title: {project_name}")
    lines.append("  subtitle: 技术方案")
    lines.append(f"  date: {datetime.now().strftime('%Y年%m月%d日')}")
    # 格式覆盖（由 AI 从招标要求中提取的结构化数据）
    if tender.format_overrides:
        fo = tender.format_overrides
        lines.append("format_overrides:")
        # 字体
        if "font" in fo:
            f = fo["font"]
            lines.append("  font:")
            if "body" in f:
                v = f['body']
                lines.append(f"    body: '{v}'")
            if "heading" in f:
                v = f['heading']
                lines.append(f"    heading: '{v}'")
            if "ascii" in f:
                v = f['ascii']
                lines.append(f"    ascii: '{v}'")
            if "size" in f:
                lines.append(f"    size: {f['size']}")
        # 页边距
        if "margins" in fo:
            m = fo["margins"]
            lines.append("  margins:")
            if "top" in m: lines.append(f"    top: {m['top']}")
            if "bottom" in m: lines.append(f"    bottom: {m['bottom']}")
            if "left" in m: lines.append(f"    left: {m['left']}")
            if "right" in m: lines.append(f"    right: {m['right']}")
        # 页面
        if "page" in fo:
            p = fo["page"]
            lines.append("  page:")
            if "size" in p:
                v = p['size']
                lines.append(f"    size: '{v}'")
            if "orientation" in p:
                v = p['orientation']
                lines.append(f"    orientation: '{v}'")
        # 行距
        if "line_spacing" in fo:
            lines.append(f"  line_spacing: {fo['line_spacing']}")
    lines.append("---")
    lines.append("")

    # === 正文 ===
    lines.append("## 第一章 项目概述")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-1")
    lines.append("page_break: true")
    lines.append("```")
    lines.append("")

    # 1.1 项目背景
    lines.append("### 1.1 项目背景")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-2")
    lines.append("```")
    lines.append("")
    lines.append(f"{purchaser}（以下简称\"采购人\"）为适应数字化转型趋势，提升会员营销与服务能力，")
    lines.append(f"拟建设统一的商业会员营销系统。本项目旨在通过构建一体化会员管理平台，")
    lines.append("实现会员数据的统一管理、精准营销、积分互通、数据分析等核心能力，")
    lines.append("提升顾客体验与运营效率。")
    lines.append("")

    if tender.scope:
        lines.append(tender.scope)
        lines.append("")

    # 1.2 建设目标
    lines.append("### 1.2 建设目标")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-2")
    lines.append("```")
    lines.append("")
    lines.append("本项目的主要建设目标包括：")
    lines.append("")
    lines.append("- 建立统一的会员管理体系，实现全生命周期会员管理")
    lines.append("- 构建多维度精准营销引擎，提升营销转化率")
    lines.append("- 实现积分通存通兑，提升会员忠诚度")
    lines.append("- 建设数据分析平台，辅助运营决策")
    lines.append("- 打通线上线下全渠道，优化用户体验")
    lines.append("")

    # 1.3 采购范围
    lines.append("### 1.3 采购范围")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-2")
    lines.append("```")
    lines.append("")

    if tender.function_list:
        lines.append("本项目采购范围涵盖以下功能模块：")
        lines.append("")
        for item in tender.function_list:
            name = item.get("module", item.get("功能模块", ""))
            desc = item.get("description", item.get("功能描述", ""))
            if name:
                lines.append(f"- **{name}**：{desc}")
        lines.append("")
    else:
        lines.append("本项目采购范围涵盖商业会员营销系统的规划、设计、开发、实施及运维服务。")
        lines.append("")

    lines.append("## 第二章 技术方案")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-1")
    lines.append("page_break: true")
    lines.append("```")
    lines.append("")

    # 2.1 系统架构
    lines.append("### 2.1 系统架构")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-2")
    lines.append("```")
    lines.append("")
    lines.append("系统采用微服务架构设计，前后端分离，确保系统的高可用性、可扩展性和安全性。")
    lines.append("前端采用微信小程序作为主要用户入口，后端基于主流的微服务技术栈构建。")
    lines.append("")
    lines.append("> 架构设计遵循高可用、可扩展、安全合规原则，支持弹性伸缩与灰度发布。")
    lines.append("")

    # 2.2 功能模块清单
    lines.append("### 2.2 功能模块清单")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-2")
    lines.append("table: function-matrix")
    lines.append("table_data:")
    lines.append('  header: ["功能模块", "子功能", "功能描述", "优先级"]')
    lines.append("  column_widths: [15, 15, 45, 10]")
    if tender.function_list:
        lines.append("  rows:")
        for item in tender.function_list:
            module = item.get("module", item.get("功能模块", ""))
            func = item.get("function", item.get("子功能", ""))
            desc = item.get("description", item.get("功能描述", ""))
            pri = item.get("priority", item.get("优先级", ""))
            lines.append(f'    - ["{module}", "{func}", "{desc}", "{pri}"]')
    else:
        lines.append("  rows: []")
    lines.append("```")
    lines.append("")

    # 2.3 技术架构
    lines.append("### 2.3 技术架构")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-2")
    lines.append("```")
    lines.append("")
    lines.append("#### 前端技术栈")
    lines.append("")
    lines.append("- 微信小程序原生开发 + Uni-app 跨端框架")
    lines.append("- Vue 3 + Element Plus 管理后台")
    lines.append("- Tailwind CSS 样式框架")
    lines.append("")
    lines.append("#### 后端技术栈")
    lines.append("")
    lines.append("- Spring Cloud 微服务架构（服务注册/配置中心/网关）")
    lines.append("- Spring Boot 业务服务")
    lines.append("- MyBatis-Plus + MySQL 数据持久层")
    lines.append("- Redis 缓存 + RabbitMQ 消息队列")
    lines.append("- Docker + K8s 容器化部署")
    lines.append("")
    lines.append("#### 安全架构")
    lines.append("")
    lines.append("- HTTPS 加密传输")
    lines.append("- JWT Token 认证 + OAuth2.0 授权")
    lines.append("- 数据加密存储（AES-256）")
    lines.append("- 操作日志审计")
    lines.append("")

    # 第三章 项目实施计划
    lines.append("## 第三章 项目实施计划")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-1")
    lines.append("page_break: true")
    lines.append("table: implementation-plan")
    lines.append("table_data:")
    lines.append('  header: ["阶段", "时间", "工作内容", "交付物"]')
    lines.append("  column_widths: [12, 10, 40, 28]")
    lines.append("  rows:")
    if tender.timeline_requirements:
        for ml in tender.timeline_requirements:
            phase = ml.get("phase", ml.get("阶段", ""))
            time = ml.get("time", ml.get("时间", ""))
            content = ml.get("content", ml.get("内容", ""))
            deliverable = ml.get("deliverable", ml.get("交付物", ""))
            lines.append(f'    - ["{phase}", "{time}", "{content}", "{deliverable}"]')
    else:
        lines.append('    - ["需求调研", "第1-2周", "现场调研、需求确认、功能梳理", "需求规格说明书"]')
        lines.append('    - ["系统设计", "第3-4周", "架构设计、UI/UX设计、数据库设计", "设计文档"]')
        lines.append('    - ["开发实施", "第5-10周", "迭代开发、单元测试、集成测试", "可运行系统"]')
        lines.append('    - ["系统测试", "第11-12周", "功能测试、性能测试、安全测试", "测试报告"]')
        lines.append('    - ["上线部署", "第13周", "生产环境部署、数据迁移", "上线确认单"]')
    lines.append("```")
    lines.append("")

    # 第四章 项目组织
    lines.append("## 第四章 项目组织与人员配置")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-1")
    lines.append("page_break: true")
    lines.append("table: personnel-matrix")
    lines.append("table_data:")
    lines.append('  header: ["角色", "姓名", "职责", "资质"]')
    lines.append("  column_widths: [15, 12, 40, 28]")
    lines.append("  rows:")
    if tender.personnel_requirements:
        for p in tender.personnel_requirements:
            role = p.get("role", p.get("角色", ""))
            name = p.get("name", p.get("姓名", "待确认"))
            duty = p.get("duty", p.get("职责", ""))
            qual = p.get("qualification", p.get("资质", ""))
            lines.append(f'    - ["{role}", "{name}", "{duty}", "{qual}"]')
    else:
        lines.append('    - ["项目经理", "待确认", "项目整体管理、进度控制、客户沟通", "PMP"]')
        lines.append('    - ["技术负责人", "待确认", "技术架构设计、关键技术决策", "高级工程师"]')
        lines.append('    - ["前端开发", "待确认", "小程序/H5/管理后台开发", "3年+经验"]')
        lines.append('    - ["后端开发", "待确认", "微服务开发、接口设计", "3年+经验"]')
        lines.append('    - ["UI设计师", "待确认", "界面设计、交互设计", "2年+经验"]')
        lines.append('    - ["测试工程师", "待确认", "功能测试、自动化测试", "ISTQB"]')
        lines.append('    - ["运维工程师", "待确认", "部署、监控、运维保障", "2年+经验"]')
    lines.append("```")
    lines.append("")

    # 第五章 质量保障
    lines.append("## 第五章 质量保障与服务体系")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-1")
    lines.append("page_break: false")
    lines.append("```")
    lines.append("")
    lines.append("### 5.1 质量保障体系")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-2")
    lines.append("```")
    lines.append("")
    lines.append("- **需求管理**：需求确认 → 需求评审 → 需求跟踪矩阵")
    lines.append("- **设计评审**：概要设计评审 → 详细设计评审 → 技术方案评审")
    lines.append("- **代码审查**：代码规范检查 → 静态代码扫描 → Peer Review")
    lines.append("- **测试验证**：单元测试 → 集成测试 → 系统测试 → UAT")
    lines.append("- **变更管理**：变更申请 → 影响分析 → 变更评审 → 变更实施")
    lines.append("")
    lines.append("### 5.2 运维服务体系")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-2")
    lines.append("```")
    lines.append("")
    if tender.service_level_requirements:
        lines.append(f"针对本项目招标要求的服务水平，{bidder or '我司'}承诺如下：")
        lines.append("")
        lines.append("| 服务级别 | 响应时间 | 解决时间 | 适用场景 |")
        lines.append("|---------|---------|---------|---------|")
        for s in tender.service_level_requirements:
            tier = s.get("tier", s.get("级别", ""))
            resp = s.get("response", s.get("响应时间", ""))
            reso = s.get("resolution", s.get("解决时间", ""))
            scene = s.get("scene", s.get("适用场景", ""))
            lines.append(f"| {tier} | {resp} | {reso} | {scene} |")
    else:
        lines.append("| 服务级别 | 响应时间 | 解决时间 | 适用场景 |")
        lines.append("|---------|---------|---------|---------|")
        lines.append("| 一级 | 30分钟 | 4小时 | 系统宕机、核心功能不可用 |")
        lines.append("| 二级 | 2小时 | 8小时 | 非核心功能故障 |")
        lines.append("| 三级 | 4小时 | 24小时 | 咨询、建议、一般性问题 |")
    lines.append("")
    lines.append("> 提供7×24小时技术支持服务，确保系统稳定运行。")
    lines.append("")

    # 第六章 资质业绩
    lines.append("## 第六章 公司资质与项目业绩")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-1")
    lines.append("page_break: false")
    lines.append("```")
    lines.append("")
    lines.append("### 6.1 公司资质")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-2")
    lines.append("```")
    lines.append("")
    if tender.qualification_requirements:
        lines.append(f"针对本项目招标要求的资质条件，{bidder or '我司'}全部满足：")
        lines.append("")
        for req in tender.qualification_requirements:
            lines.append(f"- ✅ {req}")
    else:
        lines.append(f"{bidder or '我司'}拥有以下核心资质：")
        lines.append("")
        lines.append("- 国家高新技术企业")
        lines.append("- 双软认证企业")
        lines.append("- ISO9001质量管理体系认证")
        lines.append("- ISO27001信息安全管理体系认证")
        lines.append("- ISO14001环境管理体系认证")
        lines.append("- 30+项软件著作权")
    lines.append("")
    lines.append("### 6.2 类似项目业绩")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-2")
    lines.append("```")
    lines.append("")
    lines.append("| 序号 | 项目名称 | 服务内容 | 服务期限 | 客户 |")
    lines.append("|------|---------|---------|---------|------|")
    lines.append("| 1 | 广州流花中心会员系统 | 会员管理、积分营销 | 2025.03-2026.03 | 广州城投 |")
    lines.append("| 2 | 和健生活广场会员营销系统 | 会员营销、数据分析 | 2024.05-2025.05 | 润科商业 |")
    lines.append("")

    # 写成文件
    content = "\n".join(lines)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return str(path)


def generate_slide_content(
    tender: TenderInfo,
    output_path: str,
    bidder: str = "蓝联科技",
    style: str = "商务汇报",
) -> str:
    """生成述标 PPT 内容包 (.slide-content.md)

    述标 PPT 结构（按演讲逻辑编排）:
      1. 封面
      2. 目录
      3-4. 公司介绍 + 资质
      5. 需求理解
      6-7. 需求响应（大项分类）
      8-10. 方案蓝图
      11-14. 重点响应讲解（左2/3示意图，右1/3说明）
      15. 实施计划（符合招标要求）
      16. 实施团队（体现客户要求）
      17. 售后服务体系（对标招标SLA）
      18. 为什么选择蓝联
      19. 结尾
    """
    project_name = tender.project_name or "未知项目"
    purchaser = tender.purchaser or "采购人"

    lines = []
    # ── Frontmatter ──
    lines.append("---")
    lines.append(f'title: "{project_name}述标答辩"')
    lines.append(f"type: proposal")
    lines.append(f"style: {style}")
    lines.append("target_pages: 18-22")
    lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"project: {project_name}")
    lines.append(f"client: {purchaser}")
    lines.append(f'author: "{bidder}"')
    lines.append("colors:")
    lines.append("  primary: '003366'")
    lines.append("  secondary: '004080'")
    lines.append("  accent: 'e8772e'")
    lines.append("  light: 'f0f4f8'")
    lines.append("  bg: 'ffffff'")
    lines.append("brand:")
    lines.append(f"  slogan: '让商业更智能'")
    lines.append("sources:")
    lines.append("  - path: '$MATERIALS_DIR/01-company-overview/公司简介.md'")
    lines.append("    type: 公司概况")
    lines.append("    pages: [3, 4]")
    lines.append("  - path: '$MATERIALS_DIR/04-cases/商业会员营销案例.md'")
    lines.append("    type: 客户案例")
    lines.append("    pages: [18]")
    lines.append("---")
    lines.append("")

    # ── 第1页：封面 ──
    lines.append("## 第1页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: cover")
    lines.append(f'title: "{project_name}"')
    lines.append("subtitle: 述标答辩")
    lines.append(f"date: \"{datetime.now().strftime('%Y年%m月')}\"")
    lines.append("```")
    lines.append("")

    # ── 第2页：目录 ──
    lines.append("## 第2页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: toc")
    lines.append("title: 目录")
    lines.append("items:")
    lines.append("  - '01  公司简介与资质'")
    lines.append("  - '02  需求理解'")
    lines.append("  - '03  方案蓝图'")
    lines.append("  - '04  重点响应'")
    lines.append("  - '05  实施与服务'")
    lines.append("  - '06  为什么选择我们'")
    lines.append("```")
    lines.append("")

    # ── 第3-4页：公司介绍 + 资质 ──
    lines.append("## 第3页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: section")
    lines.append("title: 01 公司简介与资质")
    lines.append("```")
    lines.append("")

    lines.append("## 第4页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: content")
    lines.append("layout: left-right")
    lines.append("title: 公司概况")
    lines.append("```")
    lines.append("")
    lines.append("左：")
    lines.append("")
    lines.append(f"{bidder}成立于2006年，是国内领先的商业地产数字化服务商。")
    lines.append("公司总部位于广州，在全国设有6个分支机构。")
    lines.append("")
    lines.append("**核心能力**")
    lines.append("- 商业会员营销系统")
    lines.append("- 商业地产数字化咨询")
    lines.append("- 智慧商圈整体解决方案")
    lines.append("- 数据中台与商业智能")
    lines.append("")
    lines.append("右：")
    lines.append("")
    lines.append("**关键数据**")
    lines.append("- 成立时间：2006年")
    lines.append("- 团队规模：200+人")
    lines.append("- 服务客户：300+商业项目")
    lines.append("- 覆盖城市：50+城市")
    lines.append("")

    # 资质页
    has_qualifications = bool(tender.qualification_requirements)
    lines.append(f"## 第5页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: content")
    lines.append("layout: bullet-list")
    if has_qualifications:
        lines.append("title: 资质响应（对标招标要求）")
    else:
        lines.append("title: 核心资质")
    lines.append("```")
    lines.append("")
    if has_qualifications:
        lines.append(f"针对本项目招标要求的资质条件，{bidder}全部满足：")
        lines.append("")
        for req in tender.qualification_requirements:
            lines.append(f"- ✅ {req}")
    else:
        lines.append(f"{bidder}拥有以下核心资质：")
        lines.append("")
        lines.append("- 🔷 国家高新技术企业")
        lines.append("- 🔷 双软认证企业")
        lines.append("- 🔷 ISO9001质量管理体系认证")
        lines.append("- 🔷 ISO27001信息安全管理体系认证")
        lines.append("- 🔷 30+项软件著作权")
    lines.append("")

    # ── 需求理解 ──
    lines.append("## 第6页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: section")
    lines.append("title: 02 需求理解")
    lines.append("```")
    lines.append("")

    lines.append("## 第7页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: content")
    lines.append("layout: bullet-list")
    lines.append("title: 核心需求理解")
    lines.append("```")
    lines.append("")
    lines.append(f"经过对招标文件的深入分析，我们认为{purchaser}的核心需求集中在以下方面：")
    lines.append("")
    lines.append("- **会员统一管理**：打通线上线下会员数据，实现统一视图")
    lines.append("- **精准营销能力**：基于会员画像的多维度精准营销引擎")
    lines.append("- **积分通存通兑**：跨商户/跨业态积分互通")
    lines.append("- **数据运营分析**：可视化数据分析与辅助决策")
    lines.append("- **全渠道覆盖**：微信小程序+H5+线下终端一体化")
    lines.append("")

    # ── 需求响应（大项分类） ──
    lines.append("## 第8页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: content")
    lines.append("layout: feature-grid")
    lines.append("title: 需求响应总览（大项响应）")
    lines.append("items:")
    lines.append("  - title: 会员管理")
    lines.append("    desc: 统一会员中心，支持多等级、多渠道")
    lines.append("    icon: '👤'")
    lines.append("  - title: 营销引擎")
    lines.append("    desc: 智能营销，自动触发+手动配置")
    lines.append("    icon: '🎯'")
    lines.append("  - title: 积分体系")
    lines.append("    desc: 通存通兑，多商户结算")
    lines.append("    icon: '💎'")
    lines.append("  - title: 数据分析")
    lines.append("    desc: 可视化大屏+多维报表")
    lines.append("    icon: '📊'")
    lines.append("  - title: 全场覆盖")
    lines.append("    desc: 小程序+H5+自助终端")
    lines.append("    icon: '📱'")
    lines.append("  - title: 开放接口")
    lines.append("    desc: 标准API，支持对接第三方")
    lines.append("    icon: '🔗'")
    lines.append("```")
    lines.append("")

    # ── 方案蓝图 ──
    lines.append("## 第9页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: section")
    lines.append("title: 03 方案蓝图")
    lines.append("```")
    lines.append("")

    lines.append("## 第10页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: content")
    lines.append("layout: left-right")
    lines.append("title: 整体架构蓝图")
    lines.append("```")
    lines.append("")
    lines.append("左：")
    lines.append("")
    lines.append("> [系统架构示意图]")
    lines.append("> 微服务架构 + 前后端分离")
    lines.append("> 由 word-master 渲染时插入实际架构图")
    lines.append("")
    lines.append("右：")
    lines.append("")
    lines.append("**架构分层**")
    lines.append("1. **接入层**：小程序/H5/API网关")
    lines.append("2. **业务层**：会员/营销/积分/数据")
    lines.append("3. **数据层**：MySQL/Redis/数据仓库")
    lines.append("4. **基础设施**：Docker/K8s/监控")
    lines.append("")

    lines.append("## 第11页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: content")
    lines.append("layout: feature-grid")
    lines.append("title: 核心功能模块")
    lines.append("items:")
    lines.append("  - title: 会员中心")
    lines.append("    desc: 会员档案、等级、积分、储值")
    lines.append("  - title: 营销中心")
    lines.append("    desc: 优惠券、秒杀、拼团、满减")
    lines.append("  - title: 积分商城")
    lines.append("    desc: 积分兑换、积分+现金")
    lines.append("  - title: 数据看板")
    lines.append("    desc: 经营分析、会员画像")
    lines.append("  - title: 消息推送")
    lines.append("    desc: 模板消息、短信、公众号")
    lines.append("  - title: 商户管理")
    lines.append("    desc: 商户入驻、结算对账")
    lines.append("```")
    lines.append("")

    # ── 重点响应 ──
    lines.append("## 第12页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: section")
    lines.append("title: 04 重点响应")
    lines.append("```")
    lines.append("")

    # 生成重点响应页（左2/3示意图，右1/3说明）
    response_items = tender.key_response_items or [
        {"title": "会员统一管理", "desc": "建立统一的会员身份中心，支持多渠道会员注册、统一积分、统一等级"},
        {"title": "精准营销引擎", "desc": "基于RFM模型+标签体系的智能营销引擎，支持自动触发与A/B测试"},
        {"title": "积分通存通兑", "desc": "支持跨商户积分互通，自动结算清分，提升会员粘性"},
    ]
    for idx, item in enumerate(response_items):
        page_num = 13 + idx
        lines.append(f"## 第{page_num}页")
        lines.append("")
        lines.append("```yaml")
        lines.append("type: content")
        lines.append("layout: left-right")
        lines.append(f"title: 重点响应：{item.get('title', '')}")
        lines.append("ratio: 2-1")
        lines.append("```")
        lines.append("")
        lines.append("左（示意图）：")
        lines.append("")
        lines.append(f"> [{item.get('title', '')} 架构/流程示意图]")
        lines.append("> 由 ppt-master 渲染时生成或引用实际截图")
        lines.append("")
        lines.append("右（说明）：")
        lines.append("")
        desc = item.get("desc", "")
        lines.append(desc)
        lines.append("")
        # 加"为什么满足"的说明
        lines.append(f"{bidder}方案优势：")
        lines.append("- 成熟产品，已落地30+商业项目")
        lines.append("- 支持深度定制，匹配业务场景")
        lines.append("- 高可用架构，保障系统稳定")
        lines.append("")

    # ── 实施计划 ──
    impl_page = 13 + len(response_items)
    lines.append(f"## 第{impl_page}页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: section")
    lines.append("title: 05 实施与服务")
    lines.append("```")
    lines.append("")

    impl_page += 1
    lines.append(f"## 第{impl_page}页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: content")
    lines.append("layout: timeline")
    lines.append("title: 实施计划（响应招标要求）")
    lines.append("items:")
    if tender.timeline_requirements:
        for i, ml in enumerate(tender.timeline_requirements):
            phase = ml.get("phase", ml.get("阶段", f"阶段{i+1}"))
            time = ml.get("time", ml.get("时间", ""))
            content = ml.get("content", ml.get("内容", ""))
            deliverable = ml.get("deliverable", ml.get("交付物", ""))
            lines.append(f"  - title: '{phase}'")
            lines.append(f"    time: '{time}'")
            lines.append(f"    desc: '{content} / {deliverable}'")
    else:
        lines.append("  - title: '需求调研'")
        lines.append("    time: '第1-2周'")
        lines.append("    desc: '现场调研、需求确认、方案设计'")
        lines.append("  - title: '系统开发'")
        lines.append("    time: '第3-8周'")
        lines.append("    desc: '迭代开发、单元测试、集成测试'")
        lines.append("  - title: '系统测试'")
        lines.append("    time: '第9-10周'")
        lines.append("    desc: '功能测试、性能测试、UAT'")
        lines.append("  - title: '上线部署'")
        lines.append("    time: '第11周'")
        lines.append("    desc: '生产部署、数据迁移、试运行'")
        lines.append("  - title: '验收交付'")
        lines.append("    time: '第12周'")
        lines.append("    desc: '正式验收、文档交付、培训'")
    lines.append("```")
    lines.append("")

    # ── 实施团队 ──
    impl_page += 1
    lines.append(f"## 第{impl_page}页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: content")
    lines.append("layout: data-table")
    lines.append("title: 实施团队（对标招标要求）")
    lines.append("table:")
    lines.append("  header:")
    lines.append("    - '角色'")
    lines.append("    - '资质/经验'")
    lines.append("    - '本项目中职责'")
    lines.append("  column_widths: [25, 35, 40]")
    lines.append("  rows:")
    if tender.personnel_requirements:
        for p in tender.personnel_requirements:
            role = p.get("role", p.get("角色", ""))
            qual = p.get("qualification", p.get("资质", ""))
            duty = p.get("duty", p.get("职责", ""))
            lines.append(f"    - ['{role}', '{qual}', '{duty}']")
    else:
        lines.append("    - ['项目经理', 'PMP认证 / 10年+经验', '项目整体管理，客户沟通']")
        lines.append("    - ['技术负责人', '高级架构师 / 8年+经验', '架构设计，技术决策']")
        lines.append("    - ['前端开发', '3年+小程序/Uniapp经验', '前端开发']")
        lines.append("    - ['后端开发', '3年+Spring Cloud经验', '后端微服务开发']")
        lines.append("    - ['测试工程师', 'ISTQB / 3年+经验', '全流程测试保障']")
        lines.append("    - ['运维工程师', '2年+Docker/K8s经验', '部署运维']")
    lines.append("```")
    lines.append("")

    # ── 售后服务体系 ──
    impl_page += 1
    lines.append(f"## 第{impl_page}页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: content")
    lines.append("layout: data-table")
    lines.append("title: 售后服务体系（对标招标SLA要求）")
    lines.append("table:")
    lines.append("  header:")
    lines.append("    - '服务级别'")
    lines.append("    - '响应时间'")
    lines.append("    - '解决时间'")
    lines.append("    - '适用场景'")
    lines.append("  column_widths: [15, 20, 20, 45]")
    lines.append("  rows:")
    if tender.service_level_requirements:
        for s in tender.service_level_requirements:
            tier = s.get("tier", s.get("级别", ""))
            resp = s.get("response", s.get("响应时间", ""))
            reso = s.get("resolution", s.get("解决时间", ""))
            scene = s.get("scene", s.get("适用场景", ""))
            lines.append(f"    - ['{tier}', '{resp}', '{reso}', '{scene}']")
    else:
        lines.append("    - ['一级', '30分钟', '4小时', '系统宕机、核心功能不可用']")
        lines.append("    - ['二级', '2小时', '8小时', '非核心功能故障']")
        lines.append("    - ['三级', '4小时', '24小时', '咨询、建议、一般性问题']")
    lines.append("```")
    lines.append("")
    lines.append("此外，我们提供7×24小时技术支持，定期巡检与主动运维。")
    lines.append("")

    # ── 为什么选择蓝联 ──
    impl_page += 1
    lines.append(f"## 第{impl_page}页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: summary")
    lines.append("title: 06 为什么选择我们")
    lines.append("```")
    lines.append("")
    lines.append(f"**{bidder}，您值得信赖的数字化伙伴**")
    lines.append("")
    lines.append(f"✅ **18年行业深耕** — 专注商业地产数字化，行业经验丰富")
    lines.append(f"✅ **300+项目验证** — 全国落地项目超过300个，覆盖50+城市")
    lines.append(f"✅ **全栈自研能力** — 从底层到应用层，全自研可控")
    lines.append(f"✅ **快速响应** — 7×24小时技术保障，本地化服务团队")
    lines.append(f"✅ **持续交付** — 承诺按时保质交付，售后无忧")
    lines.append("")

    # ── 结尾 ──
    impl_page += 1
    lines.append(f"## 第{impl_page}页")
    lines.append("")
    lines.append("```yaml")
    lines.append("type: end")
    lines.append("title: 感谢聆听")
    lines.append("contact:")
    lines.append("  company: 蓝联科技")
    lines.append("  phone: '400-xxx-xxxx'")
    lines.append("  email: 'contact@lanlnk.com'")
    lines.append("  website: 'www.lanlnk.com'")
    lines.append("```")
    lines.append("")

    # ── 写文件 ──
    content = "\n".join(lines)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return str(path)


def generate_commercial_bid(
    tender: TenderInfo,
    output_path: str,
    bidder: str = "",
    template: str = "bidding-commercial",
) -> str:
    """生成商务标内容包（简化版，后续可扩展）"""
    project_name = tender.project_name or "未知项目"
    purchaser = tender.purchaser or "采购人"

    lines = []
    lines.append("---")
    lines.append(f'title: "{project_name}商务文件"')
    lines.append("type: commercial")
    lines.append(f'template: "{template}"')
    lines.append(f"date: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"project: {project_name}")
    lines.append(f"purchaser: {purchaser}")
    lines.append(f'bidder: "{bidder}"' if bidder else "")
    lines.append("language: zh-CN")
    lines.append("cover:")
    lines.append(f"  title: {project_name}")
    lines.append("  subtitle: 商务文件")
    lines.append(f"  date: {datetime.now().strftime('%Y年%m月%d日')}")
    lines.append("---")
    lines.append("")

    lines.append("## 第一章 投标函")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-1")
    lines.append("page_break: true")
    lines.append("```")
    lines.append("")
    lines.append("> **说明**：投标函内容需根据招标文件具体要求填写，此处为框架模板。")
    lines.append("")

    lines.append("## 第二章 法定代表人授权委托书")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-1")
    lines.append("page_break: true")
    lines.append("```")
    lines.append("")

    lines.append("## 第三章 投标人资格证明")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-1")
    lines.append("page_break: true")
    lines.append("```")
    lines.append("")

    lines.append("## 第四章 类似项目业绩")
    lines.append("")
    lines.append("```yaml")
    lines.append("style: heading-1")
    lines.append("page_break: false")
    lines.append("```")
    lines.append("")

    content = "\n".join(lines)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return str(path)