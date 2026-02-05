#!/usr/bin/env python3
"""
Auto-setup script for Kiterunner.

Downloads and installs Kiterunner binary from GitHub releases.
Wordlists are fetched remotely from Assetnote CDN at runtime (no local download needed).

Usage:
    python scripts/setup_kiterunner.py

Or called automatically by Raptor when Kiterunner is not found.
"""

import os
import platform
import shutil
import stat
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

# Kiterunner release info
KR_VERSION = "1.0.2"
KR_REPO = "assetnote/kiterunner"

# Default install location
DEFAULT_BIN_DIR = Path.home() / ".local" / "bin"


def get_platform_info() -> tuple[str, str]:
    """Detect OS and architecture for binary download."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    # Normalize OS
    if system == "darwin":
        os_name = "macOS"
    elif system == "linux":
        os_name = "linux"
    elif system == "windows":
        os_name = "windows"
    else:
        raise RuntimeError(f"Unsupported OS: {system}")

    # Normalize architecture
    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("arm64", "aarch64"):
        arch = "arm64"
    elif machine in ("i386", "i686"):
        arch = "386"
    else:
        raise RuntimeError(f"Unsupported architecture: {machine}")

    return os_name, arch


def get_kr_download_url() -> str:
    """Get Kiterunner download URL for current platform."""
    os_name, arch = get_platform_info()

    ext = "zip" if os_name == "windows" else "tar.gz"
    filename = f"kiterunner_{KR_VERSION}_{os_name}_{arch}.{ext}"

    return f"https://github.com/{KR_REPO}/releases/download/v{KR_VERSION}/{filename}"


def download_file(url: str, dest: Path, desc: str = "") -> bool:
    """Download a file with progress indication."""
    print(f"Downloading {desc or url}...")

    try:
        req = Request(url, headers={"User-Agent": "Raptor/1.0"})
        with urlopen(req, timeout=60) as response:
            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(dest, "wb") as f:
                while chunk := response.read(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = (downloaded / total) * 100
                        print(f"\r  Progress: {pct:.1f}%", end="", flush=True)

            print()
        return True

    except URLError as e:
        print(f"  Failed: {e}")
        return False


def install_kiterunner(bin_dir: Path = DEFAULT_BIN_DIR) -> Path | None:
    """Download and install Kiterunner binary."""
    # Check if already installed
    existing = shutil.which("kr") or shutil.which("kiterunner")
    if existing:
        print(f"Kiterunner already installed: {existing}")
        return Path(existing)

    print("Installing Kiterunner...")

    # Create bin directory
    bin_dir.mkdir(parents=True, exist_ok=True)

    # Download
    url = get_kr_download_url()
    os_name, _ = get_platform_info()
    ext = "zip" if os_name == "windows" else "tar.gz"

    with tempfile.TemporaryDirectory() as tmpdir:
        archive_path = Path(tmpdir) / f"kiterunner.{ext}"

        if not download_file(url, archive_path, "Kiterunner"):
            return None

        # Extract
        print("Extracting...")
        if ext == "zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(tmpdir)
        else:
            with tarfile.open(archive_path, "r:gz") as tf:
                tf.extractall(tmpdir)

        # Find binary
        binary_name = "kr.exe" if os_name == "windows" else "kr"
        binary_src = None
        for root, _, files in os.walk(tmpdir):
            if binary_name in files:
                binary_src = Path(root) / binary_name
                break

        if not binary_src:
            print("Error: Could not find kr binary in archive")
            return None

        # Install
        binary_dest = bin_dir / binary_name
        shutil.copy2(binary_src, binary_dest)

        # Make executable (Unix)
        if os_name != "windows":
            binary_dest.chmod(binary_dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        print(f"Installed: {binary_dest}")

        # Check if bin_dir is in PATH
        if str(bin_dir) not in os.environ.get("PATH", ""):
            print(f"\nAdd to PATH: export PATH=\"$PATH:{bin_dir}\"")

        return binary_dest


def main() -> Path | None:
    """Run setup and return path to Kiterunner binary."""
    print("=" * 50)
    print("Raptor - Kiterunner Setup")
    print("=" * 50)
    print()

    kr_path = install_kiterunner()

    print()
    if kr_path:
        print(f"✓ Kiterunner ready: {kr_path}")
        print("\nWordlists are fetched remotely from Assetnote CDN.")
        print("No local wordlist download needed.")
    else:
        print("✗ Kiterunner installation failed")
        print("\nManual install: https://github.com/assetnote/kiterunner")

    return kr_path


if __name__ == "__main__":
    try:
        result = main()
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFailed: {e}")
        sys.exit(1)
