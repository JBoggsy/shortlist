#!/usr/bin/env bash
#
# Build the Flask backend as a standalone binary using PyInstaller,
# then place it in src-tauri/binaries/ with the Tauri target-triple naming.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Detect target triple
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  ARCH="x86_64" ;;
    aarch64) ARCH="aarch64" ;;
    arm64)   ARCH="aarch64" ;;
    *)       echo "Unsupported architecture: $ARCH"; exit 1 ;;
esac

OS="$(uname -s)"
case "$OS" in
    Linux*)  TRIPLE="${ARCH}-unknown-linux-gnu" ;;
    Darwin*) TRIPLE="${ARCH}-apple-darwin" ;;
    MINGW*|MSYS*|CYGWIN*) TRIPLE="${ARCH}-pc-windows-msvc" ;;
    *)       echo "Unsupported OS: $OS"; exit 1 ;;
esac

BINARY_NAME="flask-backend-${TRIPLE}"
OUTPUT_DIR="src-tauri/binaries"

echo "Building sidecar for target: ${TRIPLE}"
echo "Output: ${OUTPUT_DIR}/${BINARY_NAME}"

mkdir -p "$OUTPUT_DIR"

# Build with PyInstaller
uv run pyinstaller \
    --onefile \
    --name "flask-backend" \
    --hidden-import backend \
    --hidden-import backend.app \
    --hidden-import backend.config \
    --hidden-import backend.config_manager \
    --hidden-import backend.data_dir \
    --hidden-import backend.database \
    --hidden-import backend.models \
    --hidden-import backend.routes \
    --hidden-import backend.llm \
    --hidden-import backend.agent \
    main.py

# Move to Tauri binaries directory with target-triple name
cp "dist/flask-backend" "${OUTPUT_DIR}/${BINARY_NAME}"

# On Windows, the binary will have .exe extension
if [[ "$OS" == MINGW* || "$OS" == MSYS* || "$OS" == CYGWIN* ]]; then
    cp "dist/flask-backend.exe" "${OUTPUT_DIR}/${BINARY_NAME}.exe"
fi

echo "Sidecar built successfully: ${OUTPUT_DIR}/${BINARY_NAME}"

# Clean up PyInstaller artifacts
rm -rf build/ dist/ flask-backend.spec
