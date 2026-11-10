"""Multiplayer rooms: codes, separate saves, Ably tokens and live position sharing."""
import base64
import hashlib
import hmac
import json
from dataclasses import asdict, replace

import pytest

import multiplayer as mp
from logic import MAP_CONFIG, Position, initial_state, story_progress
from test_canvas_rules import canvas, NODE

KEY = "appId.keyId:c2VjcmV0LXZhbHVl"


def test_room_codes_are_short_unambiguous_and_validated():
    codes = {mp.new_room_code() for _ in range(200)}
    assert len(codes) > 190
    assert all(len(c) == mp.ROOM_LENGTH and set(c) <= set(mp.ROOM_ALPHABET) for c in codes)
    assert not set("01IO") & set(mp.ROOM_ALPHABET)
    assert mp.normalize_room(" abc234 ") == "ABC234"
    for bad in ("ABC23", "ABC2345", "ABC23O", "", None, 123, "ABC 23"):
        assert mp.normalize_room(bad) is None


def test_each_room_has_its_own_save_apart_from_single_player():
    player = "a" * 32
    one, two = mp.save_id(player, "ABC234"), mp.save_id(player, "XYZ789")
    assert len(one) == 32 and int(one, 16) >= 0
    assert len({player, one, two, mp.save_id("b" * 32, "ABC234")}) == 4
    assert mp.save_id(player, "ABC234") == one


def test_token_request_is_signed_and_limited_to_the_room():
    t = mp.token_request(KEY, "ABC234", "client-1", 1_700_000_000_000, nonce="n1")
    assert t["keyName"] == "appId.keyId" and "c2VjcmV0" not in json.dumps(t)
    assert json.loads(t["capability"]) == {"tpt:room:ABC234": ["publish", "subscribe", "presence"]}
    assert t["clientId"] == "client-1" and t["ttl"] == mp.TOKEN_TTL_MS
    signed = "appId.keyId\n%d\n%s\nclient-1\n1700000000000\nn1\n" % (mp.TOKEN_TTL_MS, t["capability"])
    expected = base64.b64encode(hmac.new(b"c2VjcmV0LXZhbHVl", signed.encode(), hashlib.sha256).digest()).decode()
    assert t["mac"] == expected
    assert mp.token_request(KEY, "ABC234", "client-1", 1)["nonce"] != mp.token_request(KEY, "ABC234", "client-1", 1)["nonce"]


def test_api_keys_are_checked_before_use():
    assert mp.valid_api_key(KEY)
    for bad in (None, "", "no-colon", "a:b", "app.key", 42):
        assert not mp.valid_api_key(bad)


def test_the_sdk_is_pinned_to_an_exact_version():
    assert "@2.30.0/" in mp.ABLY_SDK_URL and mp.ABLY_SDK_URL.startswith("https://cdn.jsdelivr.net/npm/ably@")


def _client_data(**changes):
    s = replace(initial_state(), **changes)
    return {**asdict(s), 'story': story_progress(s), 'rules': MAP_CONFIG}


@pytest.mark.skipif(NODE is None, reason='Node runs the Canvas code')
def test_positions_are_sent_only_on_change_at_most_eight_a_second():
    sent = canvas(r'''(()=>{const out=[];
      const client={data:input.d,position:{zone:'cell',value:300},facing:'right'};
      rooms.set('k',{channel:{publish:(n,d)=>{out.push([n,d.x]);return Promise.resolve();}},status:'connected',lastSent:'',lastSentAt:0,forceSend:true});
      publishPosition(client,'k',1000);           // first send
      publishPosition(client,'k',1050);           // unchanged: nothing
      client.position={zone:'cell',value:310};
      publishPosition(client,'k',1100);           // changed but too soon
      publishPosition(client,'k',1130);           // changed, 130 ms later: send
      publishPosition(client,'k',3000);           // unchanged, before heartbeat
      publishPosition(client,'k',6200);           // heartbeat
      rooms.get('k').full=true;client.position={zone:'cell',value:330};
      publishPosition(client,'k',7000);           // a third player never sends
      return out;})()''', {'d': _client_data()})
    assert sent == [['pos', 300], ['pos', 310], ['pos', 310]]


@pytest.mark.skipif(NODE is None, reason='Node runs the Canvas code')
def test_hiding_and_disguise_reach_the_partner():
    snap = canvas(r'''[partnerSnapshot({data:input.hidden,position:{zone:'hold',value:710},facing:'left'}),
                      partnerSnapshot({data:input.plain,position:{zone:'cell',value:250},facing:'right'})]''',
                  {'hidden': _client_data(hidden_barrel='barrel_hold_a', disguised=True), 'plain': _client_data()})
    assert snap[0]['h'] and snap[0]['g'] and snap[0]['f'] == -1
    assert snap[1] == {'x': 250, 'y': 500, 'f': 1, 'h': False, 'c': False, 'g': False, 'cap': False, 'e': False}


def test_single_player_stays_unchanged_when_no_room_is_used():
    from pathlib import Path
    source = Path('app.py').read_text()
    assert 'game_id = mp.save_id(player_id, room) if room else player_id' in source
    assert '"multiplayer": {' in source and '} if room and api_key else None' in source
