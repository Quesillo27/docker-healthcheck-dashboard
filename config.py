"""Configuración centralizada del dashboard."""
import os

PORT = int(os.environ.get('PORT', 5050))
DASHBOARD_TOKEN = os.environ.get('DASHBOARD_TOKEN', '')
REFRESH_INTERVAL = int(os.environ.get('REFRESH_INTERVAL', 10))
DOCKER_TIMEOUT = int(os.environ.get('DOCKER_TIMEOUT', 10))
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
LOGS_MAX_LINES = int(os.environ.get('LOGS_MAX_LINES', 500))
