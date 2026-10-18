#!/usr/bin/env python3
"""A local fixture server for the alerts page (`/alerts`): the page and its design files exactly as
the application serves them (build stamp written in, the sign-in content security policy on the
page), and a fake `/api/alerts/*` held in memory. Standard library only; for the browser check.

Every value it holds is fictional (the portfolio, the recipients, the alert's figures): no company
row, plant mapping or real contract appears here. The fake answers in the contract's shapes
(docs/work/alerts-portfolio-2026-10-17), so the page can be driven end to end without Firebase,
BigQuery or SMTP.

    /usr/bin/python3 tests/fixtures/grid/alerts/serve.py [--port 8791] [--signed-in] [--seed]
        [--hostile] [--fail] [--no-sign-in] [--no-checks] [--password] [--import]

`--seed` starts with one fictional portfolio version, one rules version (with a recipient) and one
alert in the history, so the not-signed-in view can be checked for what it must not show.
`--hostile` answers a check with an alert whose text fields carry markup and whose event link is a
script URL, for the page's text-only rule. `--fail` answers every `/api/alerts/*` call but the
client config with a 500, for the page's failure paths. `--no-sign-in` answers the client config with
the backend's 503 refusal (demo mode: Google sign-in not configured). `--no-checks` reports
`checks_available: false`. A check on Mindanao (CMIN) finishes with no alert (the price under the rule).

The shapes follow the backend as built (src/alerts/routes.py, service.py): a check answers 202
`{status: "running", id}` and is read with `GET /api/alerts/runs/<id>` until `status` is "done";
alerts carry a 24-hex `key`, `family_label`, `threshold_text` and `event_url` =
`https://grid-nowcast.web.app/alerts?alert=<key>`; refusals are `{code, message, field?, reason?}`;
not signed in, history estimates are `{"hidden": true}` and `emailed_to` is a count. Port 0 picks a free port; the server
prints `READY <port>` once it listens.

`GET /api/alerts/inbox` (ericka-desk E24) answers from three
SYNTHETIC alerts (INBOX_ALERTS) in the backend's shape; `/grid-data/<stamp>/` answers the shell
ticker's and the ask panel's files from SYNTHETIC values (GRID_DATA).

`--import` turns the portfolio import on (`import_available: true`) and answers
`GET /api/alerts/portfolio/draft` with a fictional draft (DRAFT below); without it that route answers
404 IMPORT_OFF, as the backend does with the switch off (docs/work/portfolio-import-2026-10-17).

`--password` serves a stand-in SDK that starts signed out and accepts one fictional email and password
account (judge@example.test / fixture-password, any other pair is refused with Firebase's
`auth/invalid-credential`); the fake then treats a request as signed in only when it carries that
account's token, so the password path is checked from sign-in to edit.
`--signed-in` makes the fake treat every request as a Google user (so the page's edit state can be
checked without a real sign-in); without it the fake answers as for a visitor who is not signed in,
whatever the page sends. The Firebase client config it returns is a placeholder, so the page's real
sign-in button stays inert here.
"""
import argparse
import ast
import hashlib
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
GRID = ROOT / "src" / "grid"
STAMP = "0123456789abcdef"


def constant(name):
    """A string constant of src/api/__init__.py, read from its source (no import, no FastAPI)."""
    tree = ast.parse((ROOT / "src" / "api" / "__init__.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            value = node.value
            if isinstance(value, ast.Call) and getattr(value.func, "id", None) == "frozenset":
                return frozenset(ast.literal_eval(value.args[0]))
            return ast.literal_eval(value)
    raise SystemExit(f"{name} not found")


SIGN_IN_POLICY = constant("SIGN_IN_POLICY")
DEFAULT_POLICY = constant("CONTENT_SECURITY_POLICY")
FILES = constant("GRID_FILES")
TYPES = {".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".woff2": "font/woff2",
         ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon",
         ".webmanifest": "application/manifest+json"}
# InGRID brand: the icons and manifest every page's head links, served at the root from the design
# tree as the application's own routes serve them (src/api BRAND_ROOT_FILES).
BRAND = ("favicon.ico", "favicon.svg", "apple-touch-icon.png", "icon-192.png", "icon-512.png",
         "icon-maskable-512.png", "site.webmanifest")

# The portfolio import's draft: fictional region totals in the backend's shape (src/alerts/draft.py).
DRAFT = {
    "kind": "portfolio-draft", "built_at": "2026-10-17T09:00:00Z",
    "window": {"first": "2026-09-09", "last": "2026-10-06", "days": 28, "intervals": 8064},
    "units": {"mq": "kWh", "bcq": "MWh", "stated_by": "fixture desk"},
    "regions": {"CVIS": {"demand_mw_by_hour": [40 + h for h in range(24)], "contracted_mw_by_hour": [15] * 24,
                         "intervals": 8064}},
    "left_out": {"bcq_nodes_without_meters": 2, "bcq_mw_without_meters": 3.25, "unmapped_nodes": 1,
                 "regions_missing_hours": ["CMIN"]},
    "quality": {"mq_empty": 0},
}

STATE = {
    "portfolio": [],
    "rules": [],
    "history": [],
}
EXAMPLE_ALERT = {
    "key": "0" * 24, "region": "CVIS", "interval_manila": "2026-09-21T13:40",
    "price_php_mwh": 20000, "threshold_text": "price at or above 15,000 PHP/MWh", "severity": "high",
    "likely_drivers": [
        {"family": "S", "family_label": "Supply", "score": 0.78, "why": "fictional: import share above its 28-day median"},
        {"family": "D", "family_label": "Demand", "score": 0.77, "why": "fictional: demand above its 28-day median"},
        {"family": "F", "family_label": "Fuel", "score": 0.47, "why": "fictional: fuel cost baseline"},
        {"family": "O", "family_label": "Outage", "score": 0.12, "why": "fictional: one unit out"}],
    "confidence": "Low: fictional fixture, 2 of 41 facts evidence-known",
    "relationship_trail": "Fixture unit (message) -> fixture plant -> Visayas -> price",
    "what_to_check": ["the fixture unit's return time", "link congestion", "demand against its median"],
    "source": "manual",
}
RUNS = {}

# SYNTHETIC grid data for the shell's ticker and the ask panel: two made-up notices, one made-up event
# and an empty views file, so every request the page makes is answered and the console stays clean.
GRID_DATA = {
    "advisories.json": [
        {"t": "2026-09-21T13:39:00", "id": "SYN-ADV-1", "grid": "CVIS", "kind": "trip", "text": "Synthetic unit tripped at 1334H"},
        {"t": "2026-09-21T16:12:00", "id": "SYN-ADV-2", "grid": "CVIS", "kind": "online", "text": "Synthetic unit back online"}],
    "events.json": [{"id": "syn-event", "t": "2026-09-21T13:39", "advisory": "SYN-ADV-1", "site": "SYN", "title": "Synthetic unit trip"}],
    "views/alerts.json": {"views": []},
    # replay-year: the bake's day-and-month index; the ticker reads the clock's month file.
    "replay.json": {"v": 1, "first": "2026-09-21T00:00", "last": "2026-09-21T23:55", "days": ["2026-09-21"],
                    "missing": [], "node_days": [], "months": ["2026-09"], "intervals": 288},
}
GRID_DATA["advisories/2026-09.json"] = GRID_DATA["advisories.json"]
# UX-4: the live strip reads the clock's day file. This fixture has no series: it answers null, which
# the shell reads as a day with no data (the strip then shows no prices), with no failed request.
GRID_DATA["days/2026-09-21.json"] = None

# The inbox (ericka-desk E24, E25) in the backend's shape (src/alerts/service.py inbox): SYNTHETIC
# alerts; one recorded cause groups two of them, the third has none on record.
INBOX_ALERTS = [
    {"key": "a" * 24, "source": "replay", "region": "CVIS", "region_label": "Visayas", "direction": "spike",
     "first": "2026-09-21T13:40", "last": "2026-09-21T14:05", "interval_manila": "2026-09-21T13:45", "intervals": 6,
     "price_php_mwh": 32000, "threshold_text": "price at or above 15,000 PHP/MWh", "severity": "extreme",
     "severity_reason": "at the offer cap (32,000 PHP/MWh)", "main_driver": "Synthetic unit trip (notice SYN-ADV-1 at 13:39)",
     "cause": {"kind": "event", "id": "syn-event", "title": "Synthetic unit trip", "advisory": "SYN-ADV-1",
               "known_at": "2026-09-21T13:39", "href": "/event/syn-event"},
     "facts": ["Reserve short 120 MW at 13:45 (synthetic)"], "href": "/event/syn-event",
     "next_step": "Open the event (Synthetic unit trip) and check its timeline against your position."},
    {"key": "b" * 24, "source": "replay", "region": "CVIS", "region_label": "Visayas", "direction": "spike",
     "first": "2026-09-21T15:00", "last": "2026-09-21T15:05", "interval_manila": "2026-09-21T15:00", "intervals": 2,
     "price_php_mwh": 18000, "threshold_text": "price at or above 15,000 PHP/MWh", "severity": "high",
     "severity_reason": "3.6 x usual", "main_driver": "Synthetic unit trip (notice SYN-ADV-1 at 13:39)",
     "cause": {"kind": "event", "id": "syn-event", "title": "Synthetic unit trip", "advisory": "SYN-ADV-1",
               "known_at": "2026-09-21T13:39", "href": "/event/syn-event"},
     "facts": [], "href": "/event/syn-event",
     "next_step": "Open the event (Synthetic unit trip) and check its timeline against your position."},
    {"key": "c" * 24, "source": "replay", "region": "CMIN", "region_label": "Mindanao", "direction": "collapse",
     "first": "2026-09-21T03:00", "last": "2026-09-21T03:00", "interval_manila": "2026-09-21T03:00", "intervals": 1,
     "price_php_mwh": -5, "threshold_text": "price at or below 0 PHP/MWh", "severity": "medium",
     "severity_reason": "at or below zero", "main_driver": "None on record: no recorded event explains this alert",
     "cause": None, "facts": [], "href": "/alert/" + "c" * 24,
     "next_step": "Open the alert to review the interval and the notices around it."},
]


def alert_key(region, interval, version):
    return hashlib.sha256(f"{region}|{interval}|{version}".encode()).hexdigest()[:24]


# With --signed-in the vendored SDK's two files are answered by this stand-in instead: a Firebase
# compat surface with one Google user already signed in, so the page's edit state can be driven
# without Google. Without --signed-in the real vendored files are served (and stay inert, since the
# client config above is a placeholder).
FIREBASE_STAND_IN = """(function () {
  if (window.firebase) return;
  const user = {email: 'analyst@example.test', isAnonymous: false, providerData: [{providerId: 'google.com'}],
    getIdToken: () => Promise.resolve('fixture-token')};
  let current = user; const watchers = [];
  const auth = {onAuthStateChanged(f) { watchers.push(f); setTimeout(() => f(current), 0); },
    signInWithPopup() { current = user; watchers.forEach((f) => f(current)); return Promise.resolve({user}); },
    signOut() { current = null; watchers.forEach((f) => f(null)); return Promise.resolve(); }};
  function GoogleAuthProvider() { this.setCustomParameters = () => {}; }
  const app = {auth: () => auth};
  window.firebase = {apps: [], initializeApp() { this.apps.push(app); return app; }, app: () => app,
    auth: Object.assign(() => auth, {GoogleAuthProvider})};
})();
"""


PASSWORD_TOKEN = "fixture-password-token"
PASSWORD_STAND_IN = """(function () {
  if (window.firebase) return;
  const user = {email: 'judge@example.test', isAnonymous: false, providerData: [{providerId: 'password'}],
    getIdToken: () => Promise.resolve('%s')};
  let current = null; const watchers = [];
  const auth = {onAuthStateChanged(f) { watchers.push(f); setTimeout(() => f(current), 0); },
    signInWithPopup() { return Promise.reject({code: 'auth/popup-blocked'}); },
    signInWithEmailAndPassword(email, password) {
      if (email !== 'judge@example.test' || password !== 'fixture-password') return Promise.reject({code: 'auth/invalid-credential', message: 'refused'});
      current = user; watchers.forEach((f) => f(current)); return Promise.resolve({user});
    },
    signOut() { current = null; watchers.forEach((f) => f(null)); return Promise.resolve(); }};
  function GoogleAuthProvider() { this.setCustomParameters = () => {}; }
  const app = {auth: () => auth};
  window.firebase = {apps: [], initializeApp() { this.apps.push(app); return app; }, app: () => app,
    auth: Object.assign(() => auth, {GoogleAuthProvider})};
})();
""" % PASSWORD_TOKEN


def impact(portfolio, alert):
    """The fixture's own figure, in the contract's formula, from the fictional portfolio only."""
    if not portfolio:
        return {"status": "Not available: no portfolio entered"}
    p = portfolio[-1]
    hour = int(alert["interval_manila"][11:13])
    demand = (p.get("regions", {}).get(alert["region"]) or {}).get("demand_mw_by_hour")
    if not demand:
        return {"status": "Not available: no demand entered for this region"}
    covered = sum(c["mw"] for c in p.get("contracts", []) if c["region"] == alert["region"] and hour in c["hours"])
    unhedged = max(0.0, demand[hour] - covered)
    php = unhedged * (alert["price_php_mwh"] - p["benchmark_php_mwh"]) / 12
    return {"php": round(php), "unhedged_mw": unhedged, "interval_hours": 1 / 12,
            "basis": f"Estimate from portfolio v{p['version']}, effective {p['effective_from']}"}


SEED_PORTFOLIO = {"version": 1, "effective_from": "2026-10-01", "note": "fixture", "benchmark_php_mwh": 6543,
                  "regions": {"CVIS": {"demand_mw_by_hour": [111] * 24}},
                  "contracts": [{"name": "Fixture Seed BCQ", "region": "CVIS", "mw": 44, "price_php_mwh": 5222,
                                 "hours": list(range(24)), "start": "2026-01-01", "end": "2026-12-31"}],
                  "saved_by": "seed@example.test", "saved_at": "2026-10-17T08:00:00Z"}
SEED_RULES = {"version": 1, "enabled": True, "threshold": {"mode": "absolute", "value": 15000},
              "regions": ["CVIS"], "min_severity": "high",
              "recipients": [{"email": "secret-recipient@example.test", "regions": ["CVIS"], "min_severity": "high"}],
              "saved_by": "seed@example.test", "saved_at": "2026-10-17T08:00:00Z"}
HOSTILE = '<img src=x onerror="window.__pwned=1"><script>window.__pwned=2</script>'


class Handler(BaseHTTPRequestHandler):
    signed_in = False
    hostile = False
    fail = False
    no_sign_in = False
    no_checks = False
    imported = False
    password = False

    def is_signed(self):
        if self.signed_in:
            return True
        return self.password and self.headers.get("Authorization") == "Bearer " + PASSWORD_TOKEN

    def account(self):
        return "judge@example.test" if (self.password and not self.signed_in) else "analyst@example.test"

    def log_message(self, *args):
        pass

    def send(self, status, body, ctype, policy=DEFAULT_POLICY):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", policy)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(data)

    def json(self, status, value):
        self.send(status, json.dumps(value), "application/json")

    def refuse(self, code, status, message, **extra):
        self.json(status, dict(extra, code=code, message=message))

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def config(self):
        p, r = STATE["portfolio"], STATE["rules"]
        versions = [{k: v[k] for k in ("version", "effective_from", "saved_by", "saved_at")} for v in p]
        if self.is_signed():
            return {"signed_in": True, "email": self.account(), "email_status": "configured", "checks_available": not self.no_checks,
                    "import_available": self.imported,
                    "portfolio": {"latest": p[-1], "versions": versions} if p else None,
                    "rules": r[-1] if r else None}
        rules = None
        if r:
            rules = {k: v for k, v in r[-1].items() if k != "recipients"}
            rules["recipients_count"] = len(r[-1]["recipients"])
        return {"signed_in": False, "email": None, "email_status": "configured", "checks_available": not self.no_checks,
                "import_available": self.imported,
                "portfolio": {"present": True, "version": p[-1]["version"], "effective_from": p[-1]["effective_from"]} if p else None,
                "rules": rules}

    def inbox(self, query):
        """The fake inbox: the clock, the view and sign-in as the backend applies them."""
        at, view = (query.get("at") or [None])[0], (query.get("view") or ["all"])[0]
        if view not in ("all", "high"):
            return self.refuse("INVALID_INPUT", 422, "view: one of all, high", field="view", reason="one of all, high")
        signed = self.is_signed()
        alerts = []
        for a in INBOX_ALERTS:
            if at and a["first"] > at:
                continue
            a = dict(a)
            fi = ({"php": 1234567.0 if a["key"] == "a" * 24 else 23456.0, "basis": "Estimate from portfolio v1 (synthetic)"}
                  if STATE["portfolio"] and a["region"] == "CVIS" else {"status": "Needs your portfolio"})
            a["financial_impact"] = fi if signed or "php" not in fi else {"hidden": True}
            if view == "high" and a["severity"] not in ("high", "extreme"):
                continue
            alerts.append(a)
        groups = []
        for a in alerts:
            cid = (a["cause"] or {}).get("id")
            g = next((g for g in groups if cid and g["id"] == "event:" + cid), None)
            if g is None:
                g = {"id": ("event:" + cid) if cid else "alert:" + a["key"], "cause": a["cause"], "alerts": [],
                     "severity": a["severity"], "regions": [a["region"]], "first": a["first"], "last": a["last"],
                     "next_step": a["next_step"], "financial_impact": a["financial_impact"]}
                groups.append(g)
            else:
                g["last"] = max(g["last"], a["last"])
                fi = g["financial_impact"]
                if "php" in fi and "php" in a["financial_impact"]:
                    g["financial_impact"] = dict(fi, php=fi["php"] + a["financial_impact"]["php"])
            g["alerts"].append(a)
        return self.json(200, {"at": at, "view": view, "signed_in": signed, "default_levels": not STATE["rules"],
                               "rules_version": STATE["rules"][-1]["version"] if STATE["rules"] else None,
                               "count": len(alerts), "groups": groups})

    def failing(self):
        """With --fail every alerts call but the client config answers 500."""
        if self.fail and self.path.startswith("/api/alerts/") and self.path != "/api/alerts/client-config":
            self.refuse("FIXTURE_FAILURE", 500, "fixture failure")
            return True
        return False

    def do_GET(self):
        path = self.path.split("#")[0].split("?")[0]
        if path in ("/api/agent/threads", "/api/agent/queue"):
            # DOCK-5: the dock asks for its threads and queue once signed in; this fixture has none.
            return self.json(200, {"threads": [], "items": []})
        if self.failing():
            return None
        pages = {"/alerts": "alerts.html", "/settings": "settings.html"}  # the list, and its settings
        if path.rstrip("/") in pages:
            page = (GRID / pages[path.rstrip("/")]).read_text(encoding="utf-8").replace("__NOWCAST_STAMP__", STAMP)
            return self.send(200, page, "text/html", SIGN_IN_POLICY)
        m = re.fullmatch(r"/grid/(?:%s/)?(.+)" % STAMP, path)
        if m:
            name = m.group(1)
            if (self.signed_in or self.password) and name in ("firebase-app-compat.js", "firebase-auth-compat.js"):
                stand_in = FIREBASE_STAND_IN if self.signed_in else PASSWORD_STAND_IN
                return self.send(200, stand_in if name == "firebase-app-compat.js" else "", "text/javascript")
            allowed = name in FILES or re.fullmatch(r"fonts/[a-z0-9][a-z0-9._-]*\.woff2", name)
            f = GRID / name
            if allowed and f.is_file():
                return self.send(200, f.read_bytes(), TYPES.get(f.suffix, "application/octet-stream"))
            return self.send(404, "not found", "text/plain")
        if path.lstrip("/") in BRAND:
            f = GRID / path.lstrip("/")
            return self.send(200, f.read_bytes(), TYPES[f.suffix])
        if path == "/api/alerts/client-config":
            if self.no_sign_in:
                return self.refuse("SIGN_IN_UNAVAILABLE", 503, "Sign-in is not configured here.")
            return self.json(200, {"apiKey": "fixture-not-a-key", "authDomain": "fixture.firebaseapp.com", "projectId": "fixture"})
        if path == "/api/alerts/config":
            return self.json(200, self.config())
        if path == "/api/alerts/inbox":
            from urllib.parse import parse_qs
            return self.inbox(parse_qs(self.path.split("?", 1)[1] if "?" in self.path else ""))
        m = re.fullmatch(r"/grid-data/%s/(.+)" % STAMP, path)
        if m and m.group(1) in GRID_DATA:
            return self.json(200, GRID_DATA[m.group(1)])
        if path == "/api/alerts/portfolio/draft":
            if not self.is_signed():
                return self.refuse("SIGN_IN_REQUIRED", 401, "Sign in to do this.")
            if not self.imported:
                return self.refuse("IMPORT_OFF", 404, "The portfolio import is switched off on this server.")
            return self.json(200, DRAFT)
        if path == "/api/alerts/history":
            items = STATE["history"][-50:][::-1]
            if not self.is_signed():
                items = [dict(a, financial_impact={"hidden": True} if "php" in (a.get("financial_impact") or {})
                              else a.get("financial_impact"), emailed_to=len(a.get("emailed_to") or [])) for a in items]
            return self.json(200, {"alerts": items})
        if path.startswith("/api/alerts/runs/"):
            if not self.is_signed():
                return self.refuse("SIGN_IN_REQUIRED", 401, "Sign in to do this.")
            run = RUNS.get(path.rsplit("/", 1)[1])
            if run is None:
                return self.refuse("NOT_FOUND", 404, "Not found.")
            run["polls"] += 1
            if run["polls"] < run["polls_needed"]:
                return self.json(200, {"id": run["id"], "status": "running", "alerts": [], "checked": 0})
            return self.json(200, run["done"])
        # An empty body: a page script that never reads a 404's body (ask.js's views probe) would
        # otherwise keep the request pending in Chrome, and `networkidle0` would never come.
        return self.send(404, b"", "text/plain")

    def do_PUT(self):
        if self.failing():
            return None
        if not self.is_signed():
            return self.refuse("SIGN_IN_REQUIRED", 401, "Sign in to do this.")
        if self.path == "/api/alerts/portfolio":
            p = self.body()
            if p.get("note") == "server-reject":
                return self.refuse("INVALID_INPUT", 422, "benchmark_php_mwh: fixture refusal",
                                   field="benchmark_php_mwh", reason="fixture refusal")
            p.update(version=len(STATE["portfolio"]) + 1, saved_by=self.account(), saved_at="2026-10-17T09:00:00Z")
            STATE["portfolio"].append(p)
            return self.json(200, {"version": p["version"]})
        if self.path == "/api/alerts/rules":
            r = self.body(); r.update(version=len(STATE["rules"]) + 1, saved_by=self.account(), saved_at="2026-10-17T09:00:00Z")
            STATE["rules"].append(r)
            return self.json(200, {"version": r["version"]})
        return self.send(404, "not found", "text/plain")

    def do_POST(self):
        if self.path in ("/api/agent/session", "/api/agent/session/end"):
            # DOCK-5: the page posts the sign-in to the shared session; this fixture keeps none.
            # The body is read so the connection closes cleanly.
            self.body()
            return self.send(204, b"", "text/plain")
        if self.failing():
            return None
        if not self.is_signed():
            return self.refuse("SIGN_IN_REQUIRED", 401, "Sign in to do this.")
        if self.path == "/api/alerts/test-email":
            r = STATE["rules"][-1] if STATE["rules"] else {"recipients": []}
            return self.json(200, {"sent_to": [x["email"] for x in r["recipients"]]})
        if self.path == "/api/alerts/run":
            b = self.body()
            r = STATE["rules"][-1] if STATE["rules"] else None
            region, interval = b.get("region") or "CVIS", b.get("interval_manila") or "2026-09-21T13:40"
            if region == "CMIN":
                run_id = hashlib.sha256(f"run|{len(RUNS)}|quiet".encode()).hexdigest()[:32]
                done = {"id": run_id, "status": "done", "checked": 1, "alerts": [], "emailed": 0,
                        "bytes_billed": 1_000_000, "notes": [],
                        "candidates": [{"region": region, "interval_manila": interval, "price": 3000, "crossed": False,
                                        "threshold_text": "price at or above 15,000 PHP/MWh"}]}
                RUNS[run_id] = {"id": run_id, "polls": 0, "polls_needed": 1, "done": done}
                return self.json(202, {"id": run_id, "status": "running", "checked": 0, "alerts": []})
            key = alert_key(region, interval, r["version"] if r else 0)
            alert = dict(EXAMPLE_ALERT, key=key, region=region, interval_manila=interval,
                         event_url=f"https://grid-nowcast.web.app/alerts?alert={key}")
            alert["financial_impact"] = impact(STATE["portfolio"], alert)
            sent = [x["email"] for x in (r["recipients"] if r else []) if alert["region"] in x["regions"]] if b.get("send") else []
            alert["emailed_to"] = sent
            alert["sent_at"] = "2026-10-17T09:05:00Z" if sent else None
            if self.hostile:
                alert.update(event_url="javascript:window.__pwned=3", relationship_trail=HOSTILE,
                             confidence=HOSTILE, what_to_check=[HOSTILE], emailed_to=[HOSTILE],
                             likely_drivers=[{"family": HOSTILE, "score": 0.5, "why": HOSTILE}])
            STATE["history"].append(alert)
            run_id = hashlib.sha256(f"run|{len(RUNS)}|{key}".encode()).hexdigest()[:32]
            done = {"id": run_id, "status": "done", "checked": 1, "alerts": [alert], "emailed": len(sent),
                    "bytes_billed": 12_500_000, "notes": [],
                    "candidates": [{"region": region, "interval_manila": interval, "price": alert["price_php_mwh"],
                                    "crossed": True, "threshold_text": alert["threshold_text"], "alert_key": key}]}
            RUNS[run_id] = {"id": run_id, "polls": 0, "polls_needed": 2, "done": done}
            # The backend answers 202 when the driver card takes longer than its wait; the fixture always does.
            return self.json(202, {"id": run_id, "status": "running", "checked": 0, "alerts": []})
        return self.send(404, "not found", "text/plain")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8791)
    ap.add_argument("--signed-in", action="store_true")
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--hostile", action="store_true")
    ap.add_argument("--fail", action="store_true")
    ap.add_argument("--no-sign-in", action="store_true")
    ap.add_argument("--no-checks", action="store_true")
    ap.add_argument("--password", action="store_true")
    ap.add_argument("--import", dest="imported", action="store_true")
    args = ap.parse_args()
    Handler.imported = args.imported
    Handler.signed_in, Handler.hostile, Handler.fail = args.signed_in, args.hostile, args.fail
    Handler.no_sign_in, Handler.no_checks, Handler.password = args.no_sign_in, args.no_checks, args.password
    if args.seed:
        STATE["portfolio"].append(dict(SEED_PORTFOLIO))
        STATE["rules"].append(dict(SEED_RULES))
        key = alert_key("CVIS", "2026-09-21T13:40", 1)
        seeded = dict(EXAMPLE_ALERT, key=key, event_url=f"https://grid-nowcast.web.app/alerts?alert={key}",
                      emailed_to=["secret-recipient@example.test"], sent_at="2026-10-17T08:05:00Z")
        seeded["financial_impact"] = impact(STATE["portfolio"], seeded)
        STATE["history"].append(seeded)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"READY {server.server_address[1]}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
