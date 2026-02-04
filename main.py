#!/usr/bin/env python3
"""
VGame Horizon - Switch 新游时间线
MVP 版本：命令行界面
"""

import argparse
from datetime import datetime, timezone
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, IntPrompt
from rich import box

from igdb_client import create_client_from_env, IGDBClient
from detail_fetcher import create_fetcher_from_env, GameDetails, translate_game_names


console = Console()


def format_date(timestamp: Optional[int]) -> str:
    """格式化 Unix 时间戳为日期字符串"""
    if not timestamp:
        return "TBA"
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d")


def format_date_short(timestamp: Optional[int]) -> str:
    """格式化为短日期（仅日）"""
    if not timestamp:
        return "TBA"
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.strftime("%m/%d")


def get_companies(game: dict, role: str = "developer") -> str:
    """
    获取公司名称
    
    Args:
        game: 游戏数据
        role: "developer" 或 "publisher"
        
    Returns:
        公司名称，多个用逗号分隔
    """
    involved = game.get("involved_companies", [])
    if not involved:
        return "-"
    
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
    
    return ", ".join(companies) if companies else "-"


def get_genres(game: dict) -> str:
    """获取游戏类型"""
    genres = game.get("genres", [])
    if not genres:
        return "-"
    return ", ".join(g.get("name", "") for g in genres if isinstance(g, dict))


def truncate_text(text: str, max_length: int = 80) -> str:
    """截断文本"""
    if not text:
        return "-"
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def get_chinese_name(game: dict) -> Optional[str]:
    """
    获取游戏的中文名
    
    优先级：
    1. 通过 LLM 翻译后添加的 _cn_name 字段
    2. IGDB 的 alternative_names 中的中文名
    
    Args:
        game: 游戏数据
        
    Returns:
        中文名，如果没有则返回 None
    """
    # 优先使用 LLM 翻译的结果
    if game.get("_cn_name"):
        cn_name = game["_cn_name"]
        # 如果中文名和英文名不同，才返回
        if cn_name != game.get("name"):
            return cn_name
    
    # 备用：从 IGDB 的 alternative_names 中提取
    alt_names = game.get("alternative_names", [])
    if not alt_names:
        return None
    
    for alt in alt_names:
        if not isinstance(alt, dict):
            continue
        
        name = alt.get("name", "")
        comment = alt.get("comment", "").lower() if alt.get("comment") else ""
        
        # 检查是否是中文名（通过 comment 标注或包含中文字符）
        if "chinese" in comment or "中文" in comment or "简体" in comment or "繁体" in comment:
            return name
        
        # 检查名称本身是否包含中文字符
        if any('\u4e00' <= char <= '\u9fff' for char in name):
            return name
    
    return None


def get_display_name(game: dict) -> tuple[str, Optional[str]]:
    """
    获取游戏的显示名称
    
    Args:
        game: 游戏数据
        
    Returns:
        (英文名, 中文名) - 中文名可能为 None
    """
    en_name = game.get("name", "Unknown")
    cn_name = get_chinese_name(game)
    return en_name, cn_name


def format_game_name(game: dict, show_both: bool = True) -> str:
    """
    格式化游戏名称（同时显示中英文）
    
    Args:
        game: 游戏数据
        show_both: 是否同时显示中英文
        
    Returns:
        格式化后的名称
    """
    en_name, cn_name = get_display_name(game)
    
    if cn_name and show_both:
        return f"{cn_name} ({en_name})"
    elif cn_name:
        return cn_name
    else:
        return en_name


def enrich_games_with_chinese_names(games: list) -> list:
    """
    通过 LLM 批量获取游戏中文名，并添加到游戏数据中
    
    Args:
        games: 游戏列表
        
    Returns:
        添加了 _cn_name 字段的游戏列表
    """
    if not games:
        return games
    
    # 提取所有英文名
    english_names = [game.get("name", "") for game in games if game.get("name")]
    
    if not english_names:
        return games
    
    console.print("[dim]正在获取游戏中文名...[/dim]")
    
    # 批量翻译
    translations = translate_game_names(english_names)
    
    # 添加中文名到游戏数据
    for game in games:
        en_name = game.get("name", "")
        if en_name in translations:
            game["_cn_name"] = translations[en_name]
    
    return games


def display_game_details(details: GameDetails):
    """
    展示游戏深度信息
    
    Args:
        details: 游戏详情数据
    """
    console.print()
    console.print(Panel(
        f"🔍 {details.name} - 深度信息",
        style="bold magenta",
        box=box.DOUBLE
    ))
    console.print()
    
    # 制作人员
    has_credits = False
    
    if details.directors:
        has_credits = True
        console.print("[bold cyan]🎬 监督/导演[/bold cyan]")
        for credit in details.directors:
            known_for = ", ".join(credit.known_for) if credit.known_for else "暂无"
            console.print(f"   • {credit.name}")
            console.print(f"     [dim]代表作: {known_for}[/dim]")
        console.print()
    
    if details.writers:
        has_credits = True
        console.print("[bold cyan]✍️  编剧/剧本[/bold cyan]")
        for credit in details.writers:
            known_for = ", ".join(credit.known_for) if credit.known_for else "暂无"
            console.print(f"   • {credit.name}")
            console.print(f"     [dim]代表作: {known_for}[/dim]")
        console.print()
    
    if details.composers:
        has_credits = True
        console.print("[bold cyan]🎵 作曲/音乐[/bold cyan]")
        for credit in details.composers:
            known_for = ", ".join(credit.known_for) if credit.known_for else "暂无"
            console.print(f"   • {credit.name}")
            console.print(f"     [dim]代表作: {known_for}[/dim]")
        console.print()
    
    if details.producers:
        has_credits = True
        console.print("[bold cyan]🎯 制作人[/bold cyan]")
        for credit in details.producers:
            known_for = ", ".join(credit.known_for) if credit.known_for else "暂无"
            console.print(f"   • {credit.name}")
            console.print(f"     [dim]代表作: {known_for}[/dim]")
        console.print()
    
    # 系列信息
    if details.series:
        console.print(f"[bold cyan]📚 所属系列[/bold cyan]")
        console.print(f"   {details.series}")
        console.print()
    
    # 关联作品
    if details.related_games:
        console.print("[bold cyan]🔗 关联作品[/bold cyan]")
        for game in details.related_games:
            console.print(f"   • {game}")
        console.print()
    
    # 亮点
    if details.highlights:
        console.print("[bold cyan]⭐ 值得关注[/bold cyan]")
        for highlight in details.highlights:
            console.print(f"   • {highlight}")
        console.print()
    
    if not has_credits and not details.series and not details.highlights:
        console.print("[yellow]暂未找到该游戏的详细制作信息[/yellow]")
        console.print()


def display_timeline(games: list, year: int, month: int):
    """
    以时间线形式展示游戏列表
    
    Args:
        games: 游戏列表
        year: 年份
        month: 月份
    """
    if not games:
        console.print(f"[yellow]📭 {year}年{month}月 暂无 Switch 新游数据[/yellow]")
        return
    
    # 标题
    title = f"🎮 {year}年{month}月 Switch 新游时间线"
    console.print(Panel(title, style="bold cyan", box=box.DOUBLE))
    console.print()
    
    # 按日期分组
    games_by_date = {}
    for game in games:
        date_str = format_date(game.get("first_release_date"))
        if date_str not in games_by_date:
            games_by_date[date_str] = []
        games_by_date[date_str].append(game)
    
    # 按日期排序展示
    for date_str in sorted(games_by_date.keys()):
        date_games = games_by_date[date_str]
        
        # 日期标签
        console.print(f"[bold green]📅 {date_str}[/bold green]")
        console.print("─" * 60)
        
        for game in date_games:
            name = game.get("name", "Unknown")
            developer = get_companies(game, "developer")
            publisher = get_companies(game, "publisher")
            genres = get_genres(game)
            summary = truncate_text(game.get("summary", ""), 100)
            
            # 游戏名称
            console.print(f"  [bold white]🎯 {name}[/bold white]")
            
            # 详细信息
            console.print(f"     [dim]开发商:[/dim] {developer}")
            console.print(f"     [dim]发行商:[/dim] {publisher}")
            console.print(f"     [dim]类型:[/dim] {genres}")
            if summary != "-":
                console.print(f"     [dim]简介:[/dim] {summary}")
            console.print()
        
        console.print()


def display_table(games: list, year: int, month: int):
    """
    以表格形式展示游戏列表
    
    Args:
        games: 游戏列表
        year: 年份
        month: 月份
    """
    if not games:
        console.print(f"[yellow]📭 {year}年{month}月 暂无 Switch 新游数据[/yellow]")
        return
    
    table = Table(
        title=f"🎮 {year}年{month}月 Switch 新游列表",
        box=box.ROUNDED,
        header_style="bold cyan",
        show_lines=True
    )
    
    table.add_column("日期", style="green", width=10)
    table.add_column("游戏名称", style="bold white", width=30)
    table.add_column("开发商", style="yellow", width=20)
    table.add_column("类型", style="magenta", width=15)
    table.add_column("简介", style="dim", width=40)
    
    for game in games:
        table.add_row(
            format_date_short(game.get("first_release_date")),
            game.get("name", "Unknown"),
            get_companies(game, "developer"),
            get_genres(game),
            truncate_text(game.get("summary", ""), 60)
        )
    
    console.print(table)
    console.print(f"\n[dim]共 {len(games)} 款游戏[/dim]")


def display_compact(games: list, year: int, month: int, show_index: bool = False):
    """
    紧凑模式展示
    
    Args:
        games: 游戏列表
        year: 年份
        month: 月份
        show_index: 是否显示序号
    """
    if not games:
        console.print(f"[yellow]📭 {year}年{month}月 暂无 Switch 新游数据[/yellow]")
        return
    
    console.print(Panel(
        f"🎮 {year}年{month}月 Switch 新游 ({len(games)}款)",
        style="bold cyan"
    ))
    console.print()
    
    for idx, game in enumerate(games, 1):
        date = format_date_short(game.get("first_release_date"))
        en_name, cn_name = get_display_name(game)
        developer = get_companies(game, "developer")
        
        # 构建名称显示：有中文名则显示 "中文名 (英文名)"
        if cn_name:
            name_display = f"{cn_name} [dim]({en_name})[/dim]"
        else:
            name_display = en_name
        
        if show_index:
            console.print(f"[cyan]{idx:2}.[/cyan] [green]{date}[/green] | [bold]{name_display}[/bold] [dim]- {developer}[/dim]")
        else:
            console.print(f"[green]{date}[/green] | [bold]{name_display}[/bold] [dim]- {developer}[/dim]")
    
    console.print()


def interactive_mode(games: list, year: int, month: int):
    """
    交互式模式：查看列表并选择游戏获取深度信息
    
    Args:
        games: 游戏列表
        year: 年份
        month: 月份
    """
    if not games:
        console.print(f"[yellow]📭 {year}年{month}月 暂无 Switch 新游数据[/yellow]")
        return
    
    # 初始化深度信息获取器
    fetcher = create_fetcher_from_env()
    
    while True:
        console.clear()
        
        # 显示带序号的列表
        display_compact(games, year, month, show_index=True)
        
        console.print("[dim]─" * 50 + "[/dim]")
        console.print("[bold]操作说明:[/bold]")
        console.print("  • 输入 [cyan]序号[/cyan] 查看游戏深度信息（制作人、编剧、作曲等）")
        console.print("  • 输入 [cyan]q[/cyan] 退出交互模式")
        console.print()
        
        # 获取用户输入
        choice = Prompt.ask("请选择", default="q")
        
        if choice.lower() == "q":
            console.print("[dim]退出交互模式[/dim]")
            break
        
        try:
            idx = int(choice)
            if 1 <= idx <= len(games):
                game = games[idx - 1]
                en_name, cn_name = get_display_name(game)
                
                # 优先使用中文名进行查询，没有则用英文名
                search_name = cn_name if cn_name else en_name
                display_name = f"{cn_name} ({en_name})" if cn_name else en_name
                
                if not fetcher:
                    console.print()
                    console.print("[yellow]⚠️  深度信息功能需要配置 LLM API[/yellow]")
                    console.print("[dim]在 .env 文件中配置 ARK_API_KEY + ARK_ENDPOINT_ID 以启用此功能[/dim]")
                    console.print()
                    Prompt.ask("按回车键继续")
                    continue
                
                console.print()
                console.print(f"[dim]正在获取《{display_name}》的深度信息...[/dim]")
                
                # 构建基础信息，包含中英文名
                basic_info = {
                    "developer": get_companies(game, "developer"),
                    "publisher": get_companies(game, "publisher"),
                    "release_date": format_date(game.get("first_release_date")),
                    "english_name": en_name,
                    "chinese_name": cn_name
                }
                
                # 获取深度信息（使用中文名查询效果更好）
                details = fetcher.fetch(search_name, basic_info)
                
                if details:
                    display_game_details(details)
                else:
                    console.print("[yellow]未能获取深度信息，请稍后重试[/yellow]")
                
                console.print()
                Prompt.ask("按回车键继续")
            else:
                console.print(f"[red]请输入 1-{len(games)} 之间的数字[/red]")
                Prompt.ask("按回车键继续")
        except ValueError:
            console.print("[red]请输入有效的数字或 q[/red]")
            Prompt.ask("按回车键继续")


def fetch_single_game_detail(game_name: str):
    """
    获取单个游戏的深度信息
    
    Args:
        game_name: 游戏名称
    """
    fetcher = create_fetcher_from_env()
    
    if not fetcher:
        return
    
    console.print(f"[dim]正在获取《{game_name}》的深度信息...[/dim]")
    
    details = fetcher.fetch(game_name)
    
    if details:
        display_game_details(details)
    else:
        console.print("[yellow]未能获取深度信息，请稍后重试[/yellow]")


def main():
    parser = argparse.ArgumentParser(
        description="VGame Horizon - Switch 新游时间线",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py                        # 显示当月新游
  python main.py -m 3                   # 显示3月新游
  python main.py -y 2026 -m 2           # 显示2026年2月新游
  python main.py --format table         # 表格模式
  python main.py --format compact       # 紧凑模式
  python main.py -i                     # 交互模式（可查看深度信息）
  python main.py --detail "塞尔达传说"   # 直接查询游戏深度信息
        """
    )
    
    now = datetime.now()
    
    parser.add_argument(
        "-y", "--year",
        type=int,
        default=now.year,
        help=f"年份 (默认: {now.year})"
    )
    parser.add_argument(
        "-m", "--month",
        type=int,
        default=now.month,
        help=f"月份 (默认: {now.month})"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["timeline", "table", "compact"],
        default="timeline",
        help="显示格式 (默认: timeline)"
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=50,
        help="最大显示数量 (默认: 50)"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="交互模式：可选择游戏查看深度信息"
    )
    parser.add_argument(
        "-d", "--detail",
        type=str,
        help="直接查询指定游戏的深度信息"
    )
    
    args = parser.parse_args()
    
    # 直接查询深度信息模式
    if args.detail:
        fetch_single_game_detail(args.detail)
        return
    
    # 验证月份
    if not 1 <= args.month <= 12:
        console.print("[red]错误: 月份必须在 1-12 之间[/red]")
        return
    
    # 创建客户端
    console.print("[dim]正在连接 IGDB API...[/dim]")
    client = create_client_from_env()
    
    if not client:
        return
    
    # 获取数据
    console.print(f"[dim]正在获取 {args.year}年{args.month}月 Switch 新游数据...[/dim]")
    games = client.get_upcoming_games(
        platform_id=IGDBClient.PLATFORM_SWITCH,
        year=args.year,
        month=args.month,
        limit=args.limit
    )
    
    # 通过 LLM 获取中文名
    if games:
        games = enrich_games_with_chinese_names(games)
    
    console.print()
    
    # 交互模式
    if args.interactive:
        interactive_mode(games, args.year, args.month)
        return
    
    # 显示结果
    if args.format == "timeline":
        display_timeline(games, args.year, args.month)
    elif args.format == "table":
        display_table(games, args.year, args.month)
    else:
        display_compact(games, args.year, args.month)


if __name__ == "__main__":
    main()
