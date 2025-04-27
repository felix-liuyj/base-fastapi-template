from asyncio import sleep
from enum import Enum

from httpx import AsyncClient, TimeoutException, ConnectError, HTTPStatusError, RequestError

__all__ = (
    'request_get_with_retry',
    'request_post_with_retry',
    'request_put_with_retry',
    'request_delete_with_retry',
)


class RequestMethodEnum(Enum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    DELETE = 'DELETE'


async def request_get_with_retry(url, headers=None, params=None, retries=3):
    await request_with_retry(url, RequestMethodEnum.GET, headers, params, retries)


async def request_post_with_retry(url, headers=None, params=None, retries=3):
    await request_with_retry(url, RequestMethodEnum.POST, headers, params, retries)


async def request_put_with_retry(url, headers=None, params=None, retries=3):
    await request_with_retry(url, RequestMethodEnum.PUT, headers, params, retries)


async def request_delete_with_retry(url, headers=None, params=None, retries=3):
    await request_with_retry(url, RequestMethodEnum.DELETE, headers, params, retries)


async def request_with_retry(url, method: RequestMethodEnum, headers=None, params=None, retries=3):
    """封装 GET 请求，支持异步 & 重试"""
    async with AsyncClient() as client:
        for attempt in range(retries):
            try:
                response = await client.request(method.value, url, headers=headers, params=params, timeout=10)
                # 如果 HTTP 状态码 >= 400，抛出异常
                return response.raise_for_status().json()  # 返回解析后的 JSON 数据
            except TimeoutException:
                print(f"⚠️ [警告] 请求超时，重试 {attempt + 1}/{retries}...")
            except ConnectError:
                print(f"⚠️ [警告] 连接失败，检查网络或 API 地址...")
            except HTTPStatusError as e:
                print(f"⚠️ [错误] HTTP 请求失败: {e.response.status_code} - {e.response.text}")
                break  # 如果是 HTTP 4xx 或 5xx 错误，不要重试
            except RequestError as e:
                print(f"⚠️ [错误] 发生请求异常: {str(e)}")
                break
            except ValueError:
                print("⚠️ [错误] 无法解析 JSON 响应数据")
                break
            await sleep(2)  # 失败后等待 2 秒
    return None  # 失败返回 None
