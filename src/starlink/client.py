from utils import config_path, response_to_str, setup

setup()

import asyncio
import json
import logging
from os import getenv
from typing import Any, Optional
from urllib.parse import unquote

from captcha import CaptchaSolver
from httpx import AsyncClient, Response
from bs4 import BeautifulSoup


class StarlinkClient:
    def __init__(self) -> None:
        self.login = getenv("STARLINK_LOGIN")
        self.password = getenv("STARLINK_PASSWORD")

        self.headers = self.__load_headers()
        self.proxy = self.__load_proxy()

        self.encoding = "utf-8"

        self.client = AsyncClient(
            headers=self.headers,
            proxies=self.proxy,
            event_hooks={
                "response": [self.__track_response],
            },
        )
        self.solver = CaptchaSolver("https://auth.starlink.com")

        self.callback_url: Optional[str] = None

    async def __track_response(self, response: Response):
        log = await response_to_str(response)
        logging.debug(log)

        url = str(response.request.url)

        if response.status_code >= 400:
            raise Exception(f"Request failed {url}")

        if url.startswith("https://auth.starlink.com?ReturnUrl"):
            return_url = url.split("ReturnUrl=")[1].split("&")[0]
            self.callback_url = unquote(return_url)

        return response

    def __load_headers(self) -> dict:
        with open(config_path("headers.json"), "r") as f:
            return json.load(f)

    def __load_proxy(self) -> Optional[dict]:
        proxy = getenv("PROXY")
        if proxy:
            return {"http://": proxy, "https://": proxy}
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.client.aclose()

    def __log_cookies(self):
        cookies = {k: v for k, v in self.client.cookies.items()}
        logging.info(f"Cookies: {cookies}")

    async def __get(self, url: str) -> bytes:
        logging.info(f"GET {url}")
        response = await self.client.get(url, follow_redirects=True)
        self.__log_cookies()
        return response.content

    async def __post(
        self,
        url: str,
        json_data: Optional[dict] = None,
        data: Optional[Any] = None,
        extra_headers: Optional[dict] = None,
    ) -> bytes:
        if not json_data and not data:
            raise Exception("Either json_data or data must be provided")

        logging.info(f"POST {url}")

        headers = self.headers.copy()
        headers.update(extra_headers or {})

        response = await self.client.post(
            url, json=json_data, data=data, follow_redirects=True, headers=headers
        )
        self.__log_cookies()
        return response.content

    async def __get_site_key(self) -> str:
        response = await self.__get("https://www.starlink.com/account/environment.js")
        data = response.decode(self.encoding)
        site_key = data.split("captchaKey: '")[1].split("'")[0]
        return site_key

    def __parse_sign_in_form_data(self, response: bytes) -> dict:
        html = response.decode(self.encoding)
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        inputs = form.find_all("input")  # type: ignore
        data = {i["name"]: i["value"] for i in inputs}
        return data

    async def __handle_callback(self):
        if self.callback_url:
            response = await self.__get(self.callback_url)
            form_data = self.__parse_sign_in_form_data(response)
            await self.__post(
                "https://api.starlink.com/auth-rp/auth/callback",
                data=form_data,
                extra_headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        else:
            error = "Callback URL not found"
            logging.error(error)
            raise Exception(error)

    async def sign_in(self):
        await self.__get(
            "https://api.starlink.com/auth-rp/auth/login?returnUrl=https%3A%2F%2Fwww.starlink.com%2Faccount"
        )
        site_key = await self.__get_site_key()
        token = self.solver.solve(site_key)

        await self.__post(
            "https://api.starlink.com/auth/v1/sign-in",
            {
                "captchaToken": token,
                "email": self.login,
                "password": self.password,
            },
        )

        await self.__handle_callback()

    async def assets(self):
        result = await self.__get(
            "https://api.starlink.com/webagg/v2/accounts/assets?limit=10&page=0&isConverting=false&serviceAddressId=&onlyActive=false&searchString="
        )
        return result

    async def get_assets(self):
        await self.sign_in()
        result = await self.assets()
        return result


async def main():
    async with StarlinkClient() as client:
        await client.get_assets()


if __name__ == "__main__":
    asyncio.run(main())
