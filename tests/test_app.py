"""Tests comprehensivos para docker-healthcheck-dashboard."""
import sys
import os
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import app as dashboard


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    dashboard.app.config['TESTING'] = True
    with dashboard.app.test_client() as c:
        yield c


@pytest.fixture
def auth_client(monkeypatch):
    monkeypatch.setattr(dashboard.config, 'DASHBOARD_TOKEN', 'test-secret')
    dashboard.app.config['TESTING'] = True
    with dashboard.app.test_client() as c:
        yield c


_SAMPLE_CONTAINERS = [
    {
        'id': 'abc123def456',
        'name': 'my-app',
        'image': 'nginx:latest',
        'status': 'Up 2 hours',
        'state': 'running',
        'state_icon': '🟢',
        'ports': '0.0.0.0:80->80/tcp',
        'uptime': '2 hours ago',
    },
    {
        'id': 'dead0000beef',
        'name': 'stopped-service',
        'image': 'redis:7',
        'status': 'Exited (0) 1 hour ago',
        'state': 'exited',
        'state_icon': '🔴',
        'ports': '',
        'uptime': '3 hours ago',
    },
]

_SAMPLE_SYSTEM = {
    'server_version': '24.0.5',
    'images': 10,
    'cpus': 4,
    'memory_total': 8589934592,
    'swarm_active': True,
    'containers_stopped': 2,
}


# ── Index ──────────────────────────────────────────────────────────────────────

def test_index_returns_200(client):
    resp = client.get('/')
    assert resp.status_code == 200


def test_index_contains_html(client):
    resp = client.get('/')
    assert b'Docker' in resp.data or b'docker' in resp.data


# ── /health ───────────────────────────────────────────────────────────────────

def test_health_docker_accessible(client):
    with patch('app.is_docker_accessible', return_value=True):
        resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    assert data['docker'] == 'accessible'
    assert 'timestamp' in data


def test_health_docker_not_accessible(client):
    with patch('app.is_docker_accessible', return_value=False):
        resp = client.get('/health')
    assert resp.status_code == 503
    data = resp.get_json()
    assert data['status'] == 'error'


def test_health_no_auth_required(auth_client):
    """Health endpoint no requiere token."""
    with patch('app.is_docker_accessible', return_value=True):
        resp = auth_client.get('/health')
    assert resp.status_code == 200


# ── /api/containers ───────────────────────────────────────────────────────────

def test_api_containers_returns_structure(client):
    with patch('app.get_containers', return_value=_SAMPLE_CONTAINERS), \
         patch('app.get_hostname', return_value='test-host'):
        resp = client.get('/api/containers')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'containers' in data
    assert 'total' in data
    assert 'running' in data
    assert 'stopped' in data
    assert 'timestamp' in data
    assert 'host' in data


def test_api_containers_counts(client):
    with patch('app.get_containers', return_value=_SAMPLE_CONTAINERS), \
         patch('app.get_hostname', return_value='host'):
        resp = client.get('/api/containers')
    data = resp.get_json()
    assert data['total'] == 2
    assert data['running'] == 1
    assert data['stopped'] == 1


def test_api_containers_empty(client):
    with patch('app.get_containers', return_value=[]), \
         patch('app.get_hostname', return_value='host'):
        resp = client.get('/api/containers')
    data = resp.get_json()
    assert data['total'] == 0
    assert data['running'] == 0
    assert data['stopped'] == 0


def test_api_containers_filter_by_state(client):
    with patch('app.get_containers', return_value=_SAMPLE_CONTAINERS), \
         patch('app.get_hostname', return_value='host'):
        resp = client.get('/api/containers?state=running')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert data['all_total'] == 2
    assert data['filtered_total'] == 1
    assert data['containers'][0]['state'] == 'running'
    assert data['filters']['state'] == 'running'


def test_api_containers_filter_by_search(client):
    with patch('app.get_containers', return_value=_SAMPLE_CONTAINERS), \
         patch('app.get_hostname', return_value='host'):
        resp = client.get('/api/containers?search=redis')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert data['containers'][0]['image'] == 'redis:7'
    assert data['filters']['search'] == 'redis'


def test_api_containers_pagination(client):
    with patch('app.get_containers', return_value=_SAMPLE_CONTAINERS), \
         patch('app.get_hostname', return_value='host'):
        resp = client.get('/api/containers?offset=1&limit=1')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['total'] == 1
    assert data['all_total'] == 2
    assert data['filtered_total'] == 2
    assert data['filters']['offset'] == 1
    assert data['filters']['limit'] == 1
    assert data['containers'][0]['id'] == 'dead0000beef'


def test_api_containers_invalid_state(client):
    resp = client.get('/api/containers?state=invalid')
    assert resp.status_code == 400
    assert 'state must be one of' in resp.get_json()['error']


def test_api_containers_invalid_limit(client):
    resp = client.get('/api/containers?limit=-1')
    assert resp.status_code == 400
    assert resp.get_json()['error'] == 'limit must be greater than or equal to 0'


def test_api_containers_requires_auth(auth_client):
    resp = auth_client.get('/api/containers')
    assert resp.status_code == 401


def test_api_containers_auth_x_token(auth_client):
    with patch('app.get_containers', return_value=[]), \
         patch('app.get_hostname', return_value='host'):
        resp = auth_client.get('/api/containers', headers={'X-Token': 'test-secret'})
    assert resp.status_code == 200


def test_api_containers_auth_bearer(auth_client):
    with patch('app.get_containers', return_value=[]), \
         patch('app.get_hostname', return_value='host'):
        resp = auth_client.get('/api/containers',
                               headers={'Authorization': 'Bearer test-secret'})
    assert resp.status_code == 200


def test_api_containers_auth_wrong_token(auth_client):
    resp = auth_client.get('/api/containers', headers={'X-Token': 'wrong'})
    assert resp.status_code == 401


# ── /api/system ───────────────────────────────────────────────────────────────

def test_api_system_returns_structure(client):
    with patch('app.get_system_info', return_value=_SAMPLE_SYSTEM):
        resp = client.get('/api/system')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'system' in data
    assert 'timestamp' in data
    s = data['system']
    assert 'server_version' in s
    assert 'images' in s
    assert 'cpus' in s
    assert 'memory_total' in s
    assert 'swarm_active' in s


def test_api_system_docker_unavailable(client):
    with patch('app.get_system_info', return_value={}):
        resp = client.get('/api/system')
    assert resp.status_code == 503


def test_api_system_requires_auth(auth_client):
    resp = auth_client.get('/api/system')
    assert resp.status_code == 401


# ── /api/container/<id>/logs ──────────────────────────────────────────────────

def test_api_logs_returns_lines(client):
    logs = ['2024-01-01T00:00:00 line1', '2024-01-01T00:00:01 line2']
    with patch('app.get_container_logs', return_value=logs):
        resp = client.get('/api/container/abc123def456/logs')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['logs'] == logs
    assert data['lines'] == 2
    assert data['container_id'] == 'abc123def456'


def test_api_logs_custom_lines(client):
    with patch('app.get_container_logs', return_value=[]) as mock_logs:
        client.get('/api/container/abc123def456/logs?lines=50')
    mock_logs.assert_called_once_with('abc123def456', 50)


def test_api_logs_invalid_lines(client):
    resp = client.get('/api/container/abc123def456/logs?lines=notanumber')
    assert resp.status_code == 400


def test_api_logs_invalid_container_id(client):
    with patch('app.get_container_logs', side_effect=ValueError("Invalid container ID")):
        resp = client.get('/api/container/../../etc/passwd/logs')
    assert resp.status_code in (400, 404)


def test_api_logs_docker_error(client):
    with patch('app.get_container_logs', side_effect=RuntimeError("docker logs timed out")):
        resp = client.get('/api/container/abc123def456/logs')
    assert resp.status_code == 503


def test_api_logs_requires_auth(auth_client):
    resp = auth_client.get('/api/container/abc123def456/logs')
    assert resp.status_code == 401


# ── /api/container/<id>/action ────────────────────────────────────────────────

def test_api_action_stop_success(client):
    with patch('app.container_action', return_value={'success': True, 'message': 'abc123def456'}):
        resp = client.post('/api/container/abc123def456/action',
                           json={'action': 'stop'})
    assert resp.status_code == 200
    assert resp.get_json()['success'] is True


def test_api_action_start_success(client):
    with patch('app.container_action', return_value={'success': True, 'message': ''}):
        resp = client.post('/api/container/abc123def456/action',
                           json={'action': 'start'})
    assert resp.status_code == 200


def test_api_action_invalid_action(client):
    with patch('app.container_action', side_effect=ValueError("Action must be one of: restart, start, stop")):
        resp = client.post('/api/container/abc123def456/action',
                           json={'action': 'delete'})
    assert resp.status_code == 400


def test_api_action_docker_error(client):
    with patch('app.container_action', side_effect=RuntimeError("docker stop timed out")):
        resp = client.post('/api/container/abc123def456/action',
                           json={'action': 'stop'})
    assert resp.status_code == 503


def test_api_action_requires_auth(auth_client):
    resp = auth_client.post('/api/container/abc123def456/action', json={'action': 'stop'})
    assert resp.status_code == 401


def test_api_action_no_body(client):
    with patch('app.container_action', return_value={'success': False, 'message': 'no action'}):
        resp = client.post('/api/container/abc123def456/action')
    assert resp.status_code in (200, 400, 500)


# ── Docker service unit tests ─────────────────────────────────────────────────

def test_docker_service_parse_containers():
    from services.docker_service import get_containers
    mock_output = (
        'abc123def456\tmy-app\tnginx:latest\tUp 2 hours\trunning\t80/tcp\t2 hours ago\n'
        'dead0000beef\tstopped\tredis:7\tExited (0) 1h\texited\t\t3 hours ago\n'
    )
    mock = MagicMock(stdout=mock_output, stderr='', returncode=0)
    with patch('services.docker_service._run', return_value=mock):
        result = get_containers()
    assert len(result) == 2
    assert result[0]['name'] == 'my-app'
    assert result[0]['state'] == 'running'
    assert result[0]['state_icon'] == '🟢'
    assert result[1]['state'] == 'exited'
    assert result[1]['state_icon'] == '🔴'


def test_docker_service_no_docker():
    from services.docker_service import get_containers
    with patch('services.docker_service._run', side_effect=FileNotFoundError("No such file")):
        result = get_containers()
    assert result == []


def test_docker_service_empty_output():
    from services.docker_service import get_containers
    mock = MagicMock(stdout='', stderr='', returncode=0)
    with patch('services.docker_service._run', return_value=mock):
        result = get_containers()
    assert result == []


def test_docker_service_get_system_info():
    from services.docker_service import get_system_info
    mock_output = '24.0.5\t10\t4\t8589934592\tactive\t2\n'
    mock = MagicMock(stdout=mock_output, returncode=0)
    with patch('services.docker_service._run', return_value=mock):
        result = get_system_info()
    assert result['server_version'] == '24.0.5'
    assert result['images'] == 10
    assert result['cpus'] == 4
    assert result['swarm_active'] is True
    assert result['containers_stopped'] == 2


def test_docker_service_container_logs():
    from services.docker_service import get_container_logs
    mock = MagicMock(stdout='2024-01-01 line1\n2024-01-01 line2\n', stderr='', returncode=0)
    with patch('services.docker_service._run', return_value=mock):
        result = get_container_logs('abc123def456', 10)
    assert result == ['2024-01-01 line1', '2024-01-01 line2']


def test_docker_service_container_id_validation():
    from services.docker_service import get_container_logs
    with pytest.raises(ValueError, match="Invalid container ID"):
        get_container_logs('../../etc/passwd', 10)


def test_docker_service_action_validation():
    from services.docker_service import container_action
    with pytest.raises(ValueError, match="Action must be one of"):
        container_action('abc123def456', 'delete')


def test_docker_service_action_id_validation():
    from services.docker_service import container_action
    with pytest.raises(ValueError, match="Invalid container ID"):
        container_action('../malicious', 'stop')


def test_docker_service_action_success():
    from services.docker_service import container_action
    mock = MagicMock(stdout='abc123def456\n', stderr='', returncode=0)
    with patch('services.docker_service._run', return_value=mock):
        result = container_action('abc123def456', 'stop')
    assert result['success'] is True


def test_config_defaults():
    import config as cfg
    assert cfg.PORT >= 1
    assert cfg.REFRESH_INTERVAL >= 1
    assert cfg.DOCKER_TIMEOUT >= 1
    assert cfg.LOGS_MAX_LINES >= 1
