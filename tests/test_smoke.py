#!/usr/bin/env python3
"""Smoke tests para docker-healthcheck-dashboard."""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_import():
    """Flask app importa sin errores."""
    import app as dashboard
    assert hasattr(dashboard, 'app')
    assert hasattr(dashboard, 'get_containers')
    print("test_import passed")

def test_health_route():
    """Ruta /health responde."""
    import app as dashboard
    client = dashboard.app.test_client()
    resp = client.get('/health')
    assert resp.status_code in [200, 503]
    data = resp.get_json()
    assert 'status' in data
    print(f"test_health_route passed (status={data['status']})")

def test_index_route():
    """Ruta / retorna HTML."""
    import app as dashboard
    client = dashboard.app.test_client()
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'Docker Healthcheck Dashboard' in resp.data
    print("test_index_route passed")

def test_api_containers():
    """API retorna JSON con estructura correcta."""
    import app as dashboard
    client = dashboard.app.test_client()
    resp = client.get('/api/containers')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'containers' in data
    assert 'timestamp' in data
    assert isinstance(data['containers'], list)
    print("test_api_containers passed")

if __name__ == '__main__':
    tests = [test_import, test_health_route, test_index_route, test_api_containers]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"FAILED {t.__name__}: {e}")
            import traceback; traceback.print_exc()
            failed += 1

    if failed:
        print(f"\n{failed}/{len(tests)} tests fallaron")
        sys.exit(1)
    else:
        print(f"\nTodos los tests pasaron ({len(tests)}/{len(tests)})")
        sys.exit(0)
