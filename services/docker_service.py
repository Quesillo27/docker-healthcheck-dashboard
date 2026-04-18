"""Capa de acceso a Docker via subprocess."""
import re
import subprocess
import logging
from datetime import datetime
from config import DOCKER_TIMEOUT, LOGS_MAX_LINES

logger = logging.getLogger(__name__)

_STATE_ICONS = {
    'running': '🟢',
    'exited': '🔴',
    'stopped': '🔴',
    'paused': '🟡',
    'restarting': '🔄',
    'dead': '💀',
    'created': '⚪',
}

_ALLOWED_ACTIONS = {'start', 'stop', 'restart'}
_CONTAINER_ID_RE = re.compile(r'^[a-f0-9]{12,64}$')


def _run(cmd: list, timeout: int = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout or DOCKER_TIMEOUT,
    )


def get_containers() -> list:
    """Lista todos los containers con estado, id, imagen, puertos y uptime."""
    try:
        result = _run([
            'docker', 'ps', '-a',
            '--format',
            '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.State}}\t{{.Ports}}\t{{.RunningFor}}',
        ])
        containers = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) < 5:
                continue
            cid, name, image, status_full, state = parts[:5]
            ports = parts[5] if len(parts) > 5 else ''
            running_for = parts[6] if len(parts) > 6 else ''
            state_norm = state.lower()
            containers.append({
                'id': cid,
                'name': name,
                'image': image,
                'status': status_full,
                'state': state_norm,
                'state_icon': _STATE_ICONS.get(state_norm, '⚪'),
                'ports': ports,
                'uptime': running_for,
            })
        return containers
    except FileNotFoundError:
        logger.error("docker binary not found")
        return []
    except subprocess.TimeoutExpired:
        logger.error("docker ps timed out")
        return []
    except Exception as exc:
        logger.error("get_containers error: %s", exc)
        return []


def get_system_info() -> dict:
    """Devuelve info del sistema Docker: versión, imágenes, swarm, CPUs, RAM."""
    try:
        result = _run(['docker', 'info', '--format',
                       '{{.ServerVersion}}\t{{.Images}}\t{{.NCPU}}\t{{.MemTotal}}\t{{.Swarm.LocalNodeState}}\t{{.ContainersStopped}}'])
        if not result.stdout.strip():
            raise RuntimeError("docker info returned empty")
        parts = result.stdout.strip().split('\t')
        version = parts[0] if len(parts) > 0 else ''
        images = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        cpus = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0
        mem_total = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        swarm_state = parts[4] if len(parts) > 4 else 'inactive'
        stopped = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 0
        return {
            'server_version': version,
            'images': images,
            'cpus': cpus,
            'memory_total': mem_total,
            'swarm_active': swarm_state == 'active',
            'containers_stopped': stopped,
        }
    except FileNotFoundError:
        logger.error("docker binary not found")
        return {}
    except subprocess.TimeoutExpired:
        logger.error("docker info timed out")
        return {}
    except Exception as exc:
        logger.error("get_system_info error: %s", exc)
        return {}


def get_container_logs(container_id: str, lines: int = 100) -> list:
    """Retorna las últimas N líneas de logs de un container."""
    if not _CONTAINER_ID_RE.match(container_id):
        raise ValueError(f"Invalid container ID: {container_id!r}")
    lines = max(1, min(lines, LOGS_MAX_LINES))
    try:
        result = _run(
            ['docker', 'logs', '--tail', str(lines), '--timestamps', container_id],
            timeout=15,
        )
        output = (result.stdout + result.stderr).strip()
        return output.splitlines() if output else []
    except FileNotFoundError:
        raise RuntimeError("docker binary not found")
    except subprocess.TimeoutExpired:
        raise RuntimeError("docker logs timed out")


def container_action(container_id: str, action: str) -> dict:
    """Ejecuta start/stop/restart en un container. Retorna {success, message}."""
    if action not in _ALLOWED_ACTIONS:
        raise ValueError(f"Action must be one of: {', '.join(sorted(_ALLOWED_ACTIONS))}")
    if not _CONTAINER_ID_RE.match(container_id):
        raise ValueError(f"Invalid container ID: {container_id!r}")
    try:
        result = _run(['docker', action, container_id], timeout=30)
        # Note: docker <action> <id>
        success = result.returncode == 0
        message = result.stdout.strip() or result.stderr.strip()
        if success:
            logger.info("container %s %s OK", container_id, action)
        else:
            logger.warning("container %s %s FAILED: %s", container_id, action, message)
        return {'success': success, 'message': message}
    except FileNotFoundError:
        raise RuntimeError("docker binary not found")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"docker {action} timed out")


def is_docker_accessible() -> bool:
    """Verifica si el socket de Docker es accesible."""
    try:
        result = _run(['docker', 'ps'], timeout=5)
        return result.returncode == 0
    except Exception:
        return False


def get_hostname() -> str:
    try:
        return _run(['hostname']).stdout.strip()
    except Exception:
        return 'unknown'
