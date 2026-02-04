"""
深度信息获取模块
使用 LLM + Web Search 获取游戏的制作人、编剧、编曲等深度信息
"""

import os
import json
from typing import Optional
from dataclasses import dataclass, field, asdict


@dataclass
class GameCredit:
    """游戏制作人员信息"""
    name: str
    role: str  # director, writer, composer, producer, etc.
    known_for: list[str] = field(default_factory=list)  # 代表作品


@dataclass
class GameDetails:
    """游戏深度信息"""
    name: str
    summary: str = ""
    
    # 核心制作人员
    directors: list[GameCredit] = field(default_factory=list)      # 监督/导演
    writers: list[GameCredit] = field(default_factory=list)        # 编剧/剧本
    composers: list[GameCredit] = field(default_factory=list)      # 作曲/音乐
    producers: list[GameCredit] = field(default_factory=list)      # 制作人
    designers: list[GameCredit] = field(default_factory=list)      # 设计师
    
    # 关联信息
    series: str = ""                    # 所属系列
    related_games: list[str] = field(default_factory=list)  # 关联作品（同制作人）
    
    # 额外信息
    highlights: list[str] = field(default_factory=list)     # 亮点/特色
    source_urls: list[str] = field(default_factory=list)    # 信息来源


class DetailFetcher:
    """深度信息获取器基类"""
    
    def fetch(self, game_name: str, basic_info: dict = None) -> Optional[GameDetails]:
        """获取游戏深度信息"""
        raise NotImplementedError


class OpenAIDetailFetcher(DetailFetcher):
    """使用 OpenAI API 获取深度信息"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    def _build_prompt(self, game_name: str, basic_info: dict = None) -> str:
        """构建搜索提示"""
        context = ""
        if basic_info:
            if basic_info.get("developer"):
                context += f"开发商: {basic_info['developer']}\n"
            if basic_info.get("publisher"):
                context += f"发行商: {basic_info['publisher']}\n"
            if basic_info.get("release_date"):
                context += f"发售日期: {basic_info['release_date']}\n"
        
        return f"""请搜索并整理游戏《{game_name}》的详细制作信息。

已知信息:
{context if context else "无"}

请提供以下信息（如果能找到）:
1. 监督/导演 (Director) - 姓名及其代表作
2. 编剧/剧本 (Writer/Scenario) - 姓名及其代表作
3. 作曲/音乐 (Composer/Music) - 姓名及其代表作
4. 制作人 (Producer) - 姓名及其代表作
5. 所属游戏系列
6. 值得关注的亮点（如：某知名制作人的新作、某经典系列续作等）

请用以下 JSON 格式返回，找不到的字段留空数组:
{{
    "directors": [{{"name": "姓名", "known_for": ["代表作1", "代表作2"]}}],
    "writers": [{{"name": "姓名", "known_for": ["代表作1"]}}],
    "composers": [{{"name": "姓名", "known_for": ["代表作1"]}}],
    "producers": [{{"name": "姓名", "known_for": ["代表作1"]}}],
    "series": "系列名称",
    "related_games": ["同制作人的其他作品"],
    "highlights": ["亮点1", "亮点2"]
}}

只返回 JSON，不要其他内容。如果完全找不到信息，返回空对象 {{}}。"""

    def fetch(self, game_name: str, basic_info: dict = None) -> Optional[GameDetails]:
        """获取游戏深度信息"""
        import requests
        
        prompt = self._build_prompt(game_name, basic_info)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个游戏行业专家，精通游戏制作人员信息。请基于你的知识回答问题，用 JSON 格式返回。"
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1500
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 解析 JSON
            # 处理可能的 markdown 代码块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            data = json.loads(content.strip())
            
            # 构建 GameDetails
            details = GameDetails(name=game_name)
            
            for d in data.get("directors", []):
                details.directors.append(GameCredit(
                    name=d.get("name", ""),
                    role="director",
                    known_for=d.get("known_for", [])
                ))
            
            for w in data.get("writers", []):
                details.writers.append(GameCredit(
                    name=w.get("name", ""),
                    role="writer",
                    known_for=w.get("known_for", [])
                ))
            
            for c in data.get("composers", []):
                details.composers.append(GameCredit(
                    name=c.get("name", ""),
                    role="composer",
                    known_for=c.get("known_for", [])
                ))
            
            for p in data.get("producers", []):
                details.producers.append(GameCredit(
                    name=p.get("name", ""),
                    role="producer",
                    known_for=p.get("known_for", [])
                ))
            
            details.series = data.get("series", "")
            details.related_games = data.get("related_games", [])
            details.highlights = data.get("highlights", [])
            
            return details
            
        except requests.RequestException as e:
            print(f"API 请求失败: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            return None
        except Exception as e:
            print(f"获取详情失败: {e}")
            return None


class DoubaoDetailFetcher(DetailFetcher):
    """使用豆包大模型 (火山方舟) 获取深度信息"""
    
    # 火山方舟默认 API 地址
    DEFAULT_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    
    def __init__(self, api_key: str, endpoint_id: str, base_url: str = None):
        """
        初始化豆包获取器
        
        Args:
            api_key: 火山方舟 API Key
            endpoint_id: 推理接入点 ID (如: ep-202xxxxx-xxxxx)
            base_url: 可选的自定义 API 地址
        """
        self.api_key = api_key
        self.endpoint_id = endpoint_id
        self.base_url = base_url or self.DEFAULT_BASE_URL
    
    def _build_prompt(self, game_name: str, basic_info: dict = None) -> str:
        """构建搜索提示"""
        context = ""
        if basic_info:
            if basic_info.get("developer"):
                context += f"开发商: {basic_info['developer']}\n"
            if basic_info.get("publisher"):
                context += f"发行商: {basic_info['publisher']}\n"
            if basic_info.get("release_date"):
                context += f"发售日期: {basic_info['release_date']}\n"
            # 如果有英文名，也加入上下文
            if basic_info.get("english_name") and basic_info.get("english_name") != game_name:
                context += f"英文名: {basic_info['english_name']}\n"
            if basic_info.get("chinese_name") and basic_info.get("chinese_name") != game_name:
                context += f"中文名: {basic_info['chinese_name']}\n"
        
        # 判断输入的是否是英文名（不包含中文字符）
        is_english = not any('\u4e00' <= char <= '\u9fff' for char in game_name)
        
        name_hint = ""
        if is_english:
            name_hint = f"\n注意：《{game_name}》是英文名，请先识别其对应的中文名（如有），然后基于你对该游戏的了解来回答。"
        
        return f"""请根据你的知识，整理游戏《{game_name}》的详细制作信息。{name_hint}

已知信息:
{context if context else "无"}

请提供以下信息（如果能找到）:
1. 监督/导演 (Director) - 姓名及其代表作
2. 编剧/剧本 (Writer/Scenario) - 姓名及其代表作
3. 作曲/音乐 (Composer/Music) - 姓名及其代表作
4. 制作人 (Producer) - 姓名及其代表作
5. 所属游戏系列
6. 值得关注的亮点（如：某知名制作人的新作、某经典系列续作等）

请用以下 JSON 格式返回，找不到的字段留空数组:
{{
    "directors": [{{"name": "姓名", "known_for": ["代表作1", "代表作2"]}}],
    "writers": [{{"name": "姓名", "known_for": ["代表作1"]}}],
    "composers": [{{"name": "姓名", "known_for": ["代表作1"]}}],
    "producers": [{{"name": "姓名", "known_for": ["代表作1"]}}],
    "series": "系列名称",
    "related_games": ["同制作人的其他作品"],
    "highlights": ["亮点1", "亮点2"]
}}

只返回 JSON，不要其他内容。如果完全找不到信息，返回空对象 {{}}。"""

    def fetch(self, game_name: str, basic_info: dict = None) -> Optional[GameDetails]:
        """获取游戏深度信息"""
        import requests
        
        prompt = self._build_prompt(game_name, basic_info)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.endpoint_id,  # 豆包使用 endpoint_id 作为 model
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个游戏行业专家，精通游戏制作人员信息。请基于你的知识回答问题，用 JSON 格式返回。"
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": 0.3,
            "max_tokens": 1500
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 解析 JSON
            # 处理可能的 markdown 代码块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            # 尝试找到 JSON 部分
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                content = content[start:end]
            
            data = json.loads(content.strip())
            
            # 构建 GameDetails
            details = GameDetails(name=game_name)
            
            for d in data.get("directors", []):
                if d.get("name"):
                    details.directors.append(GameCredit(
                        name=d.get("name", ""),
                        role="director",
                        known_for=d.get("known_for", [])
                    ))
            
            for w in data.get("writers", []):
                if w.get("name"):
                    details.writers.append(GameCredit(
                        name=w.get("name", ""),
                        role="writer",
                        known_for=w.get("known_for", [])
                    ))
            
            for c in data.get("composers", []):
                if c.get("name"):
                    details.composers.append(GameCredit(
                        name=c.get("name", ""),
                        role="composer",
                        known_for=c.get("known_for", [])
                    ))
            
            for p in data.get("producers", []):
                if p.get("name"):
                    details.producers.append(GameCredit(
                        name=p.get("name", ""),
                        role="producer",
                        known_for=p.get("known_for", [])
                    ))
            
            details.series = data.get("series", "")
            details.related_games = data.get("related_games", [])
            details.highlights = data.get("highlights", [])
            
            return details
            
        except requests.RequestException as e:
            print(f"API 请求失败: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应内容: {e.response.text}")
            return None
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            return None
        except Exception as e:
            print(f"获取详情失败: {e}")
            return None
    
    def translate_game_names(self, english_names: list[str]) -> dict[str, str]:
        """
        批量获取游戏的中文名
        
        Args:
            english_names: 英文游戏名列表
            
        Returns:
            {英文名: 中文名} 字典，找不到中文名的返回原英文名
        """
        import requests
        
        if not english_names:
            return {}
        
        # 分批处理，每批最多 5 个游戏，减少 LLM 混乱
        BATCH_SIZE = 5
        all_results = {}
        
        for batch_start in range(0, len(english_names), BATCH_SIZE):
            batch = english_names[batch_start:batch_start + BATCH_SIZE]
            batch_results = self._translate_batch(batch)
            all_results.update(batch_results)
        
        return all_results
    
    def _translate_batch(self, english_names: list[str]) -> dict[str, str]:
        """
        翻译一批游戏名（内部方法）
        
        要求 LLM 提供置信度，只采用高置信度的翻译
        """
        import requests
        
        if not english_names:
            return {}
        
        # 构建游戏列表（带序号）
        games_list = "\n".join(f"{i+1}. {name}" for i, name in enumerate(english_names))
        
        prompt = f"""我需要查找以下游戏的官方中文名。

游戏列表：
{games_list}

请逐个分析每个游戏，返回 JSON 数组。每个元素包含：
- "en": 原英文名（必须与上面完全一致，直接复制）
- "cn": 官方中文名
- "sure": 布尔值，true 表示你100%确定这是正确的官方译名，false 表示不确定

重要规则：
1. 只填写你100%确定的官方中文译名
2. 如果你不确定、没听说过这个游戏、或者这个游戏没有中文名，cn 填英文名，sure 填 false
3. 不要猜测，不要自己翻译，宁可保留英文名也不要填错误的中文名
4. Tales 系列是"传说"系列，不是"异闻录"；Bayonetta 是"猎天使魔女"

示例：
[
  {{"en": "The Legend of Zelda: Tears of the Kingdom", "cn": "塞尔达传说：王国之泪", "sure": true}},
  {{"en": "Some Unknown Indie Game", "cn": "Some Unknown Indie Game", "sure": false}}
]

只返回 JSON 数组。"""

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.endpoint_id,
            "messages": [
                {
                    "role": "system",
                    "content": "你是游戏翻译专家。只提供你100%确定的官方中文译名，不确定的保留英文名。绝对不要混淆不同的游戏系列。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 解析 JSON 数组
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            start = content.find("[")
            end = content.rfind("]") + 1
            if start != -1 and end > start:
                content = content[start:end]
            
            translations = json.loads(content.strip())
            
            if not isinstance(translations, list):
                return {name: name for name in english_names}
            
            # 构建结果，只采用高置信度的翻译
            result_dict = {name: name for name in english_names}
            
            for item in translations:
                if not isinstance(item, dict):
                    continue
                
                en_name = item.get("en", "")
                cn_name = item.get("cn", "")
                is_sure = item.get("sure", False)
                
                if not en_name or not cn_name:
                    continue
                
                # 只采用确定的翻译
                if not is_sure:
                    continue
                
                # 额外验证：中文名必须包含中文字符
                has_chinese = any('\u4e00' <= char <= '\u9fff' for char in cn_name)
                if not has_chinese:
                    continue
                
                # 匹配
                if en_name in result_dict:
                    result_dict[en_name] = cn_name
                else:
                    en_lower = en_name.lower().strip()
                    for orig_name in english_names:
                        if orig_name.lower().strip() == en_lower:
                            result_dict[orig_name] = cn_name
                            break
            
            return result_dict
            
        except Exception as e:
            print(f"翻译游戏名失败: {e}")
            return {name: name for name in english_names}


def create_fetcher_from_env() -> Optional[DetailFetcher]:
    """从环境变量创建深度信息获取器"""
    from dotenv import load_dotenv
    load_dotenv()
    
    # 优先使用豆包大模型 (火山方舟)
    ark_key = os.getenv("ARK_API_KEY")
    ark_endpoint = os.getenv("ARK_ENDPOINT_ID")
    ark_base = os.getenv("ARK_API_BASE")
    
    if ark_key and ark_endpoint:
        return DoubaoDetailFetcher(
            api_key=ark_key,
            endpoint_id=ark_endpoint,
            base_url=ark_base.rstrip("/") + "/chat/completions" if ark_base else None
        )
    
    # 备选：使用 OpenAI 兼容 API
    openai_key = os.getenv("OPENAI_API_KEY")
    openai_base = os.getenv("OPENAI_API_BASE")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    if openai_key:
        fetcher = OpenAIDetailFetcher(openai_key, model)
        
        if openai_base:
            fetcher.base_url = openai_base.rstrip("/") + "/chat/completions"
        
        return fetcher
    
    print("提示: 未配置 LLM API，深度信息功能不可用")
    print("请在 .env 文件中配置以下任一选项:")
    print("  1. 豆包大模型: ARK_API_KEY + ARK_ENDPOINT_ID (推荐，有免费额度)")
    print("  2. OpenAI: OPENAI_API_KEY")
    print("参考 .env.example 文件获取配置说明")
    return None


def translate_game_names(english_names: list[str]) -> dict[str, str]:
    """
    批量翻译游戏名（便捷函数）
    
    Args:
        english_names: 英文游戏名列表
        
    Returns:
        {英文名: 中文名} 字典
    """
    from dotenv import load_dotenv
    load_dotenv()
    
    ark_key = os.getenv("ARK_API_KEY")
    ark_endpoint = os.getenv("ARK_ENDPOINT_ID")
    ark_base = os.getenv("ARK_API_BASE")
    
    if ark_key and ark_endpoint:
        fetcher = DoubaoDetailFetcher(
            api_key=ark_key,
            endpoint_id=ark_endpoint,
            base_url=ark_base.rstrip("/") + "/chat/completions" if ark_base else None
        )
        return fetcher.translate_game_names(english_names)
    
    # 没有配置 API，返回原名
    return {name: name for name in english_names}
