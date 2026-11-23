"""Streamlit entry point for Team Plot Twist: Escape from the pirate ship."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from contextlib import closing
from dataclasses import asdict
from functools import partial
from pathlib import Path

import streamlit as st

from runtime_loader import load_backend
BACKEND_REVISION = load_backend(Path(__file__).resolve().parent)

from db import apply_action, claim_legacy, connect_db, load_game, new_game, restore_game, save_position
from logic import (GUARD_ROUTES, GUARD_SEGMENTS, MAP_CONFIG, Position, capture_paths,
                   state_from_backup, story_progress, game_now_ms, route_points)
from action_transport import handle_action
from content import DOCUMENTS, ENDINGS, FINALE_RESCUE_EPILOGUE, ITEMS, ROLES, STORY_POINTS
import finale
import multiplayer as mp
import shared_ship
from journal import journal_hints


ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TEAM_PLOT_TWIST_DB", ROOT / "data" / "team-progress.sqlite3"))
COMPONENT_DIR = ROOT / "game_component"
STATIC_BUILD_DIR = ROOT / "static" / "build"

st.set_page_config(
    page_title="Team Plot Twist · Escape from the pirate ship",
    page_icon="🏴‍☠️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def read_progress(player_id: str, browser_backup=None):
    with closing(connect_db(DB_PATH)) as conn:
        state = load_game(conn, player_id)
        if state is None and claim_legacy(conn, player_id):
            state = load_game(conn, player_id)
        if state is None and browser_backup is not None:
            if restore_game(conn, browser_backup, player_id):
                state = load_game(conn, player_id)
        if state is not None and STORY_POINTS.get(state.reading,{}).get('kind')=='chest':
            apply_action(conn,'close_reading',state.position,0,player_id,now_ms=int(time.time()*1000))
            state=load_game(conn,player_id)
        return state


def begin_play(state=None, epoch_ms=None, show_intro=False):
    st.session_state.playing = True
    st.session_state.confirm_new = False
    st.session_state.run_id = uuid.uuid4().hex
    if show_intro:
        st.session_state.intro_run_id = st.session_state.run_id
    # In a room every player uses the room's clock, so the guards walk the
    # same routes for both.
    st.session_state.guard_started_ms = (epoch_ms if epoch_ms is not None else
                                         game_now_ms(state, int(time.time() * 1000))
                                         if state is not None else int(time.time() * 1000))
    st.session_state.feedback_request_id = ""
    st.session_state.feedback_seq = 0
    st.session_state.feedback_text = ""
    st.session_state.feedback_accepted = False


def apply_game_action(player_id):
    """Apply a canvas action in the widget callback, before the script runs.

    The page then draws the result in the same run. Applying it after the
    canvas was drawn needed a second full run (st.rerun), which online costs
    another server round trip for every key press.
    """
    action = (st.session_state.get(f"game_canvas_{player_id}") or {}).get("action")
    if not isinstance(action, dict) or "run_id" not in st.session_state:
        return
    cache = st.session_state.setdefault("action_acknowledgements", {})
    room = st.session_state.get("room")
    wall_now = int(time.time() * 1000)
    epoch = None
    with closing(connect_db(DB_PATH)) as conn:
        before = load_game(conn, player_id) if room else None
        outcome, request_id, duplicate = handle_action(conn, action, player_id,
            st.session_state.run_id, cache, wall_now)
        if room and before is not None and outcome.accepted and not duplicate:
            outcome = share_room_action(conn, room, player_id, action, before, outcome, wall_now)
            epoch = shared_ship.room_info(conn, room)["epoch_ms"]
            st.session_state.room_generation = shared_ship.room_info(conn, room)["generation"]
    # A position snapshot that arrives together with an action is dropped:
    # a rejected action must never cause a database write.
    st.session_state.action_applied = True
    if not duplicate and outcome.accepted and action.get("kind") in ("capture_complete", "capture_tick", "restart_game") and outcome.state.capture_phase == "none":
        begin_play(epoch_ms=epoch)
        st.session_state.feedback_text = outcome.message
        st.session_state.feedback_seq = 1
        st.session_state.feedback_accepted = True
        return
    st.session_state.feedback_seq += 1
    st.session_state.feedback_request_id = request_id
    st.session_state.feedback_text = outcome.message
    st.session_state.feedback_accepted = outcome.accepted


def share_room_action(conn, room, save_id, action, before, outcome, wall_now):
    """Make an accepted action in a room happen on the shared ship."""
    from dataclasses import replace as dc_replace
    kind = action.get("kind")
    if kind == "restart_game":
        shared_ship.restart(conn, room, wall_now)
        return dc_replace(outcome, state=load_game(conn, save_id))
    after = load_game(conn, save_id)
    if before.capture_phase == "active" and after.capture_phase == "none" and kind in ("capture_complete", "capture_tick"):
        # Caught: back to the locked cell, while the crew search for the partner.
        others = [load_game(conn, m) for m in shared_ship.members(conn, room) if m != save_id]
        last_seen = next((s.position for s in others if s is not None), None)
        try:
            elapsed = float(action.get("guard_elapsed", 0))
        except (TypeError, ValueError):
            elapsed = 0.
        after = shared_ship.jailed(before, elapsed, game_now_ms(before, wall_now), last_seen)
    after = shared_ship.unpaused(before, after)
    with conn:
        from db import _write_game
        _write_game(conn, after, save_id)
    shared_ship.share(conn, room, save_id, before, after)
    return dc_replace(outcome, state=after)


def position_from_payload(payload):
    if not isinstance(payload, dict):
        return None
    try:
        return Position(str(payload["zone"]), float(payload["value"]))
    except (KeyError, TypeError, ValueError):
        return None


@st.cache_resource
def cached_component(name, html, css, js):
    # File contents participate in the cache key, so a live deployment cannot
    # keep serving the previous JavaScript, HTML or translation settings.
    return st.components.v2.component(name=name, html=html, css=css, js=js)


def publish_script(name, source):
    """Serve source as a static file named by its content hash; return its URL.

    A new name for every change means browsers can cache the file and still
    never run an outdated version after a deployment.
    """
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    target = STATIC_BUILD_DIR / f"{name}-{digest}.js"
    if not target.exists():
        STATIC_BUILD_DIR.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f"{target.name}.{uuid.uuid4().hex}.tmp")
        temporary.write_text(source, encoding="utf-8")
        os.replace(temporary, target)
        for old in STATIC_BUILD_DIR.glob(f"{name}-*.js"):
            if old != target:
                old.unlink(missing_ok=True)
    return f"app/static/build/{target.name}"


# Streamlit sends a component's inline code with every run. Inlining the game
# (over 120 KB) made every key press download it again, so the inline part is
# only this loader and the browser fetches the game file once.
GAME_LOADER = """
const source = new URL(%s, document.baseURI).href;
export default function (args) {
  let cleanup = null, gone = false;
  import(source).then(game => { if (!gone) cleanup = game.default(args); }).catch(error => {
    console.error("Team Plot Twist could not load the game", error);
    const note = document.createElement("p");
    note.textContent = "The game could not load. Reload the page to try again.";
    args.parentElement.prepend(note);
  });
  return () => { gone = true; if (typeof cleanup === "function") cleanup(); };
}
"""


def game_component():
    script = publish_script("game", (COMPONENT_DIR / "game.js").read_text(encoding="utf-8"))
    return cached_component(
        "team_plot_twist_canvas_game",
        (COMPONENT_DIR / "game.html").read_text(encoding="utf-8"),
        (COMPONENT_DIR / "game.css").read_text(encoding="utf-8"),
        GAME_LOADER % json.dumps(script),
    )


def browser_identity_component():
    return cached_component("team_plot_twist_browser_identity", "<span aria-hidden='true'></span>", "",
                            (COMPONENT_DIR / "browser_identity.js").read_text(encoding="utf-8"))


def browser_backup_component():
    return cached_component("team_plot_twist_browser_backup", "<span aria-hidden='true'></span>", "",
                            (COMPONENT_DIR / "browser_backup.js").read_text(encoding="utf-8"))


def sync_browser_backup(player_id, state):
    browser_backup_component()(
        data={"player_id": player_id, "state": asdict(state) if state is not None else None},
        key="browser_backup",
        height=1,
    )


def ably_api_key():
    """The Ably key from Streamlit secrets or the environment, if configured."""
    try:
        key = st.secrets.get("ABLY_API_KEY")
    except Exception:  # no secrets file at all
        key = None
    key = key or os.environ.get("ABLY_API_KEY")
    return key if mp.valid_api_key(key) else None


def enter_room(player_id, room):
    """Join a room: continue its save, or start both players in the cell."""
    game_id = mp.save_id(player_id, room)
    with closing(connect_db(DB_PATH)) as conn:
        info = shared_ship.join(conn, room, game_id, int(time.time() * 1000))
        state = load_game(conn, game_id)
    st.session_state.room = room
    st.session_state.room_generation = info["generation"]
    st.query_params["room"] = room
    begin_play(state, info["epoch_ms"])


def leave_room():
    st.session_state.pop("room", None)
    if "room" in st.query_params:
        del st.query_params["room"]
    st.session_state.playing = False


def multiplayer_lobby(player_id, api_key):
    """Create or join a room. Returns True when the page should stop here."""
    if "room" in st.session_state:
        room = st.session_state.room
        info, leave = st.columns([4, 1])
        info.success(f"Room **{room}**. Your friend chooses Multiplayer, enters `{room}` and presses Join.")
        if leave.button("Leave room", use_container_width=True):
            leave_room()
            st.rerun()
        return False
    if api_key is None:
        st.info("Multiplayer needs an Ably API key. Add `ABLY_API_KEY` to the app's Streamlit secrets.")
        return True
    st.caption("Two players start in the same cell and see each other move live.")
    create_col, code_col, join_col = st.columns([1.2, 1.2, 1])
    with create_col:
        if st.button("Create room", use_container_width=True, type="primary"):
            enter_room(player_id, mp.new_room_code())
            st.rerun()
    with code_col:
        code = st.text_input("Room code", value=st.query_params.get("room", ""), max_chars=mp.ROOM_LENGTH,
                             placeholder="ABC234", label_visibility="collapsed")
    with join_col:
        if st.button("Join", use_container_width=True):
            room = mp.normalize_room(code)
            if room is None:
                st.error(f"A room code has {mp.ROOM_LENGTH} letters and digits.")
            else:
                enter_room(player_id, room)
                st.rerun()
    return True


def main():
    st.markdown(
        """
        <style>
        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
          background: #132b34 !important; }
        .stApp { background:radial-gradient(ellipse at 50% 0%,#1b3036 0%,#101b22 45%,#0b1218 100%); color:#e8ede8; }
        [data-testid="stHeader"] { background: transparent !important; }
        [data-testid="stAppDeployButton"] { display:none; }
        .block-container { max-width: 1280px; padding-top: .8rem; padding-bottom: 2rem; }
        .pt-hero { position: relative; min-height: 330px; margin: 0 0 1.15rem; overflow: visible;
          border: 0; border-radius: 0; background: transparent; box-shadow: none; isolation: isolate; }
        .pt-hero__art { position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: -2; pointer-events: none; }
        .pt-hero::after { content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
          background: linear-gradient(90deg, rgba(8,22,29,.82), rgba(8,22,29,.48) 48%, rgba(8,22,29,.1)),
          linear-gradient(0deg, rgba(6,20,27,.45), transparent 55%); }
        .pt-hero__copy { position: relative; z-index: 1; max-width: 690px; padding: 34px 38px 30px; color: #f7eedb; }
        .pt-hero__eyebrow { margin: 0 0 8px; color: #e3c28a; font: 700 12px/1.2 system-ui,sans-serif;
          letter-spacing: .19em; text-transform: uppercase; }
        .pt-hero h1 { margin: 0; color: #fff6e4; font: 700 clamp(30px,4vw,48px)/1.04 Georgia,serif;
          letter-spacing: -.025em; text-shadow: 0 3px 18px rgba(0,0,0,.45); }
        h1 { margin-bottom:.1rem; font-family:Georgia,serif; color:#f0e6d1; }
        .pt-app-wordmark { display:flex; align-items:center; gap:10px; margin:0 0 10px; color:#d4ba86;
          font:750 11px/1.4 system-ui,sans-serif; letter-spacing:.2em; }
        .pt-app-wordmark::before { content:""; width:22px; height:1px; background:#b99a60; }
        .pt-hero__copy p:last-child { margin: 13px 0 0; color: #e1e0d4; font: 16px/1.55 Georgia,serif; }
        [data-testid="stRadio"] label, [data-testid="stCaptionContainer"] { color: #e1e0d4 !important; }
        [data-testid="stRadio"] [role="radiogroup"] { gap:18px; }
        [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] strong { color: #e1e0d4; }
        div[data-testid="stButton"] button { min-height: 48px; border-radius: .7rem;
          border: 1px solid #365058; background:#182c32; color:#e5e9df; font-weight: 700;
          transition: transform .15s ease, box-shadow .15s ease; }
        div[data-testid="stButton"] button:hover { transform: translateY(-1px); box-shadow: 0 5px 14px rgba(22,42,49,.18); }
        div[data-testid="stButton"] button[kind="primary"], [data-testid="stBaseButton-primary"] {
          color:#17272d !important; background:#f2dfa9 !important; border:2px solid #fff1c9 !important;
          font-size:1.05rem; font-weight:800; text-shadow:none; }
        div[data-testid="stButton"] button:not([kind="primary"]), [data-testid="stBaseButton-secondary"] {
          color:#17272d !important; background:#fff8e8 !important; border:2px solid #e7d4a7 !important;
          font-size:1.05rem; font-weight:800; text-shadow:none; }
        div[data-testid="stButton"] button:disabled, [data-testid="stBaseButton-secondary"]:disabled {
          color:#354247 !important; background:#e6dcc5 !important; border-color:#cbbd9b !important; opacity:1 !important; }
        div[data-testid="stButton"] button:hover:not(:disabled) { filter:brightness(.96); }
        [data-testid="stExpander"] { border-color:#2d454d; border-radius:10px; }
        [data-testid="stAlert"] { border-radius: 12px; background: rgba(37,62,70,.88); color: #f1eadb; }
        @media (max-width: 640px) {
          .pt-hero { min-height: 300px; }
          .pt-hero__copy { padding: 27px 23px; }
          .pt-hero__copy p:last-child { max-width: 34ch; font-size: 14px; }
          .pt-hero::after { background: linear-gradient(90deg,rgba(8,22,29,.82),rgba(8,22,29,.36)),linear-gradient(0deg,rgba(6,20,27,.42),transparent 58%); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.get("playing"):
        st.markdown('<div class="pt-app-wordmark">THE VOYAGE · TEAM PLOT TWIST</div>', unsafe_allow_html=True)
    else:
        st.markdown(
        '''
        <section class="pt-hero" aria-label="Pirates surround the prisoner at sea">
          <svg class="pt-hero__art" viewBox="0 0 1200 360" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
            <defs>
              <linearGradient id="pt-sky" x2="0" y2="1"><stop stop-color="#314b57"/><stop offset=".68" stop-color="#8c9b99"/><stop offset="1" stop-color="#536f75"/></linearGradient>
              <linearGradient id="pt-sea" x2="0" y2="1"><stop stop-color="#496f78"/><stop offset="1" stop-color="#142f3a"/></linearGradient>
              <linearGradient id="pt-fog" x2="0" y2="1"><stop stop-color="#e0e1d5" stop-opacity=".05"/><stop offset=".62" stop-color="#d8ded7" stop-opacity=".62"/><stop offset="1" stop-color="#c4d1ce" stop-opacity=".03"/></linearGradient>
              <filter id="pt-blur"><feGaussianBlur stdDeviation="13"/></filter>
            </defs>
            <rect width="1200" height="230" fill="url(#pt-sky)"/><rect y="220" width="1200" height="140" fill="url(#pt-sea)"/>
            <path d="M0 239 Q85 228 170 240 T340 239 T510 240 T680 238 T850 240 T1020 238 T1200 240" fill="none" stroke="#b7c4bc" stroke-opacity=".3" stroke-width="3"/>
            <g fill="#172b31" stroke="#111f25" stroke-width="5">
              <path d="M56 212 Q130 225 204 212 L190 238 Q130 251 70 238Z"/><path d="M126 210V86l18 13v111Z"/><path d="M145 100l43 24-43 18Z"/>
              <path d="M950 208 Q1034 226 1118 208 L1096 239 Q1034 253 972 239Z"/><path d="M1027 207V72l18 15v120Z"/><path d="M1045 88l52 28-52 21Z"/>
            </g>
            <g fill="#171c1c"><path d="M149 105l27 13-27 14Z"/><path d="M1047 92l35 19-35 19Z"/></g>
            <g opacity=".9" fill="#d3d0bd"><circle cx="160" cy="119" r="3"/><path d="M155 125l10 5m0-5-10 5" stroke="#d3d0bd" stroke-width="2"/></g>
            <g opacity=".88" fill="#d3d0bd"><circle cx="1060" cy="108" r="3"/><path d="M1055 114l10 5m0-5-10 5" stroke="#d3d0bd" stroke-width="2"/></g>
            <g fill="#17272c" stroke="#17272c" stroke-linecap="round" stroke-width="8">
              <path d="M336 260l-7 52m35-52 9 52m-25-85v45m0-38-19 16m20-15 17 14"/><circle cx="348" cy="224" r="13"/>
              <path d="M467 250l-8 64m39-64 8 64m-24-99v47m-1-37-23-17m23 17 25-28"/><circle cx="477" cy="205" r="14"/>
              <path d="M734 251l-8 63m38-63 8 63m-22-97v47m0-34-20-18m20 18 24-27"/><circle cx="741" cy="207" r="14"/>
              <path d="M859 261l-7 51m35-51 8 51m-24-79v40m-1-31-18-14m19 15 19-22"/><circle cx="871" cy="228" r="12"/>
            </g>
            <g fill="none" stroke="#d5d9d4" stroke-linecap="round" stroke-width="4">
              <path d="M358 200l34-37m-4 0 8 5-8 5"/><path d="M498 183l-31-35m-1 0 8-1-1 8"/>
              <path d="M761 184l30-38m-2-1 8 5-8 5"/><path d="M881 211l-26-35m-1 0 8-1-1 8"/>
            </g>
            <g stroke-linecap="round" stroke-width="11">
              <path d="M455 300l-7 42m49-42 7 42" stroke="#161c20"/>
              <path d="M461 252v51m-2-39-19 13m20-14 19 13" stroke="#34717b"/>
              <circle cx="461" cy="237" r="14" fill="#d3a27c" stroke="#352b27" stroke-width="3"/>
              <path d="M447 233q14-23 29 0" fill="#263a41" stroke="#263a41" stroke-width="7"/>
            </g>
            <rect y="188" width="1200" height="129" fill="url(#pt-fog)"/>
            <g filter="url(#pt-blur)" fill="#e2e4dc" opacity=".25"><ellipse cx="292" cy="235" rx="185" ry="24"/><ellipse cx="875" cy="246" rx="220" ry="22"/></g>
          </svg>
          <div class="pt-hero__copy">
            <p class="pt-hero__eyebrow">A pirate ship adventure</p>
            <h1>Team Plot Twist</h1>
            <p>Escape from the pirate ship. Six ways to freedom — explore, find clues and choose your escape.</p>
          </div>
        </section>
        ''',
        unsafe_allow_html=True,
    )

    if "playing" not in st.session_state:
        st.session_state.playing = False
    if "confirm_new" not in st.session_state:
        st.session_state.confirm_new = False
    if "browser_backup" not in st.session_state:
        st.session_state.browser_backup = None
    if "browser_storage_available" not in st.session_state:
        st.session_state.browser_storage_available = True
    identity = browser_identity_component()(
        data={"request_identity": "player_id" not in st.session_state},
        on_identity_change=lambda: None,
        key="browser_identity",
        height=1,
    ).identity
    if "player_id" not in st.session_state:
        if not isinstance(identity, dict):
            st.info("Reading your saved progress …")
            return
        player_id = identity.get("id")
        if not isinstance(player_id, str) or re.fullmatch(r"[0-9a-f]{32}", player_id) is None:
            st.error("Could not create a game in this browser. Reload the page.")
            return
        st.session_state.player_id = player_id
        st.session_state.browser_backup = state_from_backup(identity.get("backup"))
        st.session_state.browser_storage_available = bool(identity.get("storage_available"))

    player_id = st.session_state.player_id
    # Read the flag at once, so an early return below cannot leave it set.
    action_applied = st.session_state.pop("action_applied", False)
    if not st.session_state.browser_storage_available:
        st.warning("Your browser blocks local storage. Progress may be lost after a server restart.")

    api_key = ably_api_key()
    if "room" in st.session_state or st.query_params.get("room"):
        st.session_state.setdefault("mode", "Multiplayer")
    mode = st.radio("Mode", ["Single player", "Multiplayer"], key="mode", horizontal=True,
                    label_visibility="collapsed")
    if mode == "Single player" and "room" in st.session_state:
        leave_room()
    room = st.session_state.get("room") if mode == "Multiplayer" else None
    if mode == "Multiplayer":
        if multiplayer_lobby(player_id, api_key):
            return
        room = st.session_state.room
    # Each room has its own save, so multiplayer never touches single player.
    game_id = mp.save_id(player_id, room) if room else player_id

    saved = read_progress(game_id, None if room else st.session_state.browser_backup)
    room_state = None
    if room:
        if saved is None or not st.session_state.playing:
            enter_room(player_id, room)
            st.rerun()
        with closing(connect_db(DB_PATH)) as conn:
            room_state = shared_ship.room_info(conn, room)
        if room_state["generation"] != st.session_state.get("room_generation"):
            # The partner restarted the ship: start again in the cell with them.
            st.session_state.room_generation = room_state["generation"]
            begin_play(saved, room_state["epoch_ms"])
        new_clicked = continue_clicked = False
    else:
        start_col, continue_col, _ = st.columns([1, 1, 3])
        with start_col:
            new_clicked = st.button("New Game", use_container_width=True, type="primary")
        with continue_col:
            continue_clicked = st.button("Continue", use_container_width=True, disabled=saved is None)
    if new_clicked:
        if saved is None:
            with closing(connect_db(DB_PATH)) as conn:
                new_game(conn, game_id)
            begin_play(show_intro=True)
        else:
            st.session_state.confirm_new = True
        st.rerun()
    if continue_clicked and saved is not None:
        begin_play(saved)
        st.rerun()

    if st.session_state.confirm_new:
        st.warning("A saved game exists. Delete your progress and start again?")
        yes_col, no_col, _ = st.columns([1, 1, 3])
        with yes_col:
            if st.button("Confirm New Game", use_container_width=True):
                with closing(connect_db(DB_PATH)) as conn:
                    new_game(conn, game_id)
                begin_play(show_intro=True)
                st.rerun()
        with no_col:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_new = False
                st.rerun()
        if not room:
            sync_browser_backup(player_id, saved)
        return

    if not st.session_state.playing or saved is None:
        if saved is None:
            st.info("No saved progress yet. Choose New Game to start in the cell.")
        else:
            st.info("Your saved game is ready. Choose Continue to return to the ship.")
        st.caption("Each browser has its own game. Your progress is saved in this browser.")
        st.markdown("**Controls:** A/D or ←/→ walk · W/↑ climb · ↓ descend · E steal/take/ambush · F inspect/use/hide · I inventory · L lamp · R shoot · Space crouch/stand")
        sync_browser_backup(player_id, saved)
        return

    bright_view = st.toggle("Brighter view", key="bright_view", help="Brighten the ship for better visibility.")

    progress = story_progress(saved)
    data = {**asdict(saved),
        "story": progress,
        "journal_hints": journal_hints(saved, int(time.time() * 1000)),
        "documents": DOCUMENTS,
        "endings": ENDINGS,
        "rescue_epilogue": FINALE_RESCUE_EPILOGUE,
        "finale": finale.public(saved),
        "roles": ROLES,
        "run_id": st.session_state.run_id,
        "intro": st.session_state.get("intro_run_id") == st.session_state.run_id,
        "revision": BACKEND_REVISION,
        "position": asdict(saved.position),
        "has_key": saved.has_key,
        "door_open": saved.door_open,
        "reached_kitchen": saved.reached_kitchen,
        "has_blue_key": saved.has_blue_key,
        "chest_open": saved.chest_open,
        "has_pistol": saved.has_pistol,
        "in_hammock": saved.in_hammock,
        "patrol_alive": saved.patrol_alive,
        "sleeper_alive": saved.sleeper_alive,
        "patrol_corpse_x": saved.patrol_corpse_x,
        "patrol_corpse_y": saved.patrol_corpse_y,
        "facing": saved.facing,
        "held_item": saved.held_item,
        "hidden_barrel": saved.hidden_barrel,
        "wardrobe_open": saved.wardrobe_open,
        "disguised": saved.disguised,
        "door_alerted": saved.door_alerted,
        "alert_started_ms": saved.alert_started_ms,
        "alert_until_ms": saved.alert_until_ms,
        "capture_phase": saved.capture_phase,
        "capture_paths": capture_paths(saved) if saved.capture_phase == "active" else None,
        "guard_started_ms": st.session_state.guard_started_ms,
        "guard_segments": [asdict(segment) for segment in GUARD_SEGMENTS],
        "guard_routes": {name:[asdict(segment) for segment in segments]
                         for name,segments in GUARD_ROUTES.items()},
        "bright_view": bright_view,
        "rules": {**MAP_CONFIG,"story_points":{**STORY_POINTS,"seal_chest":{**STORY_POINTS['seal_chest'],"item":'captain_uniform' if 'officer' in progress.get('voyage',{}).get('concealed',{}) else 'seal'}},"watch_path":route_points(Position("cabin",300),Position("chest_room",1320))},
        "multiplayer": {
            "room": room,
            "channel": mp.channel_name(room),
            "world_version": room_state["version"] if room_state else 0,
            "client_id": mp.save_id(player_id, "ably"),
            "sdk_url": mp.ABLY_SDK_URL,
            "token_request": mp.token_request(api_key, room, mp.save_id(player_id, "ably"), int(time.time() * 1000)),
        } if room and api_key else None,
        "feedback": {
            "seq": st.session_state.feedback_seq,
            "request_id": st.session_state.get("feedback_request_id", ""),
            "text": st.session_state.feedback_text,
            "accepted": st.session_state.feedback_accepted,
        },
    }
    result = game_component()(
        data=data,
        default={"position": {**asdict(saved.position),"run_id":st.session_state.run_id}},
        on_action_change=partial(apply_game_action, game_id),
        on_position_change=lambda: None,
        on_ably_change=lambda: None,
        on_sync_change=lambda: None,
        key=f"game_canvas_{game_id}",
        width="stretch",
        height=660,
    )

    # Any action was already applied by apply_game_action before this run, so
    # the canvas above shows its result.
    if not action_applied:
        position = position_from_payload(result.position)
        if position is not None and result.position.get("run_id")==st.session_state.run_id:
            with closing(connect_db(DB_PATH)) as conn:
                save_position(conn, position, game_id)

    current = read_progress(game_id)
    if not room:
        sync_browser_backup(player_id, current)
    if current is not None:
        with st.expander("Game details", expanded=False):
            inventory, doorway, place = st.columns(3)
            items = []
            if current.has_key: items.append("🗝️ Cell")
            if current.has_blue_key: items.append("🔵 Chest")
            if current.has_pistol: items.append("🔫 Pistol")
            if current.has_lamp: items.append("🏮 Lamp")
            if current.disguised and not story_progress(current).get("voyage",{}).get("captain_worn"): items.append("🥼 Uniform")
            for item in story_progress(current)["items"]:
                items.append(ITEMS[item]["icon"] + " " + ITEMS[item]["name"])
            inventory.caption("Inventory: " + (" · ".join(items) if items else "Empty"))
            doorway.caption("Cell door: " + ("Open" if current.door_open else "Locked"))
            names = {
                "cell": "Cell",
                "hold": "Hold",
                "lower_stair": "Lower stairs",
                "mid": "Middle deck",
                "cabin": "Cabin",
                "hammock": "Upper hammock",
                "dining": "Mess hall",
                "chest_room": "Chest room",
                "upper_deck": "Upper deck",
                "upper_stair": "Upper stairs",
                "kitchen": "Galley",
                "mast": "Mast", "mast_top": "Mast top",
            }
            names.update({zone: info[0].capitalize() for zone, info in MAP_CONFIG["rooms"].items()})
            place.caption("Location: " + names.get(current.position.zone, "Ship"))


if __name__ == "__main__":
    main()
