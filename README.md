# life_and_death_bot

## WebUI

Run the WebUI on the same machine as the scripts to monitor the bot, death watcher, and syncer.
The server binds to `0.0.0.0` by default, so devices on the same LAN can access it.

```bash
python web_ui.py
```

You can adjust the host, port, and log tail size in `config.json`:

```json
"web_ui" : {
  "host" : "0.0.0.0",
  "port" : 8080,
  "log_tail_lines" : 200
}
```

## Config example

```yaml
deathwatcher:
  log_paths:
    - "D:\\Servers\\Chernarus\\profiles\\logs"
    - "D:\\Servers\\Livonia\\profiles\\logs"
```
