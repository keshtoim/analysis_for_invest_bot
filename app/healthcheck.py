import sys
import time

from app.config import HEARTBEAT_PATH

MAX_AGE_SECONDS = 5 * 60


def is_alive() -> bool:
    try:
        with open(HEARTBEAT_PATH, encoding="utf-8") as f:
            last_beat = float(f.read().strip())
    except (FileNotFoundError, ValueError):
        return False
    return time.time() - last_beat < MAX_AGE_SECONDS


if __name__ == "__main__":
    sys.exit(0 if is_alive() else 1)
