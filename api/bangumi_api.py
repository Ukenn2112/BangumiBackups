import re
import asyncio
import aiohttp
from lxml import etree


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

    async def get_subject_collections(self, pages: int = 0, type: int = None, subject_type: int = None) -> dict:
        """请求条目收藏列表"""
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
    
    async def get_mono_collections(self, pages: int = 1, _type: int = None) -> dict:
        """请求人物收藏列表"""
        try:
            params = {"page": pages}
            if _type is None: type = ["character", "person"]
            elif _type == 1: type = ["character"]
            elif _type == 2: type = ["person"]
            out = {"data": [], "total": 0}
            for t in type:
                async with self.s.get(f'https://bgm.tv/user/{self.username}/mono/{t}', params=params) as resp:
                    res = await resp.text()
                    html = etree.HTML(res)
                    _names = html.xpath('//ul[@class="coversSmall"]/li/a/text()')
                    _ids = html.xpath('//ul[@class="coversSmall"]/li/a[1]/@href')
                    for name, pid in zip(_names, _ids):
                        out["data"].append({"name": name, "person_id": int(pid.split(f"/{t}/")[-1]), "type": t})
                    if pages == 1:
                        p = html.xpath('//span[@class="p_edge"]/text()')
                        if p:
                            pag = re.findall(r'\(\xa0[0-9]+\xa0/\xa0([0-9]+)\xa0\)', p[0])[0]
                            async with self.s.get(f'https://bgm.tv/user/{self.username}/mono/{t}', params={"page": pag}) as resp:
                                ress = await resp.text()
                                htmll = etree.HTML(ress)
                                out["total"] += int(pag) * 28 + len(htmll.xpath('//ul[@class="coversSmall"]/li/a[1]/@href'))
                        else:
                            pag = len(html.xpath('//div[@id="columnA"]/div[2]/a/text()'))
                            if pag == 0:
                                out["total"] += len(html.xpath('//ul[@class="coversSmall"]/li/a[1]/@href'))
                            out["total"] += pag * 28
            return out
        except asyncio.TimeoutError:
            return {'error': 1, 'reason': "Request timed out"}
