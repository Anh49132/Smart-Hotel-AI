import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


def test_application_imports_from_another_directory():
    root = Path(__file__).resolve().parents[2]
    environment = dict(os.environ, PYTHONPATH=str(root))
    with TemporaryDirectory(prefix='hotel-import-') as directory:
        result = subprocess.run(
            [sys.executable, '-c',
             'from main import app; from core.config import FRONTEND_DIR; '
             'assert (FRONTEND_DIR / "templates/layouts/base.html").is_file(); '
             'assert any(r.path == "/api/rooms" for r in app.routes)'],
            cwd=directory, env=environment, capture_output=True, text=True,
        )
    assert result.returncode == 0, result.stderr
