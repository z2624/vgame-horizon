"""
IGDB API 客户端
用于获取游戏数据
"""

import os
import requests
from datetime import datetime, timezone
from typing import Optional


class IGDBClient:
    """IGDB API 客户端"""
    
    # 平台 ID
    PLATFORM_SWITCH = 130
    PLATFORM_PS5 = 167
    PLATFORM_XBOX_SERIES = 169
    PLATFORM_PC = 6
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.base_url = "https://api.igdb.com/v4"
    
    def authenticate(self) -> bool:
        """获取 Twitch OAuth 访问令牌"""
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            self.access_token = data.get("access_token")
            return True
        except requests.RequestException as e:
            print(f"认证失败: {e}")
            return False
    
    def _request(self, endpoint: str, query: str) -> list:
        """发送 API 请求"""
        if not self.access_token:
            if not self.authenticate():
                return []
        
        headers = {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json"
        }
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.post(url, headers=headers, data=query)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"API 请求失败: {e}")
            return []
    
    def get_upcoming_games(
        self,
        platform_id: int = PLATFORM_SWITCH,
        year: int = None,
        month: int = None,
        limit: int = 50
    ) -> list:
        """
        获取指定平台即将发售的游戏
        
        Args:
            platform_id: 平台 ID (默认 Switch = 130)
            year: 年份 (默认当前年份)
            month: 月份 (默认当前月份)
            limit: 返回数量限制
            
        Returns:
            游戏列表
        """
        now = datetime.now(timezone.utc)
        year = year or now.year
        month = month or now.month
        
        # 计算月份的开始和结束时间戳
        start_date = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())
        
        query = f"""
            fields name, summary, first_release_date, 
                   involved_companies.company.name, 
                   involved_companies.developer,
                   involved_companies.publisher,
                   cover.url,
                   genres.name,
                   platforms.name,
                   alternative_names.name,
                   alternative_names.comment,
                   hypes,
                   url;
            where platforms = ({platform_id}) 
                & first_release_date >= {start_ts} 
                & first_release_date < {end_ts};
            sort first_release_date asc;
            limit {limit};
        """
        
        return self._request("games", query)
    
    def get_game_details(self, game_id: int) -> dict:
        """
        获取游戏详细信息（包括制作人员）
        
        Args:
            game_id: 游戏 ID
            
        Returns:
            游戏详情
        """
        query = f"""
            fields name, summary, storyline, first_release_date,
                   involved_companies.company.name,
                   involved_companies.developer,
                   involved_companies.publisher,
                   cover.url,
                   genres.name,
                   themes.name,
                   game_modes.name,
                   player_perspectives.name,
                   franchises.name,
                   collection.name,
                   similar_games.name,
                   websites.url,
                   websites.category,
                   url;
            where id = {game_id};
        """
        
        results = self._request("games", query)
        return results[0] if results else {}
    
    def search_games(self, keyword: str, platform_id: int = None, limit: int = 20) -> list:
        """
        搜索游戏
        
        Args:
            keyword: 搜索关键词
            platform_id: 可选，平台过滤
            limit: 返回数量限制
            
        Returns:
            游戏列表
        """
        platform_filter = f"& platforms = ({platform_id})" if platform_id else ""
        
        query = f"""
            search "{keyword}";
            fields name, summary, first_release_date,
                   involved_companies.company.name,
                   involved_companies.developer,
                   cover.url,
                   platforms.name;
            where category = 0 {platform_filter};
            limit {limit};
        """
        
        return self._request("games", query)


def create_client_from_env() -> Optional[IGDBClient]:
    """从环境变量创建客户端"""
    from dotenv import load_dotenv
    load_dotenv()
    
    client_id = os.getenv("TWITCH_CLIENT_ID")
    client_secret = os.getenv("TWITCH_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("错误: 请在 .env 文件中配置 TWITCH_CLIENT_ID 和 TWITCH_CLIENT_SECRET")
        print("参考 .env.example 文件")
        return None
    
    return IGDBClient(client_id, client_secret)
