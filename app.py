"""Streamlit entry point for Team Plot Twist: Escape from the pirate ship."""

from __future__ import annotations

import os
import re
import time
import uuid
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

import streamlit as st

from runtime_loader import load_backend
BACKEND_REVISION = load_backend(Path(__file__).resolve().parent)

from db import apply_action, claim_legacy, connect_db, load_game, new_game, restore_game, save_position
from logic import (GUARD_ROUTES, GUARD_SEGMENTS, MAP_CONFIG, Position, capture_paths,
                   state_from_backup, story_progress, game_now_ms, route_points)
from action_transport import handle_action
from content import DOCUMENTS, ENDINGS, ITEMS, ROLES, STORY_POINTS


ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TEAM_PLOT_TWIST_DB", ROOT / "data" / "team-progress.sqlite3"))
COMPONENT_DIR = ROOT / "game_component"

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


def begin_play(state=None):
    st.session_state.playing = True
    st.session_state.confirm_new = False
    st.session_state.run_id = uuid.uuid4().hex
    st.session_state.guard_started_ms = (game_now_ms(state, int(time.time() * 1000))
                                       if state is not None else int(time.time() * 1000))
    st.session_state.feedback_request_id = ""
    st.session_state.feedback_seq = 0
    st.session_state.feedback_text = ""
    st.session_state.feedback_accepted = False


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


def game_component():
    return cached_component(
        "team_plot_twist_canvas_game",
        (COMPONENT_DIR / "game.html").read_text(encoding="utf-8"),
        (COMPONENT_DIR / "game.css").read_text(encoding="utf-8"),
        (COMPONENT_DIR / "game.js").read_text(encoding="utf-8"),
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


def main():
    st.markdown(
        """
        <style>
        .block-container { max-width: 1160px; padding-top: 1.6rem; padding-bottom: 2rem; }
        h1 { margin-bottom: .1rem; }
        div[data-testid="stButton"] button { border-radius: .65rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.title("🏴‍☠️ Team Plot Twist: Escape from the pirate ship")
    st.caption("Four ways to freedom · Explore, find clues and choose your escape.")

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
    if not st.session_state.browser_storage_available:
        st.warning("Your browser blocks local storage. Progress may be lost after a server restart.")

    saved = read_progress(player_id, st.session_state.browser_backup)
    start_col, continue_col, spacer = st.columns([1, 1, 3])
    with start_col:
        new_clicked = st.button("New Game", use_container_width=True, type="primary")
    with continue_col:
        continue_clicked = st.button("Continue", use_container_width=True, disabled=saved is None)

    if new_clicked:
        if saved is None:
            with closing(connect_db(DB_PATH)) as conn:
                new_game(conn, player_id)
            begin_play()
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
                    new_game(conn, player_id)
                begin_play()
                st.rerun()
        with no_col:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_new = False
                st.rerun()
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

    st.markdown(
        "**Controls:** `A` / `D` or `←` / `→` walk · `W` / `↑` climb · `↓` descend · `E` steal/take/ambush · `F` inspect/use/hide · `I` inventory · `L` lamp · `J` journal · `B` whistle · `R` shoot · `T` bribe · `Space` crouch/stand"
    )
    st.caption("Controls work while the game is visible. Click the game area to focus it.")
    bright_view = st.toggle("Brighter view", key="bright_view", help="Brighten the ship for better visibility.")

    progress = story_progress(saved)
    data = {**asdict(saved),
        "story": progress,
        "documents": DOCUMENTS,
        "endings": ENDINGS,
        "roles": ROLES,
        "run_id": st.session_state.run_id,
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
        on_action_change=lambda: None,
        on_position_change=lambda: None,
        key=f"game_canvas_{player_id}",
        width="stretch",
        height=660,
    )

    # Process a discrete action before any location snapshot. A rejected action
    # must never cause a database write, even if both messages arrive together.
    action = result.action
    if isinstance(action, dict):
        cache=st.session_state.setdefault('action_acknowledgements',{})
        with closing(connect_db(DB_PATH)) as conn:
            outcome,request_id,duplicate=handle_action(conn,action,player_id,
                st.session_state.run_id,cache,int(time.time()*1000))
        if not duplicate and outcome.accepted and action.get("kind") in ("capture_complete","capture_tick","restart_game") and outcome.state.capture_phase=="none":
            begin_play()
            st.session_state.feedback_text=outcome.message
            st.session_state.feedback_seq=1
            st.session_state.feedback_accepted=True
            st.rerun()
        st.session_state.feedback_seq+=1
        st.session_state.feedback_request_id=request_id
        st.session_state.feedback_text=outcome.message
        st.session_state.feedback_accepted=outcome.accepted
        st.rerun()
    else:
        position = position_from_payload(result.position)
        if position is not None and result.position.get("run_id")==st.session_state.run_id:
            with closing(connect_db(DB_PATH)) as conn:
                save_position(conn, position, player_id)

    current = read_progress(player_id)
    sync_browser_backup(player_id, current)
    if current is not None:
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
