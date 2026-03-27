import docker
import os
from flask import Flask, jsonify, render_template, request, abort
from datetime import datetime, timezone

app = Flask(__name__)
DASHBOARD_TOKEN = os.getenv('DASHBOARD_TOKEN', '')


def check_auth():
    if not DASHBOARD_TOKEN:
        return True
    auth = request.headers.get('Authorization', '')
    return auth == f'Bearer {DASHBOARD_TOKEN}'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/containers')
def get_containers():
    if not check_auth():
        abort(401)
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)
        data = []
        for c in containers:
            stats = {}
            try:
                if c.status == 'running':
                    raw_stats = c.stats(stream=False)
                    # CPU %
                    cpu_delta = (
                        raw_stats['cpu_stats']['cpu_usage']['total_usage']
                        - raw_stats['precpu_stats']['cpu_usage']['total_usage']
                    )
                    system_delta = (
                        raw_stats['cpu_stats']['system_cpu_usage']
                        - raw_stats['precpu_stats']['system_cpu_usage']
                    )
                    num_cpus = raw_stats['cpu_stats'].get('online_cpus', 1)
                    cpu_pct = (
                        (cpu_delta / system_delta) * num_cpus * 100
                        if system_delta > 0
                        else 0
                    )
                    # Memory
                    mem_usage = raw_stats['memory_stats']['usage']
                    mem_limit = raw_stats['memory_stats']['limit']
                    mem_pct = (mem_usage / mem_limit) * 100 if mem_limit > 0 else 0
                    stats = {
                        'cpu_pct': round(cpu_pct, 2),
                        'mem_usage_mb': round(mem_usage / 1024 / 1024, 1),
                        'mem_limit_mb': round(mem_limit / 1024 / 1024, 1),
                        'mem_pct': round(mem_pct, 2),
                    }
            except Exception:
                pass

            ports = {}
            if c.ports:
                for container_port, bindings in c.ports.items():
                    if bindings:
                        ports[container_port] = [b['HostPort'] for b in bindings]

            data.append({
                'id': c.short_id,
                'name': c.name,
                'image': c.image.tags[0] if c.image.tags else c.image.short_id,
                'status': c.status,
                'started_at': c.attrs['State'].get('StartedAt', ''),
                'ports': ports,
                'stats': stats,
            })

        # Sort: running first, then alphabetically by name
        data.sort(key=lambda x: (0 if x['status'] == 'running' else 1, x['name']))

        return jsonify({
            'containers': data,
            'total': len(data),
            'running': sum(1 for c in data if c['status'] == 'running'),
            'stopped': sum(1 for c in data if c['status'] != 'running'),
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health')
def health():
    try:
        client = docker.from_env()
        client.ping()
        return jsonify({
            'status': 'ok',
            'docker': 'connected',
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        return jsonify({'status': 'error', 'docker': str(e)}), 503


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5050))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug)
