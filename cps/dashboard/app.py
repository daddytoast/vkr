"""
Office presence dashboard — Flask application.

Endpoints:
  GET /          — HTML dashboard
  GET /api/now   — current snapshot as JSON
  GET /api/history?hours=24 — aggregated history as JSON
  GET /stream    — Server-Sent Events for real-time push updates
"""

import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

import yaml
from flask import Flask, Response, jsonify, render_template, request

# allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collector.database import Database
from collector.mikrotik_client import MikrotikClient, PresenceCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────

_CONFIG_PATH = os.getenv("CPS_CONFIG", str(Path(__file__).resolve().parents[1] / "config.yml"))

with open(_CONFIG_PATH) as f:
    _cfg = yaml.safe_load(f)

_mk = _cfg["mikrotik"]
_col = _cfg.get("collector", {})
_db_cfg = _cfg.get("database", {})
_srv = _cfg.get("server", {})

# ── Shared state ───────────────────────────────────────────────────────────────

db = Database(_db_cfg.get("path", "/data/presence.db"))

client = MikrotikClient(
    host=_mk["host"],
    username=_mk["username"],
    password=_mk["password"],
    port=_mk.get("port", 443),
    verify_ssl=_mk.get("verify_ssl", False),
)

collector = PresenceCollector(
    client=client,
    db=db,
    poll_interval=_col.get("poll_interval", 30),
)

# ── Background collector thread ────────────────────────────────────────────────

_collector_thread = threading.Thread(target=collector.run_forever, daemon=True, name="collector")
_collector_thread.start()

# ── Flask app ─────────────────────────────────────────────────────────────────

app = Flask(__name__)


@app.get("/")
def index():
    snapshot = db.get_latest_snapshot() or {"ts": None, "client_count": 0, "clients": []}
    return render_template("index.html", snapshot=snapshot)


@app.get("/api/now")
def api_now():
    snapshot = db.get_latest_snapshot() or {"ts": None, "client_count": 0, "clients": []}
    return jsonify(snapshot)


@app.get("/api/history")
def api_history():
    hours = min(int(request.args.get("hours", 24)), 168)
    return jsonify(db.get_history(hours))


@app.get("/stream")
def stream():
    """SSE endpoint — pushes a new snapshot every 30 s."""

    def event_generator():
        last_ts = None
        while True:
            snapshot = db.get_latest_snapshot()
            if snapshot and snapshot["ts"] != last_ts:
                last_ts = snapshot["ts"]
                data = json.dumps(snapshot)
                yield f"data: {data}\n\n"
            time.sleep(5)

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    app.run(
        host=_srv.get("host", "0.0.0.0"),
        port=_srv.get("port", 8080),
        debug=_srv.get("debug", False),
    )