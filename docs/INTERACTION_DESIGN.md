# Interaction Design: Streamer Live Monitor

## 1. Interaction Goals

- Let users add a streamer in under one minute.
- Make live status clear at a glance.
- Keep monitoring controls predictable for long-running desktop use.
- Make reminder behavior understandable and non-repetitive.
- Support both room URL and room ID input without forcing users to know platform-specific details.

## 2. Main User Flows

### 2.1 Add Streamer

1. User enters nickname.
2. User selects platform.
3. User enters room URL or room ID.
4. User optionally adds group and remark.
5. User optionally marks the streamer as favorite.
6. User optionally sets a per-streamer check interval.
7. User chooses monitoring and reminder toggles.
8. User clicks `Save Streamer`.
9. App validates required fields.
10. App saves the streamer and refreshes the table.

Validation:

- Nickname is required.
- Room URL or room ID is required.
- Platform must be selected.

Success feedback:

- Footer status shows `Added: {nickname}`.
- The new streamer appears in the table.

Failure feedback:

- A modal warning explains the missing field.

### 2.2 Edit Streamer

1. User selects a row in the table.
2. Form is populated with the selected streamer.
3. User changes fields.
4. User clicks `Save Streamer`.
5. App updates local storage and refreshes the table.

Success feedback:

- Footer status shows `Updated: {nickname}`.
- The detection detail line reflects the latest saved interval and status.

### 2.3 Delete Streamer

1. User selects a streamer.
2. User clicks `Delete`.
3. App asks for confirmation.
4. If confirmed, app deletes the streamer and clears the form.

Destructive action rule:

- Deletion must always require confirmation.

### 2.4 Manual Check

1. User clicks `Check Now`.
2. App saves current settings first.
3. App starts an async check.
4. Footer status shows checking progress.
5. Table updates row by row.

Concurrency rule:

- If a previous check is still running, app should show a non-blocking message instead of starting duplicate checks.

### 2.4.1 Check Selected Streamer

1. User selects a row in the table.
2. User clicks `Check Selected`.
3. App checks only that streamer.
4. Footer status shows progress.
5. The selected row refreshes after the check.

### 2.5 Automatic Monitoring

1. App starts monitoring after launch.
2. Every configured interval, app checks enabled streamers.
3. Disabled streamers are skipped.
4. Failed checks affect only that streamer.
5. Table and summary are refreshed after updates.

### 2.6 Open Live Room

1. User selects a streamer.
2. User clicks `Open Live Room` or double-clicks a table row.
3. If the saved value is an HTTP/HTTPS URL, app opens it directly.
4. If the saved value is a room ID and the platform adapter supports URL building, app builds the watch URL.
5. Otherwise, app shows an explanatory message.

Example:

- Bilibili room ID `123456` opens `https://live.bilibili.com/123456`.

### 2.7 Live Reminder

Trigger:

- Streamer status changes to live.
- Global notifications are enabled.
- Streamer reminder is enabled.
- The live session was not notified before.

Reminder UI:

- Toast title: `{nickname} is live`.
- Detail line: live title or platform name.
- Primary action: `Open Live Room`.
- Secondary action: `Close`.
- Auto-dismiss after a short delay.

Duplicate prevention:

- Do not notify again for the same live session.
- Notify again only after the streamer goes offline and then starts a new session, or after adapter returns a new live ID.

### 2.7.1 Live Title Change Reminder

Trigger:

- Streamer is already live.
- Adapter returns a new non-empty live title.
- Global notifications, streamer reminder, and title-change reminders are enabled.

Reminder UI:

- Toast title: `{nickname} title updated`.
- Detail line: new title.

Logging:

- The title change is written to status logs with old and new title values.

### 2.8 Filter Streamers

1. User enters a keyword, selects a platform, selects a group, or toggles favorite-only.
2. Table refreshes immediately.
3. Summary counters update to match the visible filtered rows.
4. If there are no matching streamers, the table shows an inline empty state.

Selection rule:

- Changing platform, group, or favorite filters clears the current table selection to avoid acting on a hidden streamer.

### 2.9 Reminder History

1. User clicks `Reminder History`.
2. App opens the reminder history window.
3. User can double-click a record or click `Open Live Room`.
4. User can clear all history after confirmation.

### 2.9.1 Status Logs

1. User clicks `Status Log`.
2. App opens the status log window.
3. User can inspect status transitions and live-title changes.
4. User can double-click a record or click `Open Live Room`.
5. User can clear all logs after confirmation.

### 2.9.2 Platform Configuration

1. User clicks `Platform Config`.
2. App opens the platform configuration window.
3. User enters shared Twitch or YouTube credentials.
4. User clicks `Save Config`.
5. Future checks append these credentials to the adapter input.

Rules:

- Empty values remove the saved key.
- Per-streamer remark values can still be used for streamer-level overrides or extra fields.

### 2.10 Failure Backoff

1. A streamer check fails.
2. App increments the streamer's consecutive failure count.
3. If backoff is enabled, app delays the next automatic check for that streamer.
4. A successful non-error result resets the failure count and delay.

### 2.11 Detection Detail Panel

1. User selects a streamer.
2. The detail line shows status, last check time, consecutive failures, effective interval, next check time, live session ID, and latest error or title.
3. Automatic and manual checks refresh the detail line when the selected streamer changes.

## 3. Screen States

### 3.1 Empty State

Current MVP behavior:

- Table is empty.
- User can use `Add Example`.

Recommended improvement:

- Show an inline empty message in the table area: `No streamers yet`.
- Keep `Add Example` visible.

### 3.2 Normal State

- Summary shows monitored, live, offline, and failed counts.
- Table shows all saved streamers.
- If filters are active, table shows only matching streamers.
- Live streamers appear before offline streamers.
- Selected streamer details are visible below the form controls.
- Footer shows last user action or check result.

### 3.3 Checking State

- Footer shows `Checking...`.
- Manual check button can stay enabled, but duplicate checks should be rejected by service logic.

### 3.4 Error State

- Row status shows `Check failed`.
- Footer or row selection shows the error message.
- Other streamers remain interactive.

### 3.5 Reserved Platform State

- Status shows `Unknown`.
- Detail explains that the platform entry is reserved and requires official API, authorized interface, or compliant status service.

## 4. Interaction Rules

- Single selection in the streamer table.
- Selecting a row always syncs the form with row data.
- Changing the platform filter clears table selection.
- Changing group or favorite filters clears table selection.
- `New` clears form fields and table selection.
- `Save Streamer` creates a new streamer only when no row is selected.
- `Save Settings` persists interval, notification, sound, backoff, and title-change reminder settings.
- `Check Now` should not block the UI thread.
- `Check Selected` should not block the UI thread.
- Reminder history clear requires confirmation.
- Status log clear requires confirmation.
- Platform config clear requires confirmation.
- App shutdown should stop monitor threads safely.

## 5. Accessibility Notes

- Buttons use explicit text labels.
- Form labels are placed immediately before inputs.
- Status is text-based, not color-only.
- Dialogs are used for validation and destructive confirmation.

## 6. Future Interaction Enhancements

- Add inline empty state.
- Add platform-specific placeholder text for the room input.
- Add row-level quick actions.
- Add system tray minimize behavior.
- Add notification click action that opens the correct platform URL.
- Add import/export for streamer lists.
- Add richer per-platform setup validation.
- Add quick copy for status log entries.
