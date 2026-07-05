# liveAlert

A local desktop app for monitoring streamers and sending live-start reminders.

The app is built with Python standard library and Tkinter, so it can run without third-party dependencies.

## 声明

本项目的所有功能都是基于互联网上公开的资料开发，无任何破解、逆向工程等行为。

本项目仅用于学习交流编程技术，严禁将本项目用于商业目的。如有任何商业行为，均与本项目无关。

如果本项目存在侵犯您的合法权益的情况，请及时与开发者联系，开发者将会及时删除有关内容。

## Features

- Add, edit, and delete streamers.
- Save streamers and settings to local JSON.
- Monitor streamers on a timer.
- Trigger a reminder when a streamer changes from offline to live.
- Avoid repeated reminders for the same live session.
- Support room URL or room ID input.
- Search streamers by keyword.
- Filter streamers by platform, group, and favorite status.
- Check one selected streamer without checking the whole list.
- Save reminder history locally.
- Save status-change logs locally.
- Set a custom check interval per streamer.
- Send optional reminders when a live title changes.
- Show a detection detail panel for the selected streamer.
- Open a danmaku panel for the selected streamer.
- Configure shared Twitch and YouTube API credentials in a platform config window.
- Back off automatically after repeated check failures.
- Provide a platform adapter architecture for future integrations.

## Docs

- Product requirements: `docs/PRODUCT_REQUIREMENTS.md`
- Interaction design: `docs/INTERACTION_DESIGN.md`
- Frontend design: `docs/FRONTEND_DESIGN.md`

## Supported Adapters

- Mock: local testing adapter.
- Generic HTTP: reads a user-provided HTTP/JSON status endpoint.
- Bilibili: supports live room URL or room ID, plus recent live danmaku.
- Douyu: supports live room URL or room ID.
- Huya: supports live room URL or room ID through public room page detection.
- Twitch: supports official Helix API checks and IRC chat when credentials are configured.
- YouTube: supports official Data API checks and live chat messages when an API key is configured.
- Douyin, Kuaishou: reserved platform entries.

Reserved platforms can save room URLs or room IDs, but real status checks still need official APIs, authorized public interfaces, or your own compliant status service.

## Start

```powershell
python run.py
```

If `python` is unavailable:

```powershell
py run.py
```

## Bilibili Room ID

Choose `Bilibili`, then enter either:

```text
123456
```

or:

```text
https://live.bilibili.com/123456
```

The app will resolve and query the room status through the Bilibili adapter.
The `Danmaku` button shows recent room danmaku when the public room endpoint is available.

## Douyu Room ID

Choose `Douyu`, then enter either:

```text
475252
```

or:

```text
https://www.douyu.com/475252
```

The app will query the room status through the Douyu adapter.

## Twitch Setup

Choose `Twitch`, enter a channel name or URL, then configure official API credentials either as environment variables:

```text
TWITCH_CLIENT_ID=...
TWITCH_APP_TOKEN=...
TWITCH_CHAT_NICK=...
TWITCH_CHAT_OAUTH=oauth:...
```

or in `Platform Config`:

```text
Twitch Client ID=...
Twitch App Token=...
Twitch Chat Nick=...
Twitch Chat OAuth=...
```

Per-streamer remark values still work:

```text
client_id=...
app_token=...
chat_nick=...
chat_oauth=oauth:...
```

Twitch chat uses the official IRC interface. The chat OAuth token must belong to
a Twitch user and include chat read permission.

## YouTube Setup

Choose `YouTube`, enter a video URL, or add `channel_id=...` in the remark field. Configure the official Data API key either as:

```text
YOUTUBE_API_KEY=...
```

or in `Platform Config`:

```text
YouTube API Key=...
```

Per-streamer remark values still work:

```text
api_key=...
channel_id=...
live_chat_id=...
```

The `Danmaku` button uses the YouTube Data API live chat endpoint. It can resolve
the active live chat from a live video URL, `video_id=...`, `channel_id=...`, or a
direct `live_chat_id=...` remark.

## Groups, Favorites, Search, and History

- Use `Group` to organize streamers, such as `Games`, `Music`, or `Events`.
- Enable `Favorite` to make an important streamer easier to filter.
- Use the monitor table search box to search streamer name, platform, group, room URL, remark, live title, or last error.
- The monitor table shows the latest live title when an adapter provides one.
- Use `Check Selected` to check only the selected streamer.
- Use `Reminder History` to view and open past live-start reminders.
- Use `Status Log` to view status changes and title changes.
- Use the per-streamer interval field to slow down checks for specific streamers.
- Use the selected-streamer detail line to inspect failures, backoff, next check time, and live session ID.

## Mock Examples

Choose `Mock`, then enter:

- `mock://live`: always live.
- `mock://offline`: always offline.
- `mock://toggle?period=60`: live for half the period, offline for the other half.
- `mock://fail`: simulate a check failure.

The `Danmaku` button can display generated Mock messages for `mock://live` and
the live half of `mock://toggle?period=60`.

## Generic HTTP Adapter

Choose `Generic HTTP`, then enter an HTTP/HTTPS endpoint. The adapter recognizes JSON such as:

```json
{
  "live": true,
  "title": "Live now",
  "live_id": "2026-07-05-001"
}
```

It also supports:

```json
{
  "status": "live"
}
```

For text responses, add keyword rules in the remark field:

```text
live_keyword=LIVE
offline_keyword=OFFLINE
```

For danmaku, add an optional message endpoint in the remark field:

```text
danmaku_url=https://example.test/messages
```

The endpoint may return a JSON array, or a JSON object with `danmaku`,
`messages`, `comments`, or `items`. Message objects can use fields such as
`author`, `nickname`, `content`, `text`, `id`, `message_id`, `time`, or
`timestamp`. Plain text responses are also supported, one message per line.

## Project Structure

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
|       |-- main.py
|       |-- models.py
|       |-- monitor.py
|       |-- notifier.py
|       |-- storage.py
|       `-- ui.py
`-- tests/
```

## Compliance Notes

The app does not store platform account passwords, bypass login, crack APIs, or evade platform restrictions. Real platform integrations should use official APIs, authorized public interfaces, or your own compliant service.



