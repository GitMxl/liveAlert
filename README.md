# liveAlert

一个本地桌面应用，用来统一管理主播、定时检测直播状态，并在主播开播时发送提醒。

项目基于 Python 标准库和 Tkinter 构建，默认不需要第三方依赖即可运行。

## 功能特性

- 添加、编辑、删除主播。
- 将主播列表、运行设置、提醒历史和状态日志保存到本地 JSON。
- 按定时器自动检测主播直播状态。
- 当主播从未开播变为直播中时触发提醒。
- 避免同一场直播重复提醒。
- 支持输入直播间 URL 或房间号。
- 支持为主播保存头像/封面图片路径或 URL。
- 支持按关键词搜索主播。
- 支持按平台、分组、收藏状态筛选。
- 支持导入、导出主播列表 JSON。
- 支持只检测当前选中的主播。
- 支持查看提醒历史和状态变化日志。
- 支持数据统计面板，展示平台、分组、提醒次数和近期直播记录。
- 支持每个主播单独设置检测间隔。
- 支持直播标题变化提醒。
- 支持查看选中主播的检测详情。
- 支持打开选中主播的弹幕面板。
- 支持在平台配置窗口中配置 Twitch 和 YouTube 的共享 API 凭据。
- 支持连续检测失败后的自动退避。
- 支持 Windows 系统托盘，关闭窗口后可继续后台监控。
- 支持 Windows 开机自启动。
- 提供平台适配器架构，便于继续扩展平台。

## 文档

- 产品需求：`docs/PRODUCT_REQUIREMENTS.md`
- 交互设计：`docs/INTERACTION_DESIGN.md`
- 前端设计：`docs/FRONTEND_DESIGN.md`

## 已支持平台适配器

- Generic HTTP：读取用户提供的 HTTP/JSON 状态接口。
- Bilibili：支持直播间 URL 或房间号，并支持读取近期弹幕。
- Douyu：支持直播间 URL 或房间号，并通过斗鱼公开弹幕服务读取直播弹幕。
- Huya：通过公开直播间页面检测状态，并支持原生弹幕连接和可选 HTTP 兜底。
- Twitch：配置凭据后支持官方 Helix API 检测和 IRC 聊天读取。
- YouTube：配置 API Key 后支持官方 Data API 检测和直播聊天读取。
- Douyin：支持保存直播间 URL 或房间号，并可从配置的 HTTP 端点读取弹幕。
- Kuaishou：保留平台入口。

保留平台可以保存房间 URL 或房间号，但真实状态检测仍需要官方 API、授权公开接口，或你自己的合规状态服务。

## 启动

```powershell
python run.py
```

如果 `python` 不可用：

```powershell
py run.py
```

## Bilibili 房间号

选择 `Bilibili`，然后输入房间号：

```text
123456
```

也可以输入直播间链接：

```text
https://live.bilibili.com/123456
```

应用会通过 Bilibili 适配器解析并查询直播间状态。公共接口可用时，`弹幕` 按钮可以查看近期直播弹幕。

## Douyu 房间号

选择 `Douyu`，然后输入房间号：

```text
475252
```

也可以输入直播间链接：

```text
https://www.douyu.com/475252
```

应用会通过 Douyu 适配器查询直播状态。`弹幕` 按钮会连接斗鱼公开弹幕服务并显示新收到的直播消息。

## Huya 和 Douyin 弹幕

Huya 弹幕会优先尝试公开直播页使用的原生 WebSocket/TARS 连接。如果失败，或者平台是 Douyin，可以在主播备注里添加合规的 HTTP/JSON 消息端点：

```text
danmaku_url=https://example.test/messages
```

端点返回格式可以和 `Generic HTTP` 相同：JSON 数组、包含 `danmaku`、`messages`、`comments` 或 `items` 的 JSON 对象，或者每行一条消息的纯文本。

## Twitch 配置

选择 `Twitch`，输入频道名或链接，然后通过环境变量配置官方 API 凭据：

```text
TWITCH_CLIENT_ID=...
TWITCH_APP_TOKEN=...
TWITCH_CHAT_NICK=...
TWITCH_CHAT_OAUTH=oauth:...
```

也可以在 `平台配置` 窗口中填写：

```text
Twitch Client ID=...
Twitch App Token=...
Twitch Chat Nick=...
Twitch Chat OAuth=...
```

仍然支持在单个主播备注中覆盖配置：

```text
client_id=...
app_token=...
chat_nick=...
chat_oauth=oauth:...
```

Twitch 聊天使用官方 IRC 接口。聊天 OAuth Token 必须属于一个 Twitch 用户，并包含读取聊天的权限。

## YouTube 配置

选择 `YouTube`，输入视频链接，或者在备注中添加 `channel_id=...`。官方 Data API Key 可以通过环境变量配置：

```text
YOUTUBE_API_KEY=...
```

也可以在 `平台配置` 中填写：

```text
YouTube API Key=...
```

仍然支持在单个主播备注中覆盖配置：

```text
api_key=...
channel_id=...
live_chat_id=...
```

`弹幕` 按钮会使用 YouTube Data API 的直播聊天接口。它可以从直播视频 URL、`video_id=...`、`channel_id=...` 或直接的 `live_chat_id=...` 中解析当前直播聊天。

## 分组、收藏、搜索和历史

- 使用 `分组` 管理主播，例如 `游戏`、`音乐` 或 `活动`。
- 开启 `收藏` 后，可以更快筛选重要主播。
- 使用 `头像 / 封面` 字段保存本地图片路径或远程图片 URL。Tkinter 支持的本地图片格式，例如 PNG 或 GIF，可以在详情区域预览。
- 监测列表搜索框可以搜索主播名、平台、分组、直播间、备注、直播标题或最近错误。
- 监测列表会显示适配器返回的最新直播标题。
- 使用 `检测选中` 只检测当前选中的主播。
- 使用 `提醒历史` 查看并打开过去的开播提醒。
- 使用 `状态日志` 查看状态变化和标题变化。
- 使用单主播检测间隔字段，为某些主播降低检测频率。
- 选中主播后，详情行会展示失败次数、退避时间、下次检测时间和直播场次 ID。
- 使用 `导出主播` 将主播列表保存为 JSON 文件。
- 使用 `导入主播` 合并 JSON 文件中的主播。相同平台和直播间地址的主播会被跳过。

## 数据统计

打开 `数据统计` 页签，可以查看基于本地主播、提醒历史和状态日志生成的统计面板：

- 主播总数、监测中数量、当前直播中数量、提醒次数、开播记录数、近 7 天开播次数。
- 平台分布：每个平台的总数、直播中数量、监测中数量。
- 分组分布：每个分组的总数、直播中数量、监测中数量。
- 提醒排行：按主播统计提醒次数，并显示最近提醒时间。

统计面板会随监测列表刷新，也可以手动点击 `刷新统计`。

## Windows 托盘和开机自启动

`运行设置` 页签提供桌面集成功能：

- 开启 `关闭时最小化到托盘` 后，关闭主窗口时应用会隐藏到系统托盘并继续监控。托盘菜单可以恢复主窗口、立即检测或退出应用。
- 开启 `开机自启动` 后，应用会在当前用户的 Windows 启动注册表项中写入 `liveAlert`。

这些功能使用 Python 标准库调用 Windows API。非 Windows 系统仍可正常运行应用，但托盘和开机自启动不可用。

## Generic HTTP 适配器

选择 `Generic HTTP`，然后输入一个 HTTP/HTTPS 状态接口。适配器可以识别如下 JSON：

```json
{
  "live": true,
  "title": "Live now",
  "live_id": "2026-07-05-001"
}
```

也支持：

```json
{
  "status": "live"
}
```

对于文本响应，可以在备注里添加关键词规则：

```text
live_keyword=LIVE
offline_keyword=OFFLINE
```

对于弹幕，可以在备注中添加可选消息端点：

```text
danmaku_url=https://example.test/messages
```

端点可以返回 JSON 数组，也可以返回包含 `danmaku`、`messages`、`comments` 或 `items` 的 JSON 对象。消息对象可使用 `author`、`nickname`、`content`、`text`、`id`、`message_id`、`time` 或 `timestamp` 等字段。也支持纯文本响应，每行一条消息。

## 项目结构

```text
.
|-- docs/
|   |-- PRODUCT_REQUIREMENTS.md
|   |-- INTERACTION_DESIGN.md
|   `-- FRONTEND_DESIGN.md
|-- run.py
|-- src/
|   `-- live_monitor/
|       |-- adapters/
|       |-- autostart.py
|       |-- main.py
|       |-- models.py
|       |-- monitor.py
|       |-- notifier.py
|       |-- storage.py
|       |-- tray.py
|       `-- ui.py
`-- tests/
```

## 合规说明

本应用不保存平台账号密码，不绕过登录，不破解 API，也不规避平台访问限制。真实平台集成应使用官方 API、授权公开接口，或你自己的合规服务。

本项目仅用于学习和交流编程技术，请勿用于商业目的。如有任何商业行为，均与本项目无关。

如果本项目存在侵犯您合法权益的情况，请及时联系开发者，开发者将及时删除相关内容。


## 声明

本项目的所有功能都是基于互联网上公开的资料开发，无任何破解、逆向工程等行为。

本项目仅用于学习交流编程技术，严禁将本项目用于商业目的。如有任何商业行为，均与本项目无关。

如果本项目存在侵犯您的合法权益的情况，请及时与开发者联系，开发者将会及时删除有关内容。
