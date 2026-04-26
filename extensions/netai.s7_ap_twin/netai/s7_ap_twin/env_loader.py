import os
from pathlib import Path


def load_env() -> dict:
    candidates = [
        Path(__file__).parent.parent.parent / ".env",
        Path(__file__).parent.parent.parent.parent.parent.parent
        / "source/extensions/netai.s7_ap_twin/.env",
        Path(os.getcwd()) / "source/extensions/netai.s7_ap_twin/.env",
    ]

    env_path = None
    for candidate in candidates:
        print(f"[env_loader] trying: {candidate}")
        if candidate.exists():
            env_path = candidate
            print(f"[env_loader] found: {env_path}")
            break

    if env_path is None:
        print("[env_loader] .env file not found")
        return {}

    env_vars = {}
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            os.environ[key] = value
            env_vars[key] = value

    print(f"[env_loader] load complete: {list(env_vars.keys())}")
    return env_vars
