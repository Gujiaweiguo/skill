# -*- coding: utf-8 -*-
"""
赢商大数据 HTTP API 客户端
通过逆向分析网站 JSON API，替代 Playwright 浏览器渲染做数据获取。
"""

import asyncio
import hashlib
import base64
import logging
import random
from typing import Any

import httpx

logger = logging.getLogger(__name__)


# 项目状态代码（从页面观察得到）
PROJECT_STATUS: dict[str, str] = {
    "未开业": "2072",
    "已开业": "2071",
    "全部": "",
}


class WinshangAuthError(Exception):
    """认证失败异常"""


class WinshangAPIError(Exception):
    """API 调用异常"""


class WinshangClient:
    """
    赢商大数据 HTTP API 客户端

    用法:
        async with WinshangClient(username="xxx", password="xxx") as client:
            await client.login()
            projects = await client.get_project_list(province="上海")
    """

    BASE_URL = "http://www.winshangdata.com"

    def __init__(
        self,
        username: str,
        password: str,
        token: str | None = None,
        proxy: str | None = None,
    ):
        self._username = username
        self._password = password
        self._token = token  # JWT token，可从浏览器登录后获取
        self._cookies: dict[str, str] = {}
        self._uid: str = ""
        client_kwargs: dict[str, Any] = {
            "base_url": self.BASE_URL,
            "timeout": httpx.Timeout(30.0, connect=15.0),
            "follow_redirects": True,
        }
        if proxy is not None:
            client_kwargs["proxy"] = proxy
        self._client = httpx.AsyncClient(**client_kwargs)

    async def __aenter__(self) -> "WinshangClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.aclose()

    @staticmethod
    def _md5(s: str) -> str:
        return hashlib.md5(s.encode()).hexdigest()

    @staticmethod
    def _b64(s: str) -> str:
        return base64.b64encode(s.encode()).decode()

    def _build_auth_headers(self) -> dict[str, str]:
        """构建 API 请求所需的认证 header"""
        headers: dict[str, str] = {
            "Content-Type": "application/json;charset=UTF-8",
            "apptype": "bigdata",
            "platform": "pc",
            "uuid": "123456",
        }
        if self._uid:
            headers["uid"] = self._uid
        if self._token:
            headers["authorization"] = self._token
            headers["token"] = self._token
        # pwd header = MD5 前 16 位
        if self._password:
            headers["pwd"] = self._md5(self._password)[:16]
        return headers

    # ── 认证 ──────────────────────────────────────────────

    async def login(self) -> str | None:
        """
        通过 httpx 直接调用登录 API。
        成功返回 JWT token（如果能在响应中提取到），否则返回 None。
        注意：服务器通过 Set-Cookie 设 auth, winfanguser, eyeuser。
        """
        uid_b64 = self._b64(self._username)
        pwd_md5 = self._md5(self._password)

        body = {"pwd": pwd_md5, "uid": uid_b64, "uuid": uid_b64}
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "uuid": "123456",
            "apptype": "bigdata",
            "platform": "pc",
        }

        try:
            resp = await self._client.post(
                "/wsapi/auth/getToken",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise WinshangAuthError(
                f"登录 API 返回 {e.response.status_code}: {e.response.text}"
            ) from e
        except httpx.RequestError as e:
            raise WinshangAuthError(f"登录请求失败: {e}") from e

        # 保存 cookies
        self._cookies = dict(resp.cookies)

        # 从 winfanguser cookie 提取 uid
        wf = self._cookies.get("winfanguser", "")
        if "uid=" in wf:
            self._uid = wf.split("uid=")[1].split("&")[0]

        logger.info(
            "登录成功, uid=%s, cookies: auth=%s, winfanguser=%s",
            self._uid,
            bool(self._cookies.get("auth")),
            bool(self._cookies.get("winfanguser")),
        )

        # 如果已有 token（从外部传入），直接返回
        if self._token:
            return self._token

        # 尝试用 httpx 方式获取 token：auth cookie 里包含 JWT 构建所需信息
        # 实际上 JWT 由前端 JS 生成，httpx 方式无法直接拿到
        # 此时返回 None，调用方需配合 Playwright 获取 token
        return None

    def set_token(self, token: str) -> None:
        """设置 JWT token（从 Playwright 提取后调用）"""
        self._token = token

    # ── 核心 API ──────────────────────────────────────────

    async def get_project_list(
        self,
        page_num: int = 1,
        page_size: int = 60,
        province: str = "",  # 省份名 or 代码
        city: str = "",      # 城市名 or 代码（暂用省代码映射）
        status: str = "",    # 项目状态
        keyword: str = "",   # 搜索关键词
    ) -> dict[str, Any]:
        """
        获取项目列表（getBigdataList3_5）

        参数:
            province: 省份名/直辖市名，如 "上海", "北京", "广东"
            status: "未开业"/"已开业"/""（全部）
        """
        # province 可以是城市名或直接代码
        # 由于城市代码是网站内部的 ID 系统，不做自动映射
        # 用户可以直接传入数字代码（如上海的省份代码为 "309"）
        qy_p = province if province else ""

        body = {
            "pageNum": page_num,
            "orderBy": "1",
            "pageSize": page_size,
            "zsxq_yt1": "",
            "zsxq_yt2": "",
            "qy_p": qy_p,
            "qy_c": "",
            "qy_a": "",
            "xmzt": PROJECT_STATUS.get(status, status),
            "key": keyword,
            "wuyelx": "",
            "isHaveLink": "",
            "ifdporyt": "",
        }

        headers = self._build_auth_headers()

        try:
            resp = await self._client.post(
                "/wsapi/project/getBigdataList3_5",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise WinshangAPIError(
                f"项目列表 API {e.response.status_code}: {e.response.text}"
            ) from e
        except Exception as e:
            raise WinshangAPIError(f"项目列表请求失败: {e}") from e

        if data.get("code") != 0:
            raise WinshangAPIError(
                f"项目列表返回错误: code={data.get('code')}, msg={data.get('msg')}"
            )

        return data.get("data", {})

    async def get_project_detail(self, project_id: int) -> dict[str, Any]:
        """
        获取项目详情（detailContent）
        返回: { projectId, kaiFaShang, projectJieShao, zhouBianJieShao, companyJieShao }
        """
        body = {"projectId": project_id}
        headers = self._build_auth_headers()

        try:
            resp = await self._client.post(
                "/wsapi/project/detailContent",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            raise WinshangAPIError(
                f"项目详情 API {e.response.status_code}: {e.response.text}"
            ) from e
        except Exception as e:
            raise WinshangAPIError(f"项目详情请求失败: {e}") from e

        if data.get("code") != 0:
            raise WinshangAPIError(
                f"项目详情返回错误: code={data.get('code')}, msg={data.get('msg')}"
            )

        return data.get("data", {})

    async def get_all_projects(
        self,
        province: str = "",
        status: str = "未开业",
        max_pages: int = 999,
    ) -> list[dict[str, Any]]:
        """
        获取所有页的项目列表。默认只筛选"未开业"。
        每页请求间隔 1-2s 避免触发限流。
        返回扁平化的项目列表。
        """
        all_projects: list[dict[str, Any]] = []
        page = 1
        retries = 0

        while page <= max_pages:
            logger.info("正在获取项目列表第 %s 页...", page)
            try:
                data = await self.get_project_list(
                    page_num=page,
                    province=province,
                    status=status,
                )
            except WinshangAPIError as e:
                # 限流或系统繁忙时等待重试
                if "限流" in str(e) or "系统繁忙" in str(e):
                    retries += 1
                    wait = min(30 * retries, 120)
                    logger.warning(
                        "触发了限流（第 %s 次），等待 %s 秒后重试...",
                        retries, wait,
                    )
                    await asyncio.sleep(wait)
                    continue  # 不翻页，重试当前页
                raise

            # 成功 → 重置重试计数
            retries = 0

            total = data.get("total", 0)
            items = data.get("list", [])
            if not items:
                break

            all_projects.extend(items)
            logger.info(
                "第 %s 页获取 %s 条，累计 %s / %s 条",
                page, len(items), len(all_projects), total,
            )

            if len(all_projects) >= total:
                break
            page += 1

            # 每页间隔 1-2s，避免触发限流
            await asyncio.sleep(random.uniform(1.0, 2.0))

        return all_projects

    def get_cookies(self) -> dict[str, str]:
        """返回当前会话的 cookies"""
        return dict(self._cookies)

    def get_token(self) -> str | None:
        """返回当前 JWT token"""
        return self._token
