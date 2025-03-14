import requests
from typing import Optional, Dict, Any
import aiohttp
class HttpClientBase:
    @classmethod
    async def _method(cls, method: str, url: str, headers: dict = None, json_body: dict = None, params=None, timeout=5):
        if not headers:
            headers = {}

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url,
                                       params=params,
                                       json=json_body,
                                       headers=headers,
                                       timeout=aiohttp.ClientTimeout(total=timeout)
                                       ) as response:
                if response.status != 200:
                    raise Exception(f'{url} 调用失败: {response.status}')
                return await response.json()

    @classmethod
    async def post(cls, url: str, headers: dict = None, json_body: dict = None, params=None, timeout=5):
        return await cls._method('POST', url=url, headers=headers, json_body=json_body, params=params, timeout=timeout)

    @classmethod
    async def get(cls, url: str, headers: dict = None, params=None, timeout=5):
        return await cls._method('GET', url=url, headers=headers, params=params, timeout=timeout)

    @classmethod
    async def put(cls, url: str, headers: dict = None, json_body: dict = None, params=None, timeout=5):
        return await cls._method("PUT", url=url, headers=headers, json_body=json_body, params=params, timeout=timeout)
