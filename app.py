"""
Docker Healthcheck Dashboard — Flask API + SPA
Muestra el estado de todos los containers Docker del VPS en tiempo real.
Usa subprocess (sin SDK de Docker) — compatible con cualquier entorno.
"""

import json
import os
import subprocess
import time
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__, static_folder="public")

# ── Configuración ────────────────────────────────────────────────────────────

API_TOKEN = os.getenv("DASHBOARD_TOKEN", "")  # vacío = sin auth
PORT = int(os.getenv("PORT", 5050))
REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", 10))
CACHE_TTL = int(os.getenv("CACHE_TTL", 5))

# ── Cache simple ──────────────────────────────────────────────────────────────

_cache: dict = {}


def cached(ttl: int):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = fn.__name__
            now = time.time()
            if key in _cache and now - _cache[key]["ts"] < ttl:
                return _cache[key]["data"]
            result = fn(*args, **kwargs)
            _cache[key] = {"data": result, "ts": now}
            return result
        return wrapper
    return decorator


# ── Auth opcional ─────────────────────────────────────────────────────────────

def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not API_TOKEN:
            return f(*args, **kwargs)
        token = request.headers.get("X-Token", "") or request.args.get("token", "")
        if token != API_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Docker helpers ────────────────────────────────────────────────────────────

def run_docker(cmd: list) -> tuple:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return "", 124
    except FileNotFoundError:
        return "", 127


@cached(CACHE_TTL)
def get_containers() -> list:
    fmt = (
        '{"id":"{{.ID}}",'
        '"name":"{{.Names}}",'
        '"image":"{{.Image}}",'
        '"status":"{{.Status}}",'
        '"state":"{{.State}}",'
        '"ports":"{{.Ports}}",'
        '"created":"{{.CreatedAt}}"}'
    )
    out, rc = run_docker(["docker", "ps", "-a", f"--format={fmt}"])
    if rc != 0:
        return []

    containers = []
    for line in out.splitlines():
        try:
            c = json.loads(line)
            c["healthy"] = c["state"].lower() in ("running", "restarting")
            c["state_icon"] = {
                "running":    "🟢",
                "exited":     "🔴",
                "paused":     "🟡",
                "restarting": "🔄",
                "dead":       "💀",
                "created":    "⚪",
            }.get(c["state"].lower(), "❓")
            containers.append(c)
        except json.JSONDecodeError:
            continue

    return containers


@cached(CACHE_TTL)
def get_system_info() -> dict:
    out, rc = run_docker(["docker", "info", "--format", "{{json .}}"])
    if rc != 0:
        return {}
    try:
        info = json.loads(out)
        return {
            "containers_running": info.get("ContainersRunning", 0),
            "containers_stopped": info.get("ContainersStopped", 0),
            "containers_paused":  info.get("ContainersPaused", 0),
            "images":             info.get("Images", 0),
            "server_version":     info.get("ServerVersion", "unknown"),
            "memory_total":       info.get("MemTotal", 0),
            "cpus":               info.get("NCPU", 0),
            "swarm_active":       info.get("Swarm", {}).get("LocalNodeState") == "active",
        }
    except json.JSONDecodeError:
        return {}


@cached(CACHE_TTL)
def get_disk_usage() -> dict:
    out, rc = run_docker(["docker", "system", "df", "--format", "{{json .}}"])
    if rc != 0:
        return {}
    result = {}
    for line in out.splitlines():
        try:
            item = json.loads(line)
            t = item.get("Type", "").lower()
            result[t] = {
                "total":       item.get("TotalCount", 0),
                "size":        item.get("Size", "0B"),
                "reclaimable": item.get("Reclaimable", "0B"),
            }
        except json.JSONDecodeError:
            continue
    return result


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    _, rc = run_docker(["docker", "info"])
    docker_ok = rc == 0
    return jsonify({
        "status": "ok",
        "docker": "ok" if docker_ok else "error",
        "timestamp": datetime.now().isoformat(),
    }), 200 if docker_ok else 503


@app.route("/api/containers")
@require_token
def api_containers():
    containers = get_containers()
    return jsonify({
        "containers": containers,
        "total": len(containers),
        "running": sum(1 for c in containers if c["state"].lower() == "running"),
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/system")
@require_token
def api_system():
    return jsonify({
        "system": get_system_info(),
        "disk":   get_disk_usage(),
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/container/<container_id>/logs")
@require_token
def api_container_logs(container_id: str):
    safe_id = "".join(c for c in container_id if c.isalnum() or c in "-_.")
    if safe_id != container_id:
        return jsonify({"error": "Invalid container ID"}), 400
    lines = min(int(request.args.get("lines", 50)), 500)
    out, _ = run_docker(["docker", "logs", "--tail", str(lines), safe_id])
    return jsonify({"logs": out.splitlines(), "container_id": safe_id})


@app.route("/api/container/<container_id>/action", methods=["POST"])
@require_token
def api_container_action(container_id: str):
    safe_id = "".join(c for c in container_id if c.isalnum() or c in "-_.")
    if safe_id != container_id:
        return jsonify({"error": "Invalid container ID"}), 400

    data = request.get_json(silent=True) or {}
    action = data.get("action", "")
    if action not in ("start", "stop", "restart"):
        return jsonify({"error": "Action must be start|stop|restart"}), 400

    out, rc = run_docker(["docker", action, safe_id])
    _cache.clear()
    return jsonify({
        "action": action,
        "container": safe_id,
        "success": rc == 0,
        "output": out,
    })


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("public", "index.html")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
