"""Multiplayer rooms: room codes, per-room saves and Ably tokens.

Two players share a room code. Live positions travel between the browsers
through Ably, so the Streamlit server is not polled. The server only signs a
short-lived Ably token that is limited to the room's channel; the API key
itself never reaches a browser.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets

ROOM_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I to misread
ROOM_LENGTH = 6
MAX_PLAYERS = 2
TOKEN_TTL_MS = 4 * 60 * 60 * 1000
ABLY_SDK_URL = "https://cdn.jsdelivr.net/npm/ably@2.30.0/build/ably.min.js"
_KEY_PATTERN = re.compile(r"[\w-]+\.[\w-]+:[\w+/=-]+")


def new_room_code() -> str:
    return "".join(secrets.choice(ROOM_ALPHABET) for _ in range(ROOM_LENGTH))


def normalize_room(code) -> str | None:
    """Return an upper-case room code, or None if it is not a valid one."""
    if not isinstance(code, str):
        return None
    code = code.strip().upper()
    if len(code) != ROOM_LENGTH or any(c not in ROOM_ALPHABET for c in code):
        return None
    return code


def save_id(player_id: str, room: str) -> str:
    """A separate save per room, so multiplayer never overwrites single player."""
    return hashlib.sha256(f"{player_id}:room:{room}".encode()).hexdigest()[:32]


def channel_name(room: str) -> str:
    return f"tpt:room:{room}"


def valid_api_key(api_key) -> bool:
    return isinstance(api_key, str) and _KEY_PATTERN.fullmatch(api_key) is not None


def token_request(api_key: str, room: str, client_id: str, now_ms: int, nonce: str | None = None) -> dict:
    """A signed Ably TokenRequest for one room channel.

    The browser exchanges it with Ably for a token. It is limited to publish,
    subscribe and presence on this room's channel and to this player's client id.
    """
    key_name, key_secret = api_key.split(":", 1)
    capability = json.dumps({channel_name(room): ["publish", "subscribe", "presence"]}, separators=(",", ":"))
    nonce = nonce or secrets.token_hex(16)
    signed = "\n".join([key_name, str(TOKEN_TTL_MS), capability, client_id, str(now_ms), nonce]) + "\n"
    mac = base64.b64encode(hmac.new(key_secret.encode(), signed.encode(), hashlib.sha256).digest()).decode()
    return {"keyName": key_name, "ttl": TOKEN_TTL_MS, "capability": capability, "clientId": client_id,
            "timestamp": now_ms, "nonce": nonce, "mac": mac}
