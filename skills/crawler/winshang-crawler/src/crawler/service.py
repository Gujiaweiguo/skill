import asyncio
import csv
import logging
import os
from typing import Any

from dotenv import load_dotenv

from .winshang_client import WinshangClient, WinshangAPIError

logger = logging.getLogger(__name__)

load_dotenv()


def get_credentials() -> tuple[str, str]:
    username = os.getenv("WINSHANG_USERNAME", "")
    password = os.getenv("WINSHANG_PASSWORD", "")
    if not username or not password:
        raise ValueError(
            "请在 .env 文件中设置 WINSHANG_USERNAME 和 WINSHANG_PASSWORD，"
            "或通过环境变量传入。"
        )
    return username, password


_KNOWN_CITIES = [
    "北京", "上海", "广州", "深圳", "天津", "重庆",
    "杭州", "南京", "苏州", "成都", "武汉", "西安",
    "长沙", "青岛", "郑州", "昆明", "厦门", "合肥",
    "福州", "沈阳", "济南", "南宁", "贵阳", "南昌",
    "泉州", "佛山", "东莞", "宁波", "大连", "无锡",
    "常州", "徐州", "绍兴", "嘉兴", "珠海", "中山",
    "惠州", "汕头", "湛江", "肇庆", "江门", "茂名",
    "梅州", "汕尾", "河源", "阳江", "清远", "潮州",
    "揭阳", "云浮", "韶关", "保定", "潜江",
]

_PROVINCE_CITIES: dict[str, list[str]] = {
    "广东": ["广州", "深圳", "佛山", "东莞", "珠海", "中山", "惠州",
             "汕头", "湛江", "肇庆", "江门", "茂名", "梅州", "汕尾",
             "河源", "阳江", "清远", "潮州", "揭阳", "云浮", "韶关"],
    "浙江": ["杭州", "宁波", "温州", "嘉兴", "绍兴", "金华", "台州",
             "湖州", "衢州", "舟山", "丽水"],
    "江苏": ["南京", "苏州", "无锡", "常州", "徐州", "南通", "扬州",
             "镇江", "盐城", "淮安", "连云港", "泰州", "宿迁"],
    "福建": ["福州", "厦门", "泉州", "漳州", "莆田", "龙岩", "三明",
             "南平", "宁德"],
    "山东": ["济南", "青岛", "烟台", "潍坊", "临沂", "淄博", "济宁",
             "泰安", "德州", "聊城", "威海", "东营", "日照", "滨州", "枣庄", "菏泽"],
    "四川": ["成都", "绵阳", "德阳", "宜宾", "南充", "泸州", "达州",
             "乐山", "眉山", "自贡", "遂宁", "内江", "广安"],
}


def _extract_city(name: str) -> str:
    for city in _KNOWN_CITIES:
        if name.startswith(city):
            return city
    return ""


def _province_cities(province: str) -> list[str]:
    return _PROVINCE_CITIES.get(province, [])


PROJECT_FIELDS = [
    "projectId",
    "项目名称",
    "项目状态",
    "所在城市",
    "项目类型",
    "商业面积",
    "开业时间",
    "招商需求",
    "更新时间",
    "项目概况",
    "页面地址",
]


def save_projects_to_csv(
    projects: list[dict[str, Any]],
    filepath: str = "./data/winshang_data.csv",
) -> str:
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    rows = []
    for p in projects:
        name = p.get("projectName", "")
        row = {
            "projectId": p.get("projectId", ""),
            "项目名称": name,
            "项目状态": _status_name(p.get("xmZhuangTai", "")),
            "所在城市": _extract_city(name),
            "项目类型": p.get("wuYeLx", ""),
            "商业面积": p.get("shangYeMianjiRange", ""),
            "开业时间": p.get("kaiYeShiJianRange", ""),
            "招商需求": p.get("zhaoShangXQ", ""),
            "更新时间": p.get("updateTime", ""),
            "项目概况": p.get("projectJieShao", ""),
            "页面地址": f"http://www.winshangdata.com/projectDetail?id={p.get('projectId', '')}",
        }
        rows.append(row)
    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=PROJECT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("已保存 %s 条数据到 %s", len(rows), filepath)
    return filepath


def _status_name(code: Any) -> str:
    mapping = {2072: "未开业", 2071: "已开业"}
    try:
        return mapping.get(int(code), str(code))
    except (ValueError, TypeError):
        return str(code) if code else ""


async def _extract_token_via_playwright(username: str, password: str) -> str:
    from playwright.async_api import async_playwright

    logger.info("使用 Playwright 登录以获取 JWT token...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        try:
            await page.goto(
                "http://www.winshangdata.com/userCenter/login",
                wait_until="domcontentloaded",
            )
            await page.wait_for_timeout(2000)
            await page.get_by_role("textbox", name="手机号/邮箱/用户名/昵称").fill(username)
            await page.get_by_role("textbox", name="请填写登录密码").fill(password)
            await page.locator("label span").nth(1).click()
            await page.get_by_role("button", name="登录").click()
            await page.wait_for_timeout(8000)
            token: str = await page.evaluate(
                "window.__NUXT__.state.userInfo.token || ''"
            )
            if token:
                logger.info("成功获取 JWT token（前 20 位: %s...）", token[:20])
                return token
            raise RuntimeError("无法从 Playwright 页面提取 JWT token")
        finally:
            await browser.close()


async def crawl_and_save(
    province: str = "",
    status: str = "未开业",
    output: str = "./data/winshang_data.csv",
) -> str:
    username, password = get_credentials()

    async with WinshangClient(username, password, proxy=None) as client:
        await client.login()
        token = await _extract_token_via_playwright(username, password)
        client.set_token(token)

        logger.info("正在获取项目列表（状态=%s）...", status)
        projects = await client.get_all_projects(
            province=province,
            status=status,
        )
        logger.info("获取到 %s 个项目", len(projects))

        if not projects:
            logger.warning("未获取到任何项目数据")
            return ""

        filepath = save_projects_to_csv(projects, output)
        logger.info("爬取完成，数据已保存到 %s", filepath)
        return filepath


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    asyncio.run(crawl_and_save(province="上海", status="未开业"))
