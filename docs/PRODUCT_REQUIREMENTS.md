# Product Requirements: Streamer Live Monitor

## 1. Background

Users often follow streamers across multiple platforms. Platform-native live notifications are inconsistent, and users can miss live sessions. This desktop app provides one local place to manage streamers, monitor live status, and send reminders.

## 2. Goals

- Manage multiple streamers in one local desktop app.
- Check live status on a configurable interval.
- Send a reminder when a streamer starts live.
- Support room URL and room ID input.
- Support search, grouping, favorites, and reminder history.
- Support single-streamer manual checks.
- Apply failure retry backoff.
- Support status-change logs, per-streamer check intervals, live-title change reminders, detection details, and shared platform credentials.
- Keep the platform adapter architecture easy to extend.

Related design docs:

- Interaction design: `docs/INTERACTION_DESIGN.md`
- Frontend design: `docs/FRONTEND_DESIGN.md`

## 3. Users

- Viewers who follow multiple streamers.
- Users who want reliable live-start reminders.
- Users who want a cross-platform local monitor.

## 4. Core Workflow

1. User adds a streamer with streamer name, platform, and room URL or room ID.
2. App periodically checks enabled streamers.
3. When a streamer changes from offline to live, app shows a reminder.
4. User can open the live room from the app.
5. User can enable or disable monitoring and reminders per streamer.

## 5. Functional Requirements

### 5.1 Streamer Management

Each streamer includes:

- Streamer name
- Platform
- Room URL or room ID
- Group
- Favorite flag
- Remark
- Monitoring enabled
- Reminder enabled
- Custom check interval, optional
- Current status
- Live title
- Last check time
- Last error
- Current live session ID
- Last notified live session ID

### 5.2 Status Monitoring

Status values:

- Unknown
- Offline
- Live
- Check failed

Rules:

- Only enabled streamers are checked.
- One failed platform check must not stop other checks.
- Network requests must use timeouts.
- Manual check is supported.
- Manual selected-streamer check is supported.
- Repeated failures should use configurable backoff to reduce request pressure.
- A streamer can override the global check interval with its own custom interval.
- The selected streamer should expose detection details including failure count, next check time, live session ID, and latest error.

### 5.3 Reminder Rules

A reminder is triggered when:

- The current status is live.
- The streamer has reminder enabled.
- Global notifications are enabled.
- The current live session has not been notified before.

Duplicate prevention:

- One live session should trigger at most one reminder.
- If the platform provides a live ID, use it.
- Otherwise generate a local live session ID when the status changes to live.

Title-change reminders:

- If a streamer is already live and the live title changes, the app can send a title-change reminder.
- Title-change reminders follow global notification, streamer reminder, and title-change setting switches.
- Title changes are recorded in status logs.

### 5.4 Settings

User can configure:

- Check interval, default 60 seconds.
- Notification enabled, default on.
- Sound enabled, default on.
- Retry backoff enabled, default on.
- Title-change notification enabled, default on.
- Shared platform credentials for adapters that need official API access.

### 5.5 Platform Adapters

Unified interface:

```python
check_live_status(streamer) -> LiveStatusResult
```

Current adapters:

- Mock: local testing adapter.
- Generic HTTP: reads a user-provided HTTP/JSON status endpoint.
- Bilibili: supports room URL and room ID.
- Douyu: supports room URL and room ID.
- Huya: supports room URL and room ID through public room page detection.
- Twitch: supports official Helix API checks when credentials are configured.
- YouTube: supports official Data API checks when an API key is configured.
- Douyin, Kuaishou: reserved entries.

Reserved entries can save room URLs or room IDs, but real checks require official APIs, authorized public interfaces, or a compliant user-owned status service.

Platform configuration:

- Twitch can use shared `client_id` and `app_token` values.
- YouTube can use a shared `api_key` value.
- Per-streamer remark configuration remains supported for overrides.

### 5.6 Logs

- App records status changes, including live, offline, error, and recovery transitions.
- App records live-title changes.
- Logs include streamer name, platform, old status, new status, old title, new title, room URL, and timestamp.
- Logs can be viewed and cleared from the UI.

## 6. Non-Functional Requirements

- Local JSON persistence.
- No account password storage.
- No bypassing login or access control.
- No API cracking or anti-bot evasion.
- Stable background monitoring thread.
- Clear error handling.

## 7. MVP Scope

Included:

- Tkinter desktop UI.
- Streamer CRUD.
- Timer-based checks.
- Manual check.
- Mock adapter.
- Generic HTTP adapter.
- Bilibili room ID adapter.
- Douyu room ID adapter.
- Huya room ID adapter.
- Twitch official API adapter.
- YouTube official API adapter.
- Search, platform filter, group filter, and favorite filter.
- Selected-streamer check.
- Reminder history.
- Status-change logs.
- Per-streamer custom check interval.
- Live-title change reminders.
- Selected-streamer detection detail panel.
- Platform configuration window for shared Twitch and YouTube credentials.
- Retry backoff.
- Local JSON storage.
- Desktop popup reminder.
- Sound reminder.

Not included yet:

- System tray.
- Auto-start on boot.
- Account login.
- OAuth integration.
- Cloud sync.

## 8. Acceptance Criteria

- `python run.py` opens the desktop app.
- User can add a Mock streamer and check reminder behavior.
- User can choose Bilibili and enter a room ID.
- User can open a Bilibili room from a room ID.
- Streamer list and settings persist after restart.
- Reminder history persists after restart.
- Status logs persist after restart.
- Platform configuration persists after restart.
- Per-streamer custom interval persists after restart.
- Live-title changes can create a status log and optional reminder.
- Users can filter by platform, group, favorite status, and keyword.
- Unit tests pass.
