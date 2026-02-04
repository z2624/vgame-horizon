# VGame Horizon 🎮

Switch 新游时间线工具 - 快速查看指定月份即将登陆 Nintendo Switch 的游戏。

## 功能

- 📅 按月份查看即将发售的 Switch 游戏
- 🏢 显示开发商、发行商信息
- 🎯 显示游戏类型和简介
- 📊 支持多种显示格式（时间线/表格/紧凑）

## 快速开始

### 1. 获取 API 凭证

1. 访问 [Twitch 开发者控制台](https://dev.twitch.tv/console)
2. 登录或创建 Twitch 账号
3. 点击 "注册应用程序"
4. 填写信息：
   - 名称：随意（如 "VGame Horizon"）
   - OAuth 重定向 URL：`http://localhost`
   - 分类：选择 "Application Integration"
5. 创建后，点击 "管理" 获取 Client ID 和 Client Secret

### 2. 配置环境

```bash
# 克隆/进入项目目录
cd vgame_horizon

# 安装依赖
pip install -r requirements.txt

# 配置 API 凭证
cp .env.example .env
# 编辑 .env 文件，填入你的 Client ID 和 Client Secret
```

### 3. 运行

```bash
# 查看当月 Switch 新游
python main.py

# 查看指定月份
python main.py -y 2026 -m 2

# 表格模式
python main.py --format table

# 紧凑模式
python main.py --format compact
```

## 使用示例

```bash
# 显示 2026 年 2 月新游（时间线格式）
python main.py -y 2026 -m 2

# 显示 3 月新游（表格格式）
python main.py -m 3 -f table

# 显示更多游戏（最多100款）
python main.py -l 100

# 交互模式 - 选择游戏查看深度信息（制作人、编剧、作曲等）
python main.py -i

# 直接查询某游戏的深度信息
python main.py -d "塞尔达传说"
python main.py --detail "Elden Ring"
```

## 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-y, --year` | 年份 | 当前年份 |
| `-m, --month` | 月份 | 当前月份 |
| `-f, --format` | 显示格式 (timeline/table/compact) | timeline |
| `-l, --limit` | 最大显示数量 | 50 |
| `-i, --interactive` | 交互模式，可选择游戏查看深度信息 | - |
| `-d, --detail` | 直接查询指定游戏的深度信息 | - |

## 显示格式

### Timeline（时间线）
按日期分组，详细显示每款游戏信息，适合仔细浏览。

### Table（表格）
表格形式展示，适合快速对比。

### Compact（紧凑）
单行显示，适合快速扫描。

### Interactive（交互）
带序号的列表，可选择游戏查看深度信息。

## 深度信息功能

通过配置 LLM API，可以获取游戏的深度信息：

- 🎬 **监督/导演** - 姓名及代表作
- ✍️ **编剧/剧本** - 姓名及代表作
- 🎵 **作曲/音乐** - 姓名及代表作
- 🎯 **制作人** - 姓名及代表作
- 📚 **所属系列**
- ⭐ **值得关注的亮点**

### 配置豆包大模型（推荐，有免费额度）

1. 访问 [火山方舟控制台](https://console.volcengine.com/ark)
2. 开通服务，创建 API Key
3. 创建推理接入点，选择模型（如 Doubao-lite-32k）
4. 在 `.env` 中配置：

```bash
ARK_API_KEY=your_api_key
ARK_ENDPOINT_ID=ep-202xxxxx-xxxxx
```

### 备选：配置 OpenAI API

```bash
OPENAI_API_KEY=sk-xxxxx
```

## 数据来源

数据来自 [IGDB](https://www.igdb.com/)（Internet Game Database），由 Twitch 维护的社区驱动游戏数据库。

## 后续计划

- [ ] Web 界面
- [ ] 游戏详情页（制作人、编剧、作曲等深度信息）
- [ ] 收藏/关注功能
- [ ] 多平台支持（PS5、Xbox、PC）
- [ ] 制作人关联作品查询

## License

MIT
