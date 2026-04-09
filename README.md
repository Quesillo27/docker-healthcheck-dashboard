# docker-healthcheck-dashboard

App web Flask ligera que muestra el estado de todos los containers Docker en el VPS en tiempo real.

## Instalacion rapida

```bash
git clone https://github.com/Quesillo27/docker-healthcheck-dashboard.git
cd docker-healthcheck-dashboard
pip install -r requirements.txt
python3 app.py
```

Abre http://localhost:5050

## Variables de entorno

| Variable | Default | Descripcion |
|----------|---------|-------------|
| `PORT` | 5050 | Puerto del servidor |

## API Endpoints

| Endpoint | Descripcion |
|----------|-------------|
| `GET /` | Dashboard HTML |
| `GET /api/containers` | JSON con lista de containers |
| `GET /health` | Health check (verifica acceso a Docker) |

## Docker

```bash
docker build -t docker-healthcheck-dashboard .
docker run -v /var/run/docker.sock:/var/run/docker.sock -p 5050:5050 docker-healthcheck-dashboard
```

## Tests

```bash
python3 tests/test_smoke.py
```

## Requisitos

- Python 3.8+
- Flask 3.0+
- Docker accesible en el host
