# 公司介绍 Word 模板

## 使用方法

1. 复制 `company-intro.word-content.md` 到项目 content-packages 目录
2. 修改 frontmatter 中的 client、date 字段
3. 修改第三章"近三年服务业绩"表格数据（按最新业绩更新）
4. 修改第四章"重点案例介绍"（选择3-4个标杆案例）
5. 修改第五章"合同信息"表格（更新联系人信息）
6. 运行 word-master 生成 .docx

```bash
cd /opt/code/skill/skills/word/word-master
uv run python -m src.main <内容包路径> --output <输出路径.docx>
```

## 文档结构（6章）

| 章 | 内容 | 数据来源 |
|----|------|---------|
| 第一章 | 公司介绍（定位+技术实力+认证+客户） | `$MATERIALS_DIR/01-company-overview/公司简介.md` |
| 第二章 | 公司资质（营业执照+资质证书+软著表） | `$MATERIALS_DIR/02-qualifications/` |
| 第三章 | 近三年服务业绩（8-10个案例表格） | `$MATERIALS_DIR/01-company-overview/近三年服务业绩.md` |
| 第四章 | 重点案例介绍（3-4个详细案例） | `$MATERIALS_DIR/04-cases/` |
| 第五章 | 合同信息（业绩表+联系方式） | 近三年服务业绩表 Excel |
| 第六章 | 联系方式 | 固定 |

## 客户要求覆盖

| 客户要求 | 对应章节 |
|---------|---------|
| 公司介绍 | 第一章 |
| 公司相关资质 | 第二章 |
| 案例清单 | 第三章 |
| 案例合同 | 第五章 |
