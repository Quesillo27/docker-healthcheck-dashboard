#!/usr/bin/env python3
"""Docker Healthcheck Dashboard — Monitor de containers en tiempo real."""

import logging
import functools
from datetime import datetime, timezone
from flask import Flask, jsonify, render_template, request, abort

import config
from services.docker_service import (
    get_containers,
    get_system_info,
    get_container_logs,
    container_action,
    is_docker_accessible,
    get_hostname,
)

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


# ── Auth ──────────────────────────────────────────────────────────────────────

def _check_token() -> bool:
    if not config.DASHBOARD_TOKEN:
        return True
    token = (
        request.headers.get('X-Token')
        or request.headers.get('Authorization', '').removeprefix('Bearer ')
        or request.args.get('token', '')
    )
    return token == config.DASHBOARD_TOKEN


def require_auth(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        if not _check_token():
            return jsonify({'error': 'Unauthorized'}), 401
        return fn(*args, **kwargs)
    return wrapper


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template(
        'dashboard.html',
        refresh_interval=config.REFRESH_INTERVAL,
    )


@app.route('/api/containers')
@require_auth
def api_containers():
    containers = get_containers()
    running = sum(1 for c in containers if c['state'] == 'running')
    stopped = sum(1 for c in containers if c['state'] != 'running')
    return jsonify({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'host': get_hostname(),
        'containers': containers,
        'total': len(containers),
        'running': running,
        'stopped': stopped,
    })


@app.route('/api/system')
@require_auth
def api_system():
    info = get_system_info()
    if not info:
        return jsonify({'error': 'Docker not accessible'}), 503
    return jsonify({
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'system': info,
    })


@app.route('/api/container/<container_id>/logs')
@require_auth
def api_container_logs(container_id):
    try:
        lines = int(request.args.get('lines', 100))
    except ValueError:
        return jsonify({'error': 'lines must be an integer'}), 400
    try:
        log_lines = get_container_logs(container_id, lines)
        return jsonify({
            'container_id': container_id,
            'lines': len(log_lines),
            'logs': log_lines,
        })
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 503


@app.route('/api/container/<container_id>/action', methods=['POST'])
@require_auth
def api_container_action(container_id):
    body = request.get_json(silent=True) or {}
    action = body.get('action', '')
    try:
        result = container_action(container_id, action)
        status = 200 if result['success'] else 500
        return jsonify(result), status
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({'error': str(exc)}), 503


@app.route('/health')
def health():
    if is_docker_accessible():
        return jsonify({
            'status': 'ok',
            'docker': 'accessible',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    return jsonify({
        'status': 'error',
        'docker': 'not accessible',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }), 503


if __name__ == '__main__':
    logger.info("Docker Healthcheck Dashboard en http://0.0.0.0:%d", config.PORT)
    app.run(host='0.0.0.0', port=config.PORT, debug=False)
