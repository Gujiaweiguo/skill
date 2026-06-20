"""数据模型定义"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TableData:
    """读取到的表格数据"""
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)


@dataclass
class ImageAsset:
    """从文档中提取的图片资源"""
    path: str              # 提取后的文件路径
    alt_text: str = ""     # 替代文本/描述
    source: str = ""       # 来源（文档中的位置，如"第3页/第2段"）


@dataclass
class RawDocument:
    """统一文档读取结果"""
    file_path: str
    file_type: str  # docx / pptx / xlsx / pdf
    title: str = ""
    text_content: str = ""       # 提取的全文文本
    tables: list[TableData] = field(default_factory=list)
    images: list[ImageAsset] = field(default_factory=list)


@dataclass
class TenderInfo:
    """招标文件结构化摘要"""
    project_name: str = ""
    purchaser: str = ""
    project_no: str = ""
    budget: str = ""
    service_period: str = ""
    deadline: str = ""
    delivery_place: str = ""

    # 资格要求
    qualification_requirements: list[str] = field(default_factory=list)

    # 实质性条款
    substantive_clauses: list[str] = field(default_factory=list)

    # 技术需求
    technical_requirements: list[dict] = field(default_factory=list)

    # 采购内容/范围
    scope: str = ""

    # 评分办法
    scoring_method: str = ""
    scoring_items: list[dict] = field(default_factory=list)

    # 功能清单（从 xlsx 提取）
    function_list: list[dict] = field(default_factory=list)

    # 报价要求
    pricing_requirements: str = ""

    # 格式要求（原始文本，供 AI 解析）
    format_requirements: str = ""

    # 格式覆盖（结构化，由 AI 从 format_requirements 解析）
    # 格式: {"font": {"body": "宋体", "heading": "黑体", ...}, "margins": {...}, "page": {...}}
    format_overrides: dict = field(default_factory=dict)

    # 人员要求（关键角色及资质）
    personnel_requirements: list[dict] = field(default_factory=list)

    # 服务/售后要求（SLA 级别）
    service_level_requirements: list[dict] = field(default_factory=list)

    # 实施周期/里程碑要求
    timeline_requirements: list[dict] = field(default_factory=list)

    # 文件组成
    required_documents: list[str] = field(default_factory=list)

    # 原始文本全文
    raw_text: str = ""

    # 述标PPT重点响应项（客户重点关注的内容）
    key_response_items: list[dict] = field(default_factory=list)