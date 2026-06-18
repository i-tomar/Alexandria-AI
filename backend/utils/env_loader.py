from pathlib import Path
import os


def load_project_env():
    # Check both Root and Backend folders for .env
    env_paths = [
        Path(__file__).resolve().parents[2] / ".env",  # Root
        Path(__file__).resolve().parents[1] / ".env",  # Backend folder
    ]
    
    for env_path in env_paths:
        if not env_path.exists():
            continue

        try:
            for raw_line in env_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ[key] = value
        except Exception:
            pass
