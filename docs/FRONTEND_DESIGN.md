# Frontend Design: Streamer Live Monitor

## 1. Design Direction

The app is a desktop utility for repeated, long-running use. The frontend should feel quiet, compact, and operational rather than promotional. The main screen should prioritize scanning, editing, and checking streamers quickly.

Design keywords:

- Clear
- Dense
- Stable
- Low distraction
- Utility-first

## 2. Information Architecture

Single-window MVP layout:

```text
Header
|-- App title
`-- Summary counters

Streamer Form
|-- Streamer name
|-- Platform
|-- Room URL / Room ID
|-- Group
|-- Favorite
|-- Remark
|-- Monitoring toggle
|-- Reminder toggle
|-- Custom interval
|-- Detection detail line
`-- Actions

Streamer Table
|-- Keyword search
|-- Platform filter
|-- Group filter
|-- Favorite filter
|-- Status
|-- Favorite
|-- Streamer name
|-- Platform
|-- Group
|-- Live title
|-- Monitoring
|-- Reminder
|-- Last checked
`-- Room URL / Room ID

Settings Bar
|-- Check interval
|-- Notification toggle
|-- Sound toggle
|-- Failure backoff toggle
|-- Title-change reminder toggle
|-- Save settings
|-- Check selected
|-- Check now
|-- Reminder history
|-- Status log
|-- Platform config
`-- Add example

Footer
|-- Current status message
`-- Data file path
```

## 3. Layout Rules

- Use one main window with no landing page.
- Keep the streamer table as the visual center of the app.
- Keep settings close to the table because they affect monitoring behavior.
- Keep form controls above the table to support quick add/edit flows.
- Do not use nested cards.
- Do not use decorative backgrounds or large hero sections.
- Prefer compact controls and predictable alignment.

## 4. Component Specs

### 4.1 Header

Purpose:

- Identify the app.
- Show system-level monitoring summary.

Content:

- Left: `Streamer Live Monitor` or localized app title.
- Right: monitored count, live count, offline count, failed count.

Behavior:

- Counts update after every table refresh.

### 4.2 Streamer Form

Fields:

- Streamer name: text input.
- Platform: read-only dropdown.
- Room URL / Room ID: text input.
- Group: text input.
- Favorite: checkbox.
- Remark: multi-line text.
- Monitoring enabled: checkbox.
- Reminder enabled: checkbox.
- Custom interval: numeric input, `0` means use global interval.
- Detection detail line: selected streamer status, last check, failures, next check, session ID, and latest error or title.

Primary action:

- `Save Streamer`.

Secondary actions:

- `New`
- `Delete`
- `Open Live Room`

Validation:

- Streamer name required.
- Room URL / Room ID required.

### 4.3 Streamer Table

Toolbar:

- Current selection summary.
- Keyword search box.
- Platform filter dropdown.
- Group filter dropdown.
- Favorite-only toggle.
- Visible/total count.
- Double-click hint.

Columns:

- Status
- Favorite
- Streamer name
- Platform
- Group
- Live title
- Monitoring
- Reminder
- Last checked
- Room URL / Room ID

Status labels:

- Unknown
- Offline
- Live
- Check failed

Recommended visual treatment:

- Live: green text or badge.
- Check failed: red text or badge.
- Offline: neutral.
- Unknown: muted.

Current implementation uses text labels plus row-level status color.

Filtering:

- `All Platforms` shows every streamer.
- Selecting one platform shows only streamers from that platform.
- Selecting one group shows only streamers in that group.
- Favorite-only shows only favorite streamers.
- Keyword search matches streamer name, platform, group, room URL, remark, live title, and last error.
- Summary counters follow the current filtered table view.
- Empty state explains when no streamer matches the selected platform.

Sorting:

- Enabled streamers are shown before disabled streamers.
- Live streamers are shown before failed/unknown/offline streamers.
- Offline streamers are placed after active or uncertain statuses.

### 4.4 Settings Bar

Controls:

- Check interval numeric input.
- Notification checkbox.
- Sound checkbox.
- Failure backoff checkbox.
- Title-change reminder checkbox.
- Save settings button.
- Check selected button.
- Check now button.
- Reminder history button.
- Status log button.
- Platform config button.
- Add example button.

Rules:

- Minimum interval is 10 seconds.
- Saving settings should be explicit.
- Check now should save current settings first.
- Check selected should only check the currently selected streamer.
- Failure backoff should reduce repeated failed checks.
- Title-change reminder can be disabled without disabling live-start reminders.

### 4.5 Toast Reminder

Layout:

```text
Title: {nickname} is live
Detail: live title or platform

[Open Live Room] [Close]
```

Behavior:

- Topmost window.
- Auto-dismiss after several seconds.
- Sound plays if enabled.

### 4.6 Reminder History Window

Columns:

- Reminder time
- Streamer
- Platform
- Title
- Room URL

Actions:

- Open live room.
- Clear history.

### 4.7 Status Log Window

Columns:

- Time
- Streamer
- Platform
- Event
- Old status
- New status
- Old title
- New title
- Room URL

Actions:

- Refresh.
- Open live room.
- Clear logs.

### 4.8 Platform Config Window

Fields:

- Twitch Client ID.
- Twitch App Token.
- YouTube API Key.

Actions:

- Save config.
- Clear config.

Behavior:

- Secret fields are masked.
- Empty fields remove saved values.
- The window is separate from streamer editing because values are shared by multiple streamers.

## 5. Visual Style

### 5.1 Color

Recommended palette:

- Background: `#f7f7f5`
- Surface: system default or `#ffffff`
- Text: `#202124`
- Muted text: `#5f6368`
- Live: `#0f7b45`
- Error: `#b42318`
- Border: `#d7d7d2`

Use color as reinforcement, not as the only signal.

### 5.2 Typography

- Use system UI font.
- Window title area: 16px equivalent, bold.
- Form/table text: default system size.
- Avoid oversized headings inside the utility layout.

### 5.3 Spacing

- Outer padding: 12px.
- Form internal padding: 10px.
- Vertical section gap: 8-10px.
- Button gap: 6-8px.

### 5.4 Responsive Behavior

The desktop window should support resizing:

- Table expands vertically and horizontally.
- Form text inputs expand horizontally.
- Action buttons keep stable width.
- Minimum window size prevents cramped controls.

## 6. Platform Input Guidance

Room input label:

- `Room URL / Room ID`

Examples:

- Bilibili: `123456` or `https://live.bilibili.com/123456`
- Douyu: `475252` or `https://www.douyu.com/475252`
- Huya: `room-id` or `https://www.huya.com/room-id`
- Twitch: channel name or `https://www.twitch.tv/channel`
- YouTube: video URL, or `channel_id=...` in the remark field
- Mock: `mock://live`
- Generic HTTP: `https://example.com/live-status.json`

Future improvement:

- Change placeholder/help text based on selected platform.

Current implementation:

- The room input hint changes when the selected platform changes.
- Twitch and YouTube shared credentials can be edited through `Platform Config`.

## 7. Future Frontend Enhancements

- Inline empty state for first-time users.
- Row-level status color styling.
- Search/filter streamers.
- Group by platform.
- System tray mode.
- Import/export dialog.
- Per-platform setup help.
- Better toast positioning across multi-monitor setups.
- Status log export.
- Platform credential validation.
