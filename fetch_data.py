#!/usr/bin/env python3
"""Holt frische Daten fuer Jakobs Dashboard aus Notion und schreibt data.json.

Laeuft in der GitHub Action. Braucht env NOTION_TOKEN.
- Todos: Datenbank-Query (alle Zeilen ausser dem \u2699\ufe0f-Datenspeicher)
- Mails/Termine: JSON-Codeblock im Eintrag "\u2699\ufe0f dashboard-data"
"""
import json, os, urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DB_ID = "5163053d-7ff9-485c-8e73-95d0ec9d5389"
BUS_PAGE = "3aabc82e815a81029b60cc3df98e037a"
API = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": "Bearer " + os.environ["NOTION_TOKEN"],
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def req(path, method="GET", body=None):
    r = urllib.request.Request(API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None, headers=HEADERS)
    return json.load(urllib.request.urlopen(r))

def prop_text(p):
    return "".join(t.get("plain_text", "") for t in (p.get("title") or p.get("rich_text") or []))

def main():
    rows, cursor = [], None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        data = req(f"/databases/{DB_ID}/query", "POST", body)
        for page in data["results"]:
            props = page["properties"]
            name = prop_text(props.get("Name", {}))
            if not name or name.startswith("\u2699"):
                continue
            sel = lambda k: (props.get(k, {}).get("select") or {}).get("name")
            date = lambda k: (props.get(k, {}).get("date") or {}).get("start")
            rows.append({
                "id": page["id"].replace("-", ""),
                "name": name,
                "prio": sel("Priorit\u00e4t"),
                "abt": sel("Abteilung"),
                "punkte": props.get("Punkte", {}).get("number"),
                "faellig": (date("F\u00e4llig") or "")[:10] or None,
                "done": bool(props.get("Erledigt", {}).get("checkbox")),
                "doneAt": date("Erledigt am"),
                "_created": page.get("created_time", ""),
            })
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    rows.sort(key=lambda r: ((r["prio"] != "Hoch"), r["_created"]))
    for r in rows:
        r.pop("_created", None)

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = [r for r in rows if r["done"] and r["doneAt"] and r["doneAt"][:10] >= cutoff]
    punkte7 = sum(r["punkte"] or 0 for r in recent)

    bus = {"mailTotal": "~?", "mails": [], "events": []}
    try:
        blocks = req(f"/blocks/{BUS_PAGE}/children?page_size=100")
        for b in blocks.get("results", []):
            if b.get("type") == "code":
                txt = "".join(t.get("plain_text", "") for t in b["code"].get("rich_text", []))
                bus = json.loads(txt)
                break
    except Exception as e:
        print("Bus-Seite nicht lesbar:", e)

    out = {
        "stand": datetime.now(ZoneInfo("Europe/Vienna")).strftime("%d.%m.%Y, %H:%M Uhr"),
        "punkte7": punkte7,
        "done7": len(recent),
        "mailTotal": bus.get("mailTotal", "~?"),
        "rows": rows,
        "mails": bus.get("mails", []),
        "events": bus.get("events", []),
    }
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("data.json:", len(rows), "Todos,", len(out["mails"]), "Mails,", len(out["events"]), "Termine")

if __name__ == "__main__":
    main()
