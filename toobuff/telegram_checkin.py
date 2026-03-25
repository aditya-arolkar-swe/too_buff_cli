"""Telegram IO adapter for Too Buff CLI check-in."""

import json
import time as time_module
from pathlib import Path
from typing import Optional, Tuple

import requests

from toobuff.config import get_config_dir

RESPONSE_TIMEOUT = 300  # 5 minutes per question


def get_env_path() -> Path:
    return Path(get_config_dir()) / ".env"


def load_telegram_config() -> Tuple[str, str, Optional[str]]:
    """Load TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, and optional TELEGRAM_THREAD_ID."""
    env_path = get_env_path()

    if not env_path.exists():
        raise FileNotFoundError(
            f"Telegram config not found at {env_path}\n"
            f"Create the file with:\n"
            f"  TELEGRAM_BOT_TOKEN=your_bot_token\n"
            f"  TELEGRAM_CHAT_ID=your_chat_id\n\n"
            f"Get a bot token from @BotFather on Telegram.\n"
            f"Get your chat ID by messaging @userinfobot."
        )

    config = {}
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip().strip("\"'")

    bot_token = config.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = config.get("TELEGRAM_CHAT_ID", "")
    thread_id = config.get("TELEGRAM_THREAD_ID", "") or None

    if not bot_token:
        raise ValueError(f"TELEGRAM_BOT_TOKEN is missing from {env_path}")
    if not chat_id:
        raise ValueError(f"TELEGRAM_CHAT_ID is missing from {env_path}")

    return bot_token, chat_id, thread_id


def _api_post(bot_token: str, method: str, payload: dict) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    resp = requests.post(url, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error ({method}): {data.get('description', 'unknown')}")
    return data.get("result")


def _get_updates(bot_token: str, offset: Optional[int], poll_timeout: int) -> list:
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    params: dict = {
        "timeout": poll_timeout,
        "allowed_updates": json.dumps(["message", "callback_query"]),
    }
    if offset is not None:
        params["offset"] = offset
    resp = requests.get(url, params=params, timeout=poll_timeout + 10)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram API error (getUpdates): {data.get('description', 'unknown')}")
    return data.get("result", [])


def _get_current_offset(bot_token: str) -> Optional[int]:
    """Consume all pending updates so old messages are ignored."""
    updates = _get_updates(bot_token, offset=None, poll_timeout=0)
    return updates[-1]["update_id"] + 1 if updates else None


def _send_message(bot_token: str, chat_id: str, text: str,
                  reply_markup=None, thread_id: Optional[str] = None) -> int:
    payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    if thread_id is not None:
        payload["message_thread_id"] = int(thread_id)
    return _api_post(bot_token, "sendMessage", payload)["message_id"]


def _edit_message(bot_token: str, chat_id: str, message_id: int, text: str) -> None:
    try:
        _api_post(bot_token, "editMessageText", {
            "chat_id": chat_id, "message_id": message_id,
            "text": text, "parse_mode": "HTML",
        })
    except Exception:
        pass


def _answer_callback(bot_token: str, callback_query_id: str) -> None:
    try:
        _api_post(bot_token, "answerCallbackQuery", {"callback_query_id": callback_query_id})
    except Exception:
        pass


def _wait_for_update(bot_token: str, chat_id: str,
                     offset: Optional[int], timeout: int) -> Tuple[dict, int]:
    deadline = time_module.time() + timeout
    current_offset = offset

    while time_module.time() < deadline:
        poll = min(30, int(deadline - time_module.time()))
        if poll <= 0:
            break
        for update in _get_updates(bot_token, offset=current_offset, poll_timeout=poll):
            uid = update["update_id"]
            current_offset = uid + 1
            source: Optional[str] = None
            if "message" in update:
                source = str(update["message"]["chat"]["id"])
            elif "callback_query" in update:
                source = str(update["callback_query"]["message"]["chat"]["id"])
            if source == str(chat_id):
                return update, current_offset

    raise TimeoutError(f"No response received within {timeout} seconds.")


class TelegramIO:
    """Telegram-based IO adapter — mirrors the CliIO interface."""

    def __init__(self, bot_token: str, chat_id: str, thread_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.thread_id = thread_id
        self.offset = _get_current_offset(bot_token)

    def _send(self, text: str, reply_markup=None) -> int:
        return _send_message(self.bot_token, self.chat_id, text,
                             reply_markup=reply_markup, thread_id=self.thread_id)

    def _recv(self, timeout: int = RESPONSE_TIMEOUT) -> dict:
        update, self.offset = _wait_for_update(
            self.bot_token, self.chat_id, self.offset, timeout
        )
        return update

    def prompt(self, label: str, default=None, type_converter=None,
               show_default: bool = True):
        from toobuff.commands import CHECKIN_LABEL_WIDTH
        padded = label.ljust(CHECKIN_LABEL_WIDTH)
        hint = f"  <i>(default: {default})</i>" if default is not None and show_default else ""

        while True:
            self._send(f"<b>{padded}:</b>{hint}")
            update = self._recv()
            text = update.get("message", {}).get("text", "").strip() if "message" in update else ""

            if not text:
                if default is not None:
                    return default
                continue

            if type_converter is not None:
                try:
                    return type_converter(text)
                except (ValueError, TypeError):
                    self._send("Invalid value. Please try again.")
                    continue

            return text

    def confirm(self, label: str, default: bool = True) -> bool:
        from toobuff.commands import CHECKIN_LABEL_WIDTH
        padded = label.ljust(CHECKIN_LABEL_WIDTH)
        keyboard = {"inline_keyboard": [[
            {"text": "✅ Yes", "callback_data": "yes"},
            {"text": "❌ No", "callback_data": "no"},
        ]]}
        msg_id = self._send(f"<b>{padded}:</b>", reply_markup=keyboard)
        update = self._recv()

        if "callback_query" in update:
            cb = update["callback_query"]
            _answer_callback(self.bot_token, cb["id"])
            chosen = cb["data"] == "yes"
            label_text = "✅ Yes" if chosen else "❌ No"
            _edit_message(self.bot_token, self.chat_id, msg_id,
                          f"<b>{padded}:</b> {label_text}")
            return chosen

        if "message" in update:
            return update["message"].get("text", "").strip().lower() in ("yes", "y", "1")

        return default

    def error(self, msg: str):
        self._send(msg)

    def info(self, msg: str):
        self._send(msg)


def run_telegram_checkin(config: dict, dry_run: bool = False) -> None:
    import click
    import pytz
    from datetime import datetime

    from toobuff.commands import collect_checkin, _save_and_display_checkin
    from toobuff.config import load_data

    try:
        bot_token, chat_id, thread_id = load_telegram_config()
    except (FileNotFoundError, ValueError) as exc:
        click.echo(click.style(f"Error: {exc}", fg="red", bold=True))
        import sys
        sys.exit(1)

    et_tz = pytz.timezone("US/Eastern")
    checkin_timestamp = datetime.now(et_tz)
    timestamp_str = checkin_timestamp.strftime("%Y-%m-%d at %I:%M %p %Z")
    data = load_data()

    click.echo(click.style("Connecting to Telegram...", fg="cyan"))
    io = TelegramIO(bot_token, chat_id, thread_id)

    io.info(f"🏋️ <b>Too Buff Daily Check-in</b>\n📅 {timestamp_str}")
    click.echo(click.style(
        "✓ Check-in started in Telegram — answer the questions there.",
        fg="green", bold=True,
    ))

    checkin = collect_checkin(io, checkin_timestamp)
    _save_and_display_checkin(checkin, checkin_timestamp, data, config, dry_run, io=io)

    if not dry_run:
        io.info("✅ <b>Check-in recorded successfully!</b>")
