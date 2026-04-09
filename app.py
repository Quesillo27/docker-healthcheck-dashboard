#!/usr/bin/env python3
"""Docker Healthcheck Dashboard — Monitor de containers en tiempo real."""

import subprocess
import json
import os
from datetime import datetime
from flask import Flask, jsonify, render_template_string

app = Flask(__name__)
PORT = int(os.environ.get('PORT', 5050))

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Docker Healthcheck Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; min-height: 100vh; }
        header { background: #161b22; border-bottom: 1px solid #30363d; padding: 16px 24px; display: flex; align-items: center; gap: 12px; }
        header h1 { font-size: 1.25rem; font-weight: 600; }
        .badge { background: #21262d; border: 1px solid #30363d; border-radius: 12px; padding: 2px 10px; font-size: 0.75rem; }
        main { padding: 24px; max-width: 1200px; margin: 0 auto; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .stat-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
        .stat-card .value { font-size: 2rem; font-weight: 700; }
        .stat-card .label { font-size: 0.8rem; color: #8b949e; margin-top: 4px; }
        .running { color: #3fb950; }
        .stopped { color: #f85149; }
        .paused { color: #d29922; }
        table { width: 100%; border-collapse: collapse; background: #161b22; border: 1px solid #30363d; border-radius: 8px; overflow: hidden; }
        th { background: #21262d; padding: 12px 16px; text-align: left; font-size: 0.8rem; text-transform: uppercase; color: #8b949e; }
        td { padding: 12px 16px; border-top: 1px solid #30363d; font-size: 0.875rem; }
        tr:hover td { background: #21262d; }
        .status-badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 500; }
        .status-running { background: #1a4a2e; color: #3fb950; border: 1px solid #2ea043; }
        .status-exited, .status-stopped { background: #3d1a1a; color: #f85149; border: 1px solid #da3633; }
        .status-paused { background: #3d2e00; color: #d29922; border: 1px solid #9e6a03; }
        .status-other { background: #21262d; color: #8b949e; border: 1px solid #30363d; }
        .refresh-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .last-update { font-size: 0.8rem; color: #8b949e; }
        button { background: #21262d; color: #c9d1d9; border: 1px solid #30363d; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.875rem; }
        button:hover { background: #30363d; }
        #error { background: #3d1a1a; border: 1px solid #da3633; color: #f85149; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; display: none; }
    </style>
</head>
<body>
    <header>
        <span>[D]</span>
        <h1>Docker Healthcheck Dashboard</h1>
        <span class="badge" id="host">cargando...</span>
    </header>
    <main>
        <div class="stats">
            <div class="stat-card"><div class="value running" id="count-running">-</div><div class="label">Running</div></div>
            <div class="stat-card"><div class="value stopped" id="count-stopped">-</div><div class="label">Stopped/Exited</div></div>
            <div class="stat-card"><div class="value paused" id="count-paused">-</div><div class="label">Paused</div></div>
            <div class="stat-card"><div class="value" id="count-total">-</div><div class="label">Total</div></div>
        </div>
        <div class="refresh-bar">
            <span class="last-update" id="last-update">-</span>
            <button onclick="loadContainers()">Actualizar</button>
        </div>
        <div id="error"></div>
        <table>
            <thead><tr><th>Estado</th><th>Nombre</th><th>Imagen</th><th>Puertos</th><th>Uptime</th></tr></thead>
            <tbody id="tbody"></tbody>
        </table>
    </main>
    <script>
        async function loadContainers() {
            try {
                const r = await fetch('/api/containers');
                if (!r.ok) throw new Error(await r.text());
                const data = await r.json();
                document.getElementById('error').style.display = 'none';
                document.getElementById('host').textContent = data.host;
                document.getElementById('last-update').textContent = 'Actualizado: ' + new Date(data.timestamp).toLocaleTimeString('es-MX');

                const counts = { running: 0, stopped: 0, paused: 0 };
                data.containers.forEach(c => {
                    if (c.status === 'running') counts.running++;
                    else if (c.status === 'paused') counts.paused++;
                    else counts.stopped++;
                });
                document.getElementById('count-running').textContent = counts.running;
                document.getElementById('count-stopped').textContent = counts.stopped;
                document.getElementById('count-paused').textContent = counts.paused;
                document.getElementById('count-total').textContent = data.containers.length;

                const tbody = document.getElementById('tbody');
                tbody.innerHTML = data.containers.map(c => {
                    const st = c.status === 'running' ? 'running' :
                               c.status === 'paused' ? 'paused' :
                               (c.status === 'exited' || c.status === 'stopped') ? 'exited' : 'other';
                    return '<tr>' +
                        '<td><span class="status-badge status-' + st + '">' + c.status + '</span></td>' +
                        '<td><strong>' + c.name + '</strong></td>' +
                        '<td style="color:#8b949e;font-size:0.8rem">' + c.image + '</td>' +
                        '<td style="font-size:0.8rem">' + (c.ports || '-') + '</td>' +
                        '<td style="font-size:0.8rem">' + (c.uptime || '-') + '</td>' +
                        '</tr>';
                }).join('');
            } catch (e) {
                const el = document.getElementById('error');
                el.textContent = 'Error: ' + e.message;
                el.style.display = 'block';
            }
        }
        loadContainers();
        setInterval(loadContainers, 15000);
    </script>
</body>
</html>"""

def get_containers():
    """Obtiene lista de containers via docker ps."""
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format',
             '{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}'],
            capture_output=True, text=True, timeout=10
        )
        containers = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|')
            if len(parts) >= 3:
                name, image, status_full = parts[0], parts[1], parts[2]
                ports = parts[3] if len(parts) > 3 else ''
                status_lower = status_full.lower()
                if 'up' in status_lower:
                    status = 'running'
                elif 'exited' in status_lower:
                    status = 'exited'
                elif 'paused' in status_lower:
                    status = 'paused'
                else:
                    status = 'stopped'
                containers.append({
                    'name': name,
                    'image': image.split('/')[-1] if '/' in image else image,
                    'status': status,
                    'ports': ports[:60] if ports else '',
                    'uptime': status_full[:50],
                })
        return containers
    except Exception as e:
        return [{'name': 'error', 'image': str(e), 'status': 'error', 'ports': '', 'uptime': ''}]

def get_hostname():
    try:
        return subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip()
    except:
        return 'unknown'

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/containers')
def api_containers():
    return jsonify({
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'host': get_hostname(),
        'containers': get_containers(),
    })

@app.route('/health')
def health():
    try:
        subprocess.run(['docker', 'ps'], capture_output=True, timeout=5)
        return jsonify({'status': 'ok', 'docker': 'accessible', 'timestamp': datetime.utcnow().isoformat() + 'Z'})
    except Exception as e:
        return jsonify({'status': 'error', 'docker': str(e)}), 503

if __name__ == '__main__':
    print(f"Docker Healthcheck Dashboard en http://0.0.0.0:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False)
