import asyncio
import aiohttp


class BangumiAPI:
    api_url = 'https://api.bgm.tv/v0'

    def __init__(self, access_token: str = '', username: str = ''):
        self.access_token = access_token
        self.username = username

    async def __aenter__(self):
        self.s = aiohttp.ClientSession(
            headers={
                'User-Agent':'Ukenn/BangumiBackups',
                'Authorization': 'Bearer ' + self.access_token
            },
            timeout=aiohttp.ClientTimeout(total=10),
        )
        return self

    async def __aexit__(self, exc_t, exc_v, exc_tb):
        await self.s.close()

    async def get_collections(self, pages: int = 0, type: int = None, subject_type: int = None) -> dict:
        """请求收藏列表"""
        try:
            params = {"limit": 50, "offset": pages * 50}
            if type is not None:
                params["type"] = type
            if subject_type is not None:
                params["subject_type"] = subject_type
            async with self.s.get(f'{self.api_url}/users/{self.username}/collections', params=params) as resp:
                res = await resp.json()
            return res
        except asyncio.TimeoutError:
            return {'error': 1, 'reason': "Request timed out"}
