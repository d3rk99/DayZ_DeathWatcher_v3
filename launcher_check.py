import sys

from config_loader import ConfigError, load_config, sync_startup_message


def main() -> int:
    try:
        config, warnings = load_config("config.json")
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return 1

    for warning in warnings:
        print(f"Configuration warning: {warning}")
    print(sync_startup_message(config))
    print("SYNC_ENABLED=1" if config.get("sync_enabled") else "SYNC_ENABLED=0")
    return 0


if (__name__ == "__main__"):
    sys.exit(main())
