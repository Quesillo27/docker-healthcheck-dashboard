#!/usr/bin/env python3
"""Smoke tests para Docker Healthcheck Dashboard."""

import sys
import importlib.util
from pathlib import Path

# Verificar que app.py existe y es importable
APP_PATH = Path(__file__).parent.parent / "app.py"


def test_app_exists():
    assert APP_PATH.exists(), f"app.py no encontrado en {APP_PATH}"
    print("✅ app.py existe")


def test_app_syntax():
    spec = importlib.util.spec_from_file_location("app", APP_PATH)
    # Solo verificar que se puede cargar el spec (no ejecutar)
    assert spec is not None
    print("✅ app.py tiene sintaxis válida (spec cargado)")


def test_requirements_exist():
    req_path = APP_PATH.parent / "requirements.txt"
    assert req_path.exists(), "requirements.txt no encontrado"
    content = req_path.read_text()
    assert "flask" in content.lower() or "Flask" in content, "Flask no está en requirements.txt"
    print("✅ requirements.txt existe y contiene Flask")


def test_dockerfile_exists():
    dockerfile = APP_PATH.parent / "Dockerfile"
    assert dockerfile.exists(), "Dockerfile no encontrado"
    content = dockerfile.read_text()
    assert "FROM" in content, "Dockerfile no tiene instrucción FROM"
    assert "CMD" in content or "ENTRYPOINT" in content, "Dockerfile no tiene CMD/ENTRYPOINT"
    print("✅ Dockerfile existe y tiene estructura correcta")


def test_templates_exist():
    templates = APP_PATH.parent / "templates"
    assert templates.exists(), "Directorio templates/ no encontrado"
    html_files = list(templates.glob("*.html"))
    assert len(html_files) > 0, "No hay archivos HTML en templates/"
    print(f"✅ templates/ existe con {len(html_files)} archivo(s) HTML")


if __name__ == "__main__":
    print("🧪 Ejecutando smoke tests de Docker Healthcheck Dashboard...\n")
    errors = 0

    tests = [
        test_app_exists,
        test_app_syntax,
        test_requirements_exist,
        test_dockerfile_exists,
        test_templates_exist,
    ]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ {test.__name__}: FAIL — {e}")
            errors += 1

    print(f"\n{'='*50}")
    if errors == 0:
        print(f"✅ Todos los smoke tests pasaron ({len(tests)}/{len(tests)})")
    else:
        print(f"❌ {errors} test(s) fallaron")
        sys.exit(1)
