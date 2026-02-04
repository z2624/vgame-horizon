"""
Vercel Serverless Function - 简单 HTTP Handler
"""

import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timezone

# 设置 Python 路径
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from igdb_client import create_client_from_env, IGDBClient
from detail_fetcher import create_fetcher_from_env, translate_game_names


# 知名厂商列表
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


def format_date(timestamp):
    if not timestamp:
        return None
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def get_companies(game, role="developer"):
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


def get_genres(game):
    genres = game.get("genres", [])
    if not genres:
        return []
    return [g.get("name", "") for g in genres if isinstance(g, dict) and g.get("name")]


def get_cover_url(game):
    cover = game.get("cover", {})
    if isinstance(cover, dict) and cover.get("url"):
        url = cover["url"]
        return url.replace("t_thumb", "t_cover_big")
    return None


def is_notable_game(game):
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


def convert_game(game, cn_name=None):
    return {
        "id": game.get("id", 0),
        "name": game.get("name", "Unknown"),
        "name_cn": cn_name,
        "release_date": format_date(game.get("first_release_date")),
        "developer": get_companies(game, "developer"),
        "publisher": get_companies(game, "publisher"),
        "genres": get_genres(game),
        "summary": game.get("summary"),
        "cover_url": get_cover_url(game),
        "is_notable": is_notable_game(game)
    }


def handle_get_games(params):
    """处理 /api/games 请求"""
    igdb_client = create_client_from_env()
    
    if not igdb_client:
        return {"error": "IGDB 服务不可用，请检查环境变量配置"}, 503
    
    now = datetime.now()
    year = int(params.get("year", [str(now.year)])[0])
    month = int(params.get("month", [str(now.month)])[0])
    limit = int(params.get("limit", ["50"])[0])
    translate = params.get("translate", ["true"])[0].lower() == "true"
    
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
    
    return {
        "year": year,
        "month": month,
        "total": len(game_list),
        "games": game_list
    }, 200


def handle_get_detail(game_name, params):
    """处理 /api/games/{name}/detail 请求"""
    fetcher = create_fetcher_from_env()
    
    if not fetcher:
        return {"error": "LLM 服务不可用"}, 503
    
    fallback_name = params.get("fallback_name", [None])[0]
    
    details = fetcher.fetch(game_name)
    
    if not details and fallback_name and fallback_name != game_name:
        details = fetcher.fetch(fallback_name)
    
    if not details:
        return {
            "name": game_name,
            "directors": [],
            "writers": [],
            "composers": [],
            "producers": [],
            "series": None,
            "related_games": [],
            "highlights": []
        }, 200
    
    return {
        "name": details.name,
        "directors": [{"name": d.name, "known_for": d.known_for} for d in details.directors],
        "writers": [{"name": w.name, "known_for": w.known_for} for w in details.writers],
        "composers": [{"name": c.name, "known_for": c.known_for} for c in details.composers],
        "producers": [{"name": p.name, "known_for": p.known_for} for p in details.producers],
        "series": details.series or None,
        "related_games": details.related_games,
        "highlights": details.highlights
    }, 200


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)
        
        # CORS headers
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        
        try:
            if path == "/api/games" or path == "/api/games/":
                data, status = handle_get_games(params)
            elif path.startswith("/api/games/") and path.endswith("/detail"):
                # 提取游戏名: /api/games/{name}/detail
                parts = path.split("/")
                game_name = parts[3] if len(parts) > 3 else ""
                # URL 解码
                from urllib.parse import unquote
                game_name = unquote(game_name)
                data, status = handle_get_detail(game_name, params)
            else:
                data, status = {"error": "Not found"}, 404
        except Exception as e:
            data, status = {"error": str(e)}, 500
        
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
        return
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        return
