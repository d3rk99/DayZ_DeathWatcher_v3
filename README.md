# DayZ DeathWatcher

DayZ DeathWatcher is a Discord-connected tool for monitoring DayZ deaths and managing the related whitelist, ban-list, Discord role, revive, alive-time leaderboard, WebUI, and optional multi-server synchronization workflow.

The default setup is for one DayZ server. Multi-server whitelist and ban-list synchronization is optional and only runs when `"sync_enabled": true`.

## Features

- DayZ death monitoring from CFTools Architect Agent detailed logs.
- Discord alive and dead role management.
- Steam ID validation with whitelist and ban-list updates.
- Revive handling through roles, timers, and manual unban file support.
- Optional alive-time leaderboard from disconnect events.
- Optional local WebUI for status, logs, and user database review.
- Optional one-way multi-server whitelist and ban-list synchronization.

## Requirements

- Windows is the primary supported environment.
- Python 3.11 is recommended by `run_bot.bat`.
- Python packages are listed in `requirement.txt`.
- A Discord bot token with server member intent access.
- Discord permissions to read members, manage roles, create/delete/move voice channels, send messages, and use slash commands.
- A DayZ deployment that writes detailed log files. CFTools Architect Agent deployments are the expected path layout, but equivalent detailed log files can work.
- Existing whitelist and ban files. DeathWatcher validates these before it starts.

Install dependencies manually with:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirement.txt
```

## Quick Start: Single Server

1. Download or clone this repository.
2. Install Python dependencies.
3. Copy `config.example.json` to `config.json`.
4. Copy `death_watcher/config.example.json` to `death_watcher/config.json`.
5. Create a Discord bot, invite it to your server, and enable the required intents.
6. Fill in the bot token, guild ID, roles, channels, whitelist path, ban path, and detailed log path.
7. Keep `"sync_enabled": false`.
8. Run `run_bot.bat`.
9. Check the console windows or WebUI at `http://127.0.0.1:8080`.

## Multi-Server Synchronization

Synchronization is one-way. The top-level `whitelist_path` and `blacklist_path` are the master files, and the syncer overwrites each configured target server file with those master lists.

1. Set `"sync_enabled": true`.
2. Keep `whitelist_path` and `blacklist_path` pointed at the master whitelist and ban files.
3. Add each target server whitelist file to `syncer.whitelist_server_paths`.
4. Add each target server ban file to `syncer.blacklist_server_paths`.
5. Set `syncer.sync_interval_seconds` to the polling interval you want.
6. Start with `run_bot.bat`; the launcher starts the syncer only when sync is enabled.
7. Verify the WebUI sync tab shows `Running` and the target files match the master files.

Do not edit target server list files expecting them to merge back. Target lists are overwritten by the master lists.

## Sync Config Migration

Old configs may have used this shape:

```json
{
  "syncer": {
    "whitelist_sync_path": "C:/Master/whitelist.txt",
    "blacklist_sync_path": "C:/Master/ban.txt",
    "whitelist_server_paths": ["C:/Server1/whitelist.txt"],
    "blacklist_server_paths": ["C:/Server1/ban.txt"]
  }
}
```

Use this shape now:

```json
{
  "sync_enabled": false,
  "whitelist_path": "C:/Master/whitelist.txt",
  "blacklist_path": "C:/Master/ban.txt",
  "syncer": {
    "whitelist_server_paths": [],
    "blacklist_server_paths": [],
    "sync_interval_seconds": 10
  }
}
```

Single-server users should set `"sync_enabled": false`; the `syncer` section can be omitted.

Multi-server users should set `"sync_enabled": true`, move old `syncer.whitelist_sync_path` to top-level `whitelist_path`, move old `syncer.blacklist_sync_path` to top-level `blacklist_path`, and keep only target server paths inside `syncer`.

For compatibility, if top-level master paths are missing and old syncer master paths exist, DeathWatcher uses the legacy values and prints a migration warning. It does not silently rewrite your config.

## Configuration Reference

| Key | Required | Default | What it controls |
| --- | --- | --- | --- |
| `prefix` | Yes | `*` | Legacy command prefix. |
| `token` | Yes | None | Discord bot token. Never share it. |
| `sync_enabled` | Yes | `false` | Enables one-way multi-server whitelist and ban-list sync. |
| `whitelist_path` | Yes | None | Master whitelist file. Also the active single-server whitelist. |
| `blacklist_path` | Yes | None | Master ban file. Also the active single-server ban list. |
| `userdata_db_path` | Yes | `./userdata_db.json` | Local Discord/Steam user database. |
| `death_watcher_death_path` | Yes | `./death_watcher/deaths.txt` | File where the death watcher queues GUID deaths for the bot. |
| `death_watcher_alive_time_path` | No | `./death_watcher/alive_times.txt` | File where the death watcher queues alive-time events. |
| `steam_ids_to_unban_path` | Yes | `./steam_ids_to_unban.txt` | Manual unban scratch file. |
| `guild_id` | Yes | None | Discord server ID. |
| `admin_role_id` | Yes | None | Discord admin role ID. |
| `alive_role` | Yes | None | Role assigned to alive players. |
| `dead_role` | Yes | None | Role assigned to dead players. |
| `join_vc_id` | Yes | None | Voice channel users join to create temporary channels. |
| `join_vc_category_id` | Yes | None | Category where temporary voice channels are created. |
| `validate_steam_id_channel` | Yes | None | Channel where `/validatesteamid` is allowed. |
| `error_dump_channel` | No | `-1` | Channel for error messages. `-1` disables Discord error posts. |
| `death_timer_seconds` | No | `1209600` | Seconds before a dead user is automatically revived. |
| `revive_dm_message` | No | Built-in message | DM sent after timed revive. Supports `{username}`, `{display_name}`, and `{mention}`. |
| `watch_death_watcher` | No | `true` | Enables the bot task that consumes death watcher deaths. `0`/`1` still work. |
| `error_dump_allow_mention` | No | `false` | Allows configured error mention tag. `0`/`1` still work. |
| `error_dump_mention_tag` | No | `everyone` | Mention tag or username for error posts when mentions are enabled. |
| `web_ui.host` | No | `127.0.0.1` | WebUI bind address. Use `0.0.0.0` only when you intentionally want LAN access. |
| `web_ui.port` | No | `8080` | WebUI port. |
| `web_ui.log_tail_lines` | No | `200` | Number of log lines shown in the WebUI. |
| `web_ui.bot_log_path` | No | `./bot.log` | Optional bot log file displayed in the WebUI. |
| `syncer.whitelist_server_paths` | Sync only | `[]` | Target server whitelist files overwritten from `whitelist_path`. |
| `syncer.blacklist_server_paths` | Sync only | `[]` | Target server ban files overwritten from `blacklist_path`. |
| `syncer.sync_interval_seconds` | Sync only | `10` | Seconds between sync passes. |
| `alive_leaderboard_channel_id` | No | `-1` | Deprecated alias for leaderboard channel. |
| `leaderboard_text_channel_id` | No | `-1` | Channel where the alive-time leaderboard is posted. |

The death watcher process has its own `death_watcher/config.json`:

| Key | Required | Default | What it controls |
| --- | --- | --- | --- |
| `log_paths` | Yes | None | Detailed log files or folders to watch. |
| `path_to_bans` | Yes | `./deaths.txt` | Death queue file consumed by the bot. |
| `path_to_alive_times` | No | `./alive_times.txt` | Alive-time event queue file consumed by the bot. |
| `cache_paths` | No | `./death_watcher_cache.json` | Per-log read offset cache files. |
| `ban_delay` | No | `5` | Seconds to wait before writing a death. |
| `search_logs_interval` | No | `1` | Seconds between log scans. |
| `verbose_logs` | No | `1` | Prints extra log scan output. |

## Troubleshooting

- `config.json not found`: copy `config.example.json` to `config.json` and edit it.
- Invalid Discord token: regenerate the token in the Discord Developer Portal and update `config.json`.
- Missing permissions or intents: enable Server Members Intent and give the bot Manage Roles plus the channel permissions it needs.
- Bot does not see a user or role: verify the guild ID, role IDs, bot role order, and that the bot is in the server.
- Whitelist or ban file path does not exist: create the file or correct `whitelist_path` / `blacklist_path`.
- Death logs are not detected: check `death_watcher/config.json` `log_paths`, then run the death watcher window and look for path errors.
- Sync is disabled: this is normal when `"sync_enabled": false`.
- Sync targets are invalid: ensure target arrays are lists, contain at least one path each, and every target file exists.
- WebUI cannot be reached: check `web_ui.host`, `web_ui.port`, firewall settings, and the WebUI console.
- Port already in use: change `web_ui.port` or stop the other program using the port.

## Security

Never share `config.json`, Discord tokens, private server paths, logs, or user database files. The repository intentionally ships `config.example.json` with placeholders and ignores local runtime files.

Before public distribution, choose and add a license file.
