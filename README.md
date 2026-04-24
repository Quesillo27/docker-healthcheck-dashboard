# docker-healthcheck-dashboard

![tests](https://img.shields.io/badge/tests-46%20passing-brightgreen)

App web Flask que muestra el estado de todos los containers Docker en tiempo real. Incluye logs inline, acciones (start/stop/restart), info del sistema y auto-refresh configurable.

## Instalación en 3 comandos

```bash
git clone https://github.com/Quesillo27/docker-healthcheck-dashboard.git
cd docker-healthcheck-dashboard
pip install -r requirements.txt && python3 app.py
```

Abre http://localhost:5050

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `PORT` | 5050 | Puerto del servidor |
| `DASHBOARD_TOKEN` | *(vacío)* | Token de acceso (si se configura, todos los endpoints `/api/*` requieren autenticación) |
| `REFRESH_INTERVAL` | 10 | Segundos entre auto-refresh del dashboard |
| `DOCKER_TIMEOUT` | 10 | Timeout en segundos para comandos Docker |
| `LOGS_MAX_LINES` | 500 | Máximo de líneas de log a retornar |
| `LOG_LEVEL` | INFO | Nivel de logging (DEBUG, INFO, WARNING, ERROR) |

## Autenticación

Si `DASHBOARD_TOKEN` está configurado, los endpoints `/api/*` requieren el token via:

```http
X-Token: mi-token-secreto
Authorization: Bearer mi-token-secreto
GET /api/containers?token=mi-token-secreto
```

El token también se puede guardar en `localStorage.dashboard_token` desde el navegador.

## API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `GET /` | — | Dashboard HTML |
| `GET /health` | — | Health check (sin auth) |
| `GET /api/containers` | — | Lista todos los containers con estado |
| `GET /api/system` | — | Info del sistema Docker (versión, CPUs, RAM, Swarm) |
| `GET /api/container/<id>/logs?lines=100` | — | Últimas N líneas de logs |
| `POST /api/container/<id>/action` | `{"action": "start\|stop\|restart"}` | Controlar container |

### Filtros en `GET /api/containers`

La lista de containers ahora acepta filtros y paginación opcional para integraciones o hosts con muchos containers:

| Query param | Ejemplo | Descripción |
|-------------|---------|-------------|
| `state` | `running` | Filtra por estado (`running`, `exited`, `paused`, `restarting`, `dead`, `created`) |
| `search` | `nginx` | Busca por nombre o imagen |
| `limit` | `10` | Límite máximo de resultados |
| `offset` | `20` | Desplazamiento para paginación |

Ejemplo:

```bash
curl "http://localhost:5050/api/containers?state=running&search=nginx&limit=10"
```

La respuesta mantiene `containers`, `total`, `running` y `stopped`, y agrega `all_total`, `filtered_total` y `filters` para facilitar paginación y debugging.

## Docker

```bash
docker build -t docker-healthcheck-dashboard .
docker run -v /var/run/docker.sock:/var/run/docker.sock -p 5050:5050 \
  -e DASHBOARD_TOKEN=mi-token docker-healthcheck-dashboard
```

O con docker-compose:

```bash
cp .env.example .env
# Editar .env con tus valores
docker compose up -d
```

## Estructura del proyecto

```
├── app.py                    # Rutas Flask
├── config.py                 # Configuración centralizada
├── services/
│   └── docker_service.py     # Interacción con Docker
├── templates/
│   └── dashboard.html        # UI principal
├── tests/
│   └── test_app.py           # 46 tests
└── Dockerfile
```

## Tests

```bash
python3 -m pytest tests/ -v
```

## Requisitos

- Python 3.8+
- Flask 3.0+
- Docker accesible en el host (socket montado)

## Roadmap

- Métricas de CPU/memoria en tiempo real via `docker stats`
- Historial de uptime con gráficos
- Filtros por red Docker y por label
- Notificaciones cuando un container cambia de estado
