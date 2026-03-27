# Docker Healthcheck Dashboard

A lightweight web dashboard built with Flask that displays the real-time status of all Docker containers running on your host. Includes CPU and memory usage, uptime, exposed ports, and auto-refresh every 30 seconds.

---

## Features

- Live container status: running, stopped, restarting, paused
- CPU and memory usage with progress bars (color-coded by load level)
- Uptime calculated from container start time
- Exposed ports display
- Filter by All / Running / Stopped
- Auto-refresh every 30 seconds with visible countdown
- Optional Bearer token authentication
- Dark UI with Bootstrap 5

---

## Dashboard layout (text description)

```
┌─────────────────────────────────────────────┐
│  🐳 Docker Dashboard         [12 containers] │
├─────────────────────────────────────────────┤
│   Total: 12   │  Running: 9  │  Stopped: 3   │
├─────────────────────────────────────────────┤
│  [All] [Running] [Stopped]                   │
├──────────────┬──────────────┬───────────────┤
│ nginx         │ postgres      │ redis          │
│ ● running     │ ● running     │ ✕ exited       │
│ Image: nginx  │ Image: pg:15  │ Image: redis   │
│ Uptime: 2d 4h │ Uptime: 12h   │ Uptime: —      │
│ Port: 80→80   │ Port: 5432    │                │
│ CPU ██░░ 12%  │ CPU █░░░  5%  │                │
│ MEM ███░ 45%  │ MEM ██░░ 38%  │                │
└──────────────┴──────────────┴───────────────┘
│ Last updated: 14:32:10   [↻ Refresh] [30s]   │
└─────────────────────────────────────────────┘
```

---

## Installation

### Option 1 — docker-compose (recommended)

```bash
git clone https://github.com/Quesillo27/docker-healthcheck-dashboard.git
cd docker-healthcheck-dashboard
cp .env.example .env
# Edit .env and set DASHBOARD_TOKEN
docker-compose up -d
```

Open http://localhost:5050

### Option 2 — docker run

```bash
docker build -t docker-dashboard .
docker run -d \
  -p 5050:5050 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -e DASHBOARD_TOKEN=my-secret-token \
  --name docker-dashboard \
  docker-dashboard
```

### Option 3 — Python directly (development)

```bash
git clone https://github.com/Quesillo27/docker-healthcheck-dashboard.git
cd docker-healthcheck-dashboard
pip install -r requirements.txt
export DASHBOARD_TOKEN=my-secret-token   # optional
python app.py
```

Open http://localhost:5050

---

## Environment variables

| Variable         | Default | Description                                    |
|------------------|---------|------------------------------------------------|
| `DASHBOARD_TOKEN`| (empty) | Bearer token for auth. If empty, auth disabled |
| `PORT`           | `5050`  | Port the server listens on                     |
| `FLASK_DEBUG`    | `false` | Enable Flask debug mode                        |

---

## API Endpoints

### GET /api/containers

Returns the list of all Docker containers with stats.

**Headers (if token is set):**
```
Authorization: Bearer my-secret-token
```

**Response:**
```json
{
  "containers": [
    {
      "id": "a1b2c3d4",
      "name": "nginx",
      "image": "nginx:latest",
      "status": "running",
      "started_at": "2026-03-25T10:00:00Z",
      "ports": {
        "80/tcp": ["80"]
      },
      "stats": {
        "cpu_pct": 2.34,
        "mem_usage_mb": 128.5,
        "mem_limit_mb": 2048.0,
        "mem_pct": 6.27
      }
    }
  ],
  "total": 1,
  "running": 1,
  "stopped": 0,
  "timestamp": "2026-03-27T14:00:00+00:00"
}
```

### GET /api/health

Health check — verifies Docker socket connectivity.

**Response 200:**
```json
{
  "status": "ok",
  "docker": "connected",
  "timestamp": "2026-03-27T14:00:00+00:00"
}
```

**Response 503:**
```json
{
  "status": "error",
  "docker": "Error connecting to Docker daemon"
}
```

---

## Usage examples

```bash
# Without auth
curl http://localhost:5050/api/health
curl http://localhost:5050/api/containers

# With auth token
curl -H "Authorization: Bearer my-secret-token" http://localhost:5050/api/containers

# Pretty print
curl -s http://localhost:5050/api/containers | python3 -m json.tool
```

---

## Setting the auth token in the browser

If `DASHBOARD_TOKEN` is set, the dashboard needs to send the token with each API request. Open `templates/index.html` and set:

```javascript
const TOKEN = 'my-secret-token';
```

Alternatively, you can put the dashboard behind a reverse proxy (Nginx/Traefik) that handles authentication at the proxy level and leave `DASHBOARD_TOKEN` empty.

---

## Requirements

- Docker host with access to `/var/run/docker.sock`
- Python 3.11+ (for direct run) or Docker (for containerized run)

---

## License

MIT
