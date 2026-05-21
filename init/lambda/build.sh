#!/bin/bash
set -e

PKG_DIR="/tmp/lambda-pkg"
ZIP_OUT="/lambda/dist/lambda.zip"

echo "[lambda-builder] Installing dependencies..."
pip install -r /lambda/requirements.txt -t "$PKG_DIR" --quiet --no-cache-dir

echo "[lambda-builder] Copying source code..."
cp -r /lambda/src/. "$PKG_DIR"/

echo "[lambda-builder] Creating ZIP..."
python3 - <<'EOF'
import zipfile, os, sys

base = "/tmp/lambda-pkg"
out  = "/lambda/dist/lambda.zip"

os.makedirs(os.path.dirname(out), exist_ok=True)

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith(".pyc"):
                fp = os.path.join(root, f)
                zf.write(fp, os.path.relpath(fp, base))

size_mb = os.path.getsize(out) / (1024 * 1024)
print(f"[lambda-builder] {out} criado ({size_mb:.1f} MB)")
EOF
