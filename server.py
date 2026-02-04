#!/usr/bin/env python3
"""
VGame Horizon - Web 服务端
基于 FastAPI 的 API 服务
"""

import os
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from igdb_client import create_client_from_env, IGDBClient
from detail_fetcher import create_fetcher_from_env, translate_game_names


# 全局客户端实例
igdb_client: Optional[IGDBClient] = None


# 知名厂商/系列列表（用于判断是否显示"明星团队"按钮）
NOTABLE_DEVELOPERS = {
    # 日本大厂
    "Nintendo", "Nintendo EPD", "Nintendo EAD",
    "Square Enix", "Square", "Enix",
    "Bandai Namco", "Bandai Namco Entertainment", "Bandai Namco Studios",
    "Capcom", "CAPCOM",
    "Konami", "Konami Digital Entertainment",
    "SEGA", "Sega",
    "Atlus", "ATLUS",
    "Koei Tecmo", "Koei Tecmo Games", "Omega Force", "Team Ninja",
    "Level-5", "Level5",
    "FromSoftware", "From Software",
    "PlatinumGames", "Platinum Games",
    "Falcom", "Nihon Falcom",
    "NIS", "Nippon Ichi Software",
    "Arc System Works",
    "Spike Chunsoft",
    "Grasshopper Manufacture",
    "Vanillaware",
    "Game Freak",
    "HAL Laboratory",
    "Intelligent Systems",
    "Monolith Soft",
    "Retro Studios",
    # 欧美大厂
    "Ubisoft", "Ubisoft Montreal", "Ubisoft Paris",
    "Electronic Arts", "EA", "EA Sports",
    "Activision", "Activision Blizzard",
    "Blizzard", "Blizzard Entertainment",
    "Bethesda", "Bethesda Game Studios", "Bethesda Softworks",
    "2K Games", "2K", "Firaxis Games",
    "Rockstar Games", "Rockstar North",
    "Warner Bros", "WB Games",
    "CD Projekt", "CD Projekt Red",
    "Devolver Digital",
    "505 Games",
    "THQ Nordic",
    # 独立游戏知名工作室
    "Team Cherry",
    "Supergiant Games",
    "Moon Studios",
    "Yacht Club Games",
    "Motion Twin",
    "ConcernedApe",
}

# hypes 阈值
NOTABLE_HYPES_THRESHOLD = 10


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global igdb_client
    igdb_client = create_client_from_env()
    if igdb_client:
        print("✅ IGDB 客户端初始化成功")
    else:
        print("⚠️ IGDB 客户端初始化失败，请检查配置")
    yield


app = FastAPI(
    title="VGame Horizon",
    description="Switch 新游时间线 API",
    version="1.0.0",
    lifespan=lifespan
)


# 数据模型
class GameBasic(BaseModel):
    """游戏基础信息"""
    id: int
    name: str
    name_cn: Optional[str] = None
    release_date: Optional[str] = None
    developer: Optional[str] = None
    publisher: Optional[str] = None
    genres: list[str] = []
    summary: Optional[str] = None
    cover_url: Optional[str] = None
    is_notable: bool = False  # 是否为知名游戏（显示"明星团队"按钮）


class GameDetail(BaseModel):
    """游戏深度信息"""
    name: str
    directors: list[dict] = []
    writers: list[dict] = []
    composers: list[dict] = []
    producers: list[dict] = []
    series: Optional[str] = None
    related_games: list[str] = []
    highlights: list[str] = []


class GamesResponse(BaseModel):
    """游戏列表响应"""
    year: int
    month: int
    total: int
    games: list[GameBasic]


# 辅助函数
def format_date(timestamp: Optional[int]) -> Optional[str]:
    """格式化时间戳"""
    if not timestamp:
        return None
    from datetime import timezone
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def get_companies(game: dict, role: str = "developer") -> Optional[str]:
    """获取公司名称"""
    involved = game.get("involved_companies", [])
    if not involved:
        return None
    
    companies = []
    for ic in involved:
        if role == "developer" and ic.get("developer"):
            company = ic.get("company", {})
            if isinstance(company, dict):
                companies.append(company.get("name", ""))
        elif role == "publisher" and ic.get("publisher"):
            company = ic.get("company", {})
            if isinstance(company, dict):
                companies.append(company.get("name", ""))
    
    return ", ".join(companies) if companies else None


def get_genres(game: dict) -> list[str]:
    """获取游戏类型"""
    genres = game.get("genres", [])
    if not genres:
        return []
    return [g.get("name", "") for g in genres if isinstance(g, dict) and g.get("name")]


def get_cover_url(game: dict) -> Optional[str]:
    """获取封面图 URL"""
    cover = game.get("cover", {})
    if isinstance(cover, dict) and cover.get("url"):
        url = cover["url"]
        # 转换为大图
        return url.replace("t_thumb", "t_cover_big")
    return None


def is_notable_game(game: dict) -> bool:
    """
    判断是否为知名游戏（应显示"明星团队"按钮）
    
    判断条件（满足任一即可）：
    1. hypes >= 10
    2. 开发商/发行商在知名厂商列表中
    """
    # 条件1: hypes 达到阈值
    hypes = game.get("hypes") or 0
    if hypes >= NOTABLE_HYPES_THRESHOLD:
        return True
    
    # 条件2: 开发商/发行商在知名列表中
    involved = game.get("involved_companies", [])
    for ic in involved:
        company = ic.get("company", {})
        if isinstance(company, dict):
            company_name = company.get("name", "")
            # 检查是否匹配知名厂商（支持部分匹配）
            for notable in NOTABLE_DEVELOPERS:
                if notable.lower() in company_name.lower() or company_name.lower() in notable.lower():
                    return True
    
    return False


def convert_game(game: dict, cn_name: Optional[str] = None) -> GameBasic:
    """转换游戏数据格式"""
    return GameBasic(
        id=game.get("id", 0),
        name=game.get("name", "Unknown"),
        name_cn=cn_name,
        release_date=format_date(game.get("first_release_date")),
        developer=get_companies(game, "developer"),
        publisher=get_companies(game, "publisher"),
        genres=get_genres(game),
        summary=game.get("summary"),
        cover_url=get_cover_url(game),
        is_notable=is_notable_game(game)
    )


# API 路由
@app.get("/api/games", response_model=GamesResponse)
async def get_games(
    year: int = Query(default=None, description="年份"),
    month: int = Query(default=None, ge=1, le=12, description="月份"),
    limit: int = Query(default=50, ge=1, le=100, description="数量限制"),
    translate: bool = Query(default=True, description="是否翻译中文名")
):
    """获取指定月份的 Switch 新游列表"""
    if not igdb_client:
        raise HTTPException(status_code=503, detail="IGDB 服务不可用")
    
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    
    # 获取游戏列表
    games = igdb_client.get_upcoming_games(
        platform_id=IGDBClient.PLATFORM_SWITCH,
        year=year,
        month=month,
        limit=limit
    )
    
    # 翻译中文名
    cn_names = {}
    if translate and games:
        english_names = [g.get("name", "") for g in games if g.get("name")]
        cn_names = translate_game_names(english_names)
    
    # 转换格式
    game_list = []
    for game in games:
        en_name = game.get("name", "")
        cn_name = cn_names.get(en_name)
        # 如果中文名和英文名相同，设为 None
        if cn_name == en_name:
            cn_name = None
        game_list.append(convert_game(game, cn_name))
    
    return GamesResponse(
        year=year,
        month=month,
        total=len(game_list),
        games=game_list
    )


@app.get("/api/games/{game_name}/detail", response_model=GameDetail)
async def get_game_detail(
    game_name: str,
    fallback_name: Optional[str] = Query(default=None, description="备用查询名（英文名）")
):
    """获取游戏深度信息"""
    fetcher = create_fetcher_from_env()
    
    if not fetcher:
        raise HTTPException(status_code=503, detail="LLM 服务不可用")
    
    # 优先用传入的名字查询
    details = fetcher.fetch(game_name)
    
    # 如果失败且有备用名，尝试用备用名查询
    if not details and fallback_name and fallback_name != game_name:
        details = fetcher.fetch(fallback_name)
    
    # 即使没有详情也返回空数据，让前端显示"暂无信息"
    if not details:
        return GameDetail(
            name=game_name,
            directors=[],
            writers=[],
            composers=[],
            producers=[],
            series=None,
            related_games=[],
            highlights=[]
        )
    
    return GameDetail(
        name=details.name,
        directors=[{"name": d.name, "known_for": d.known_for} for d in details.directors],
        writers=[{"name": w.name, "known_for": w.known_for} for w in details.writers],
        composers=[{"name": c.name, "known_for": c.known_for} for c in details.composers],
        producers=[{"name": p.name, "known_for": p.known_for} for p in details.producers],
        series=details.series or None,
        related_games=details.related_games,
        highlights=details.highlights
    )


# 静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    """首页"""
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
