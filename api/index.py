"""
Vercel Serverless Function 入口
将 FastAPI 应用暴露给 Vercel
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 从同目录导入
try:
    # Vercel 环境
    from api.igdb_client import create_client_from_env, IGDBClient
    from api.detail_fetcher import create_fetcher_from_env, translate_game_names
except ImportError:
    # 本地环境
    from igdb_client import create_client_from_env, IGDBClient
    from detail_fetcher import create_fetcher_from_env, translate_game_names


# 知名厂商/系列列表
NOTABLE_DEVELOPERS = {
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
    "Team Cherry",
    "Supergiant Games",
    "Moon Studios",
    "Yacht Club Games",
    "Motion Twin",
    "ConcernedApe",
}

NOTABLE_HYPES_THRESHOLD = 10


# 数据模型
class GameBasic(BaseModel):
    id: int
    name: str
    name_cn: Optional[str] = None
    release_date: Optional[str] = None
    developer: Optional[str] = None
    publisher: Optional[str] = None
    genres: list[str] = []
    summary: Optional[str] = None
    cover_url: Optional[str] = None
    is_notable: bool = False


class GameDetail(BaseModel):
    name: str
    directors: list[dict] = []
    writers: list[dict] = []
    composers: list[dict] = []
    producers: list[dict] = []
    series: Optional[str] = None
    related_games: list[str] = []
    highlights: list[str] = []


class GamesResponse(BaseModel):
    year: int
    month: int
    total: int
    games: list[GameBasic]


# 辅助函数
def format_date(timestamp: Optional[int]) -> Optional[str]:
    if not timestamp:
        return None
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def get_companies(game: dict, role: str = "developer") -> Optional[str]:
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
    genres = game.get("genres", [])
    if not genres:
        return []
    return [g.get("name", "") for g in genres if isinstance(g, dict) and g.get("name")]


def get_cover_url(game: dict) -> Optional[str]:
    cover = game.get("cover", {})
    if isinstance(cover, dict) and cover.get("url"):
        url = cover["url"]
        return url.replace("t_thumb", "t_cover_big")
    return None


def is_notable_game(game: dict) -> bool:
    hypes = game.get("hypes") or 0
    if hypes >= NOTABLE_HYPES_THRESHOLD:
        return True
    
    involved = game.get("involved_companies", [])
    for ic in involved:
        company = ic.get("company", {})
        if isinstance(company, dict):
            company_name = company.get("name", "")
            for notable in NOTABLE_DEVELOPERS:
                if notable.lower() in company_name.lower() or company_name.lower() in notable.lower():
                    return True
    
    return False


def convert_game(game: dict, cn_name: Optional[str] = None) -> GameBasic:
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


# FastAPI 应用
app = FastAPI(title="VGame Horizon API")


@app.get("/api/games", response_model=GamesResponse)
async def get_games(
    year: int = Query(default=None),
    month: int = Query(default=None, ge=1, le=12),
    limit: int = Query(default=50, ge=1, le=100),
    translate: bool = Query(default=True)
):
    """获取指定月份的 Switch 新游列表"""
    igdb_client = create_client_from_env()
    
    if not igdb_client:
        raise HTTPException(status_code=503, detail="IGDB 服务不可用，请检查环境变量配置")
    
    now = datetime.now()
    year = year or now.year
    month = month or now.month
    
    games = igdb_client.get_upcoming_games(
        platform_id=IGDBClient.PLATFORM_SWITCH,
        year=year,
        month=month,
        limit=limit
    )
    
    cn_names = {}
    if translate and games:
        english_names = [g.get("name", "") for g in games if g.get("name")]
        cn_names = translate_game_names(english_names)
    
    game_list = []
    for game in games:
        en_name = game.get("name", "")
        cn_name = cn_names.get(en_name)
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
    fallback_name: Optional[str] = Query(default=None)
):
    """获取游戏深度信息"""
    fetcher = create_fetcher_from_env()
    
    if not fetcher:
        raise HTTPException(status_code=503, detail="LLM 服务不可用")
    
    details = fetcher.fetch(game_name)
    
    if not details and fallback_name and fallback_name != game_name:
        details = fetcher.fetch(fallback_name)
    
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


# Vercel 需要的 handler
handler = app
