#!/usr/bin/env python3
"""Fetch the NFL schedule/scores (ESPN) and game-winner odds (Polymarket) and
update docs/data/games.json. Standard library only. Run by GitHub Actions."""
import json, re, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "docs" / "data"
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
GAMMA = "https://gamma-api.polymarket.com/events"


def get(url, **params):
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "nfl-pricer/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def espn_games():
    today = datetime.now(timezone.utc).date()
    rng = f"{today - timedelta(days=4):%Y%m%d}-{today + timedelta(days=21):%Y%m%d}"
    events = get(ESPN, dates=rng, limit="300").get("events", []) or get(ESPN).get("events", [])
    out = []
    for e in events:
        c = e["competitions"][0]
        t = {x["homeAway"]: x for x in c["competitors"]}
        if "home" not in t or "away" not in t:
            continue

        def side(x):
            tm, sc = x["team"], str(x.get("score", ""))
            return {"abbr": tm.get("abbreviation"), "name": tm.get("displayName"),
                    "mascot": tm.get("name"), "score": int(sc) if sc.isdigit() else None}
        st = e["status"]["type"]
        out.append({"id": str(e["id"]), "week": (e.get("week") or {}).get("number"), "start": e["date"],
                    "state": st["state"], "detail": st.get("shortDetail"),
                    "home": side(t["home"]), "away": side(t["away"]), "_odds": c.get("odds")})
    return out


def ml_prob(o):  # American moneyline -> implied probability
    o = float(o)
    return 100 / (o + 100) if o > 0 else -o / (-o + 100)


def espn_prob(g):  # fallback if Polymarket has nothing for this game
    try:
        o = g["_odds"][0]
        h, a = ml_prob(o["homeTeamOdds"]["moneyLine"]), ml_prob(o["awayTeamOdds"]["moneyLine"])
        return h / (h + a)
    except Exception:
        return None


def poly_events():
    out, off = [], 0
    while off < 600:
        page = get(GAMMA, tag_slug="nfl", active="true", closed="false", limit="100", offset=str(off))
        out += page
        if len(page) < 100:
            break
        off += 100
    return out


def loads(x):
    return json.loads(x) if isinstance(x, str) else x


def poly_prob(g, events):
    """P(home wins) from the Polymarket moneyline market for this game, or None."""
    h, a = g["home"]["mascot"].lower(), g["away"]["mascot"].lower()
    gdate = datetime.fromisoformat(g["start"].replace("Z", "+00:00")).date()
    for ev in events:
        for m in ev.get("markets", []):
            q = (m.get("question", "") + " " + m.get("groupItemTitle", "")).lower()
            if m.get("sportsMarketType", "moneyline") != "moneyline" or any(w in q for w in ("spread", "o/u", "total")):
                continue
            try:
                outs, px = [o.lower() for o in loads(m["outcomes"])], [float(x) for x in loads(m["outcomePrices"])]
            except Exception:
                continue
            if len(outs) != 2 or len(px) != 2:
                continue
            hi = next((i for i, o in enumerate(outs) if h in o), None)
            ai = next((i for i, o in enumerate(outs) if a in o), None)
            if hi is None or ai is None or hi == ai:
                continue
            d = re.search(r"\d{4}-\d{2}-\d{2}", ev.get("slug", "") + " " + str(m.get("gameStartTime", "")))
            if d and abs((datetime.fromisoformat(d.group()).date() - gdate).days) > 1:
                continue
            tot = px[hi] + px[ai]
            if tot > 0:
                return px[hi] / tot
    return None


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    f = DATA / "games.json"
    db = json.loads(f.read_text()) if f.exists() else {}
    try:
        events = poly_events()
    except Exception as e:
        print("Polymarket fetch failed, using ESPN odds only:", e)
        events = []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for g in espn_games():
        r = db.setdefault(g["id"], {"history": [], "p_home": None, "source": None})
        r.update({k: g[k] for k in ("id", "week", "start", "state", "detail", "home", "away")})
        if g["state"] == "pre":  # odds are only updated before kickoff, then locked
            p, src = poly_prob(g, events), "Polymarket"
            if p is None:
                p, src = espn_prob(g), "ESPN odds"
            if p is not None:
                r["p_home"], r["source"] = round(p, 4), src
                if not r["history"] or abs(r["history"][-1][1] - p) >= 0.001:
                    r["history"] = (r["history"] + [[now, round(p, 4)]])[-300:]
    f.write_text(json.dumps(db, indent=1, sort_keys=True))
    (DATA / "meta.json").write_text(json.dumps({"updated": now}))
    print(f"Saved {len(db)} games.")


if __name__ == "__main__":
    main()
