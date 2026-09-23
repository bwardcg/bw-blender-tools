"""
Copy bw_tools/ into Blender's user addons folder, replacing any existing copy.

    python install.py          # newest Blender version found in %APPDATA%
    python install.py 5.1      # a specific Blender version

Restart Blender (or Preferences > Add-ons > untick/tick BW Tools) afterwards.
"""
import os
import shutil
import sys
from pathlib import Path

REPO_ADDON = Path(__file__).resolve().parent / "bw_tools"
BLENDER_CONFIG = Path(os.environ["APPDATA"]) / "Blender Foundation" / "Blender"


def _version_key(path):
    try:
        return tuple(int(p) for p in path.name.split("."))
    except ValueError:
        return ()


def main():
    if len(sys.argv) > 1:
        version_dir = BLENDER_CONFIG / sys.argv[1]
    else:
        versions = [p for p in BLENDER_CONFIG.iterdir() if p.is_dir() and _version_key(p)]
        if not versions:
            sys.exit(f"No Blender config folders found in {BLENDER_CONFIG}")
        version_dir = max(versions, key=_version_key)

    if not version_dir.is_dir():
        sys.exit(f"Blender config folder not found: {version_dir}")

    target = version_dir / "scripts" / "addons" / "bw_tools"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(REPO_ADDON, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    print(f"Installed {REPO_ADDON} -> {target}")


if __name__ == "__main__":
    main()
