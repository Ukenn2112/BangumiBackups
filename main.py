import asyncio
import json
import os
import sqlite3
import time
from math import ceil

import requests
from rich.console import Console
from rich.progress import track
from rich.prompt import IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

from api import BangumiAPI


class BangumiBackups(BangumiAPI):
    _config_file = 'config.json'
    _backups_path = './backup_data/'

    def __init__(self):
        super().__init__()
        self.console = Console()
        self.table = Table()

        if not os.path.exists(self._backups_path): os.makedirs(self._backups_path)
        self.conn = sqlite3.connect(f'{self._backups_path}{time.strftime("%y%m%d_%H%M%S", time.localtime())}.db', timeout=5)

        self.console.rule('Welcome to Bangumi Backups')
        if os.path.exists(self._config_file):
            with open(self._config_file, 'r') as f:
                params = json.loads(f.read())
                self.access_token = params['access_token']
                self.username = params['username']
                self.console.log(f'[bold green][初始化][/] 检测到配置文件，User Name: [bold green]{self.username}[/]')
        else:
            self.console.log('[bold green][初始化][/] 没有找到 "config.json" 配置文件! ')
            self.console.log('[bold green][初始化][/] 前往 https://next.bgm.tv/demo/access-token 生成 Access Token')
            self.access_token = Prompt.ask(Text.assemble(("请输入 Access Token")), console=self.console)
            with self.console.status("[bold green][初始化中][/] 正在获取 username..."):
                try:
                    self.username = requests.get('https://api.bgm.tv/v0/me', 
                    headers={'User-Agent':'Ukenn/BangumiBackups', 'Authorization': f'Bearer {self.access_token}'}).json()['username']
                except:
                    self.console.log('[bold red][初始化失败][/] 请检查 Access Token 是否正确')
                    exit(1)
                self.console.log(f'[bold green][初始化成功][/] 获取到 User Name: [bold green]{self.username}[/]')
                cfg = json.dumps({
                    'username': self.username,
                    'access_token': self.access_token
                }, ensure_ascii=False).encode()
                with open('config.json', "wb") as cf:
                    cf.write(cfg)
                    cf.flush()
            self.console.log('[bold green][初始化完成][/] 已将配置保存至 "config.json"')

    async def main_menu(self) -> None:
        self.console.rule('>> 操作选项', align='left')
        self.console.log(
            '[bold yellow]> 1. 备份收藏列表 [/]\n'
            '[bold red]> 2. 退出 [/]\n')
        op = IntPrompt.ask(Text.assemble(("请输入操作序号")), default=2, choices=["1", "2"], console=self.console)
        if op == 1:
            return await self.collections()
        elif op == 2:
            return
    
    async def collections(self) -> None:
        self.console.rule('>>> 备份收藏列表', align='left')
        self.console.log(
            '[bold yellow]> 1. 全部备份 [/]\n'
            '[bold yellow]> 2. 按类型备份 [/]\n'
            '[bold red]> 3. 返回上一级 [/]\n')
        op = IntPrompt.ask(Text.assemble(("请输入操作序号")), default=1, choices=["1", "2", "3"], console=self.console)
        if op == 1:
            return await self.collections_backup_all()
        elif op == 2:
            return await self.collections_backup_by_subject_type()
        elif op == 3:
            return await self.main_menu()
    
    async def collections_backup_all(self) -> None:
        self.console.rule('>>>> 备份全部收藏列表', align='left')
        total = await self.get_collections()
        for i in track(range(ceil(total["total"]/50)), description=f'[bold green][备份中][/] 共 {total["total"]} 个条目...'):
            self.data = await self.get_collections(i)
            await self.save_collections()
    
    async def collections_backup_by_subject_type(self) -> None:
        self.console.rule('>>>> 按类型备份 选择条目类型', align='left')
        self.console.log(
            '[bold yellow]> 1. 书籍 [/]\n'
            '[bold yellow]> 2. 动画 [/]\n'
            '[bold yellow]> 3. 音乐 [/]\n'
            '[bold yellow]> 4. 游戏 [/]\n'
            '[bold yellow]> 6. 三次元 [/]\n'
            '[bold yellow]> 7. 全部 [/]\n'
            '[bold red]> 8. 返回上一级 [/]\n')
        op = IntPrompt.ask(Text.assemble(("请输入操作序号")), default=2, choices=["1", "2", "3", "4", "6", "7", "8"], console=self.console)
        if op == 7:
            return await self.collections_backup_by_type(None)
        elif op == 8:
            return await self.collections()
        else:
            return await self.collections_backup_by_type(op)
    
    async def collections_backup_by_type(self, subject_type) -> None:
        self.console.rule('>>>> 按类型备份 选择收藏类型', align='left')
        self.console.log(
            '[bold yellow]> 1. 想看 [/]\n'
            '[bold yellow]> 2. 看过 [/]\n'
            '[bold yellow]> 3. 在看 [/]\n'
            '[bold yellow]> 4. 搁置 [/]\n'
            '[bold yellow]> 5. 抛弃 [/]\n'
            '[bold yellow]> 6. 全部 [/]\n'
            '[bold red]> 7. 返回上一级 [/]\n')
        op = IntPrompt.ask(Text.assemble(("请输入操作序号")), default=2, choices=["1", "2", "3", "4", "5", "6", "7"], console=self.console)
        if op == 6 and subject_type is None:
            return await self.collections_backup_all()
        elif op == 6:
            op = None
            total = await self.get_collections(subject_type=subject_type)
        elif op == 7:
            return await self.collections()
        else:
            total = await self.get_collections(type=op, subject_type=subject_type)
        
        for i in track(range(ceil(total["total"]/50)), description=f'[bold green][备份中][/] 共 {total["total"]} 个条目...'):
            self.data = await self.get_collections(pages=i, type=op, subject_type=subject_type)
            await self.save_collections()

    async def save_collections(self) -> dict:
        """保存备份至数据库"""
        self.conn.execute(
            '''create table if not exists
            collections(
            id integer primary key AUTOINCREMENT,
            bgm_id integer,
            name varchar(128),
            rate integer,
            type integer,
            subject_type integer,
            comment varchar(128),
            tags varchar(128),
            updated_at varchar(128))
            '''
        )
        for data in self.data['data']:
            self.conn.execute(
                '''insert into collections(bgm_id, name, rate, type, subject_type, comment, tags, updated_at) values(?, ?, ?, ?, ?, ?, ?, ?)''',
                (data['subject_id'], data['subject']['name'], data['rate'], data["type"], data["subject_type"], data["comment"], str(data["tags"]), data["updated_at"])
            )
        self.conn.commit()
        

async def main_menu():
    async with BangumiBackups() as i:       
        await i.main_menu()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main_menu())