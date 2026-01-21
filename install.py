#!/usr/bin/env python3
"""
Installation script for SimpleSyntenyViewer dependencies.
Installs minimap2 and samtools using conda/mamba if available.
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

ENV_NAME = "simplesyntenyviewer"
REQUIRED_TOOLS = ["minimap2"]
OPTIONAL_TOOLS = ["samtools"]  # Optional - speeds up FASTA indexing but not required
CONDA_PACKAGES = ["minimap2>=2.24"]
CONDA_PACKAGES_OPTIONAL = ["samtools>=1.19"]


def check_tool_installed(tool_name: str) -> bool:
    """Check if a tool is installed and in PATH."""
    return shutil.which(tool_name) is not None


def check_all_tools() -> dict[str, bool]:
    """Check which required and optional tools are installed."""
    all_tools = {tool: check_tool_installed(tool) for tool in REQUIRED_TOOLS}
    all_tools.update({tool: check_tool_installed(tool) for tool in OPTIONAL_TOOLS})
    return all_tools


def find_conda() -> Optional[Path]:
    """Find conda or mamba executable."""
    for cmd in ["mamba", "conda", "micromamba"]:
        path = shutil.which(cmd)
        if path:
            return Path(path)
    return None


def conda_env_exists(conda_path: Path) -> bool:
    """Check if the conda environment exists."""
    try:
        result = subprocess.run(
            [str(conda_path), "env", "list"],
            capture_output=True,
            text=True,
            check=True
        )
        return ENV_NAME in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def create_conda_env(conda_path: Path, force: bool = False, include_optional: bool = True) -> bool:
    """Create conda environment with required tools."""
    if force and conda_env_exists(conda_path):
        print(f"Removing existing environment '{ENV_NAME}'...")
        subprocess.run(
            [str(conda_path), "env", "remove", "-y", "-n", ENV_NAME],
            check=False
        )
    
    if conda_env_exists(conda_path):
        print(f"Environment '{ENV_NAME}' already exists.")
        return True
    
    packages = CONDA_PACKAGES.copy()
    if include_optional:
        packages.extend(CONDA_PACKAGES_OPTIONAL)
    
    print(f"Creating conda environment '{ENV_NAME}' with {', '.join(packages)}...")
    try:
        subprocess.run(
            [
                str(conda_path),
                "create",
                "-y",
                "-n",
                ENV_NAME,
                "-c",
                "conda-forge",
                "-c",
                "bioconda",
                *packages,
            ],
            check=True
        )
        print(f"✓ Environment '{ENV_NAME}' created successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create environment: {e}")
        return False


def get_env_bin_path(conda_path: Path) -> Optional[Path]:
    """Get the bin directory of the conda environment."""
    try:
        result = subprocess.run(
            [str(conda_path), "env", "list"],
            capture_output=True,
            text=True,
            check=True
        )
        for line in result.stdout.splitlines():
            if ENV_NAME in line:
                parts = line.split()
                if len(parts) >= 2:
                    env_path = Path(parts[-1])
                    bin_path = env_path / "bin"
                    if bin_path.exists():
                        return bin_path
        # Try default location
        conda_info = subprocess.run(
            [str(conda_path), "info", "--base"],
            capture_output=True,
            text=True,
            check=True
        )
        base_path = Path(conda_info.stdout.strip())
        env_path = base_path / "envs" / ENV_NAME / "bin"
        if env_path.exists():
            return env_path
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return None


def print_activation_instructions(conda_path: Path):
    """Print instructions for activating the environment."""
    bin_path = get_env_bin_path(conda_path)
    if not bin_path:
        print("\n⚠ Could not determine environment path. Please activate manually:")
        print(f"  {conda_path} activate {ENV_NAME}")
        return
    
    print("\n" + "="*60)
    print("To use the installed tools, activate the environment:")
    print("="*60)
    print(f"  {conda_path} activate {ENV_NAME}")
    print("\nOr add to your PATH:")
    print(f"  export PATH=\"{bin_path}:$PATH\"")
    print("\nOr update your shell config (~/.bashrc, ~/.zshrc, etc.):")
    print(f"  echo 'export PATH=\"{bin_path}:$PATH\"' >> ~/.bashrc")
    print("="*60)


def install_with_conda(conda_path: Path, force: bool = False, include_optional: bool = True) -> bool:
    """Install tools using conda/mamba."""
    print(f"Using {conda_path.name} to install dependencies...")
    
    if not create_conda_env(conda_path, force=force, include_optional=include_optional):
        return False
    
    # Verify installation
    bin_path = get_env_bin_path(conda_path)
    if bin_path:
        print("\nVerifying installation...")
        for tool in REQUIRED_TOOLS:
            tool_path = bin_path / tool
            if tool_path.exists():
                print(f"  ✓ {tool} found at {tool_path}")
            else:
                print(f"  ✗ {tool} not found in environment")
                return False
        # Check optional tools
        for tool in OPTIONAL_TOOLS:
            tool_path = bin_path / tool
            if tool_path.exists():
                print(f"  ✓ {tool} found at {tool_path} (optional)")
    
    print_activation_instructions(conda_path)
    return True


def print_manual_instructions():
    """Print manual installation instructions."""
    print("\n" + "="*60)
    print("Manual Installation Instructions")
    print("="*60)
    print("\nOption 1: Install via conda/mamba (recommended):")
    print("  conda install -c bioconda minimap2 samtools")
    print("\nOption 2: Install via homebrew (macOS):")
    print("  brew install minimap2 samtools")
    print("\nOption 3: Install via apt (Linux):")
    print("  sudo apt-get install minimap2 samtools")
    print("\nOption 4: Build from source:")
    print("  - minimap2: https://github.com/lh3/minimap2")
    print("  - samtools: https://github.com/samtools/samtools")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Install minimap2 and samtools for SimpleSyntenyViewer"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate conda environment if it exists"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if tools are installed, don't install"
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove the conda environment"
    )
    parser.add_argument(
        "--no-optional",
        action="store_true",
        help="Don't install optional tools (samtools)"
    )
    args = parser.parse_args()
    
    # Check current status
    tools_status = check_all_tools()
    all_installed = all(tools_status.values())
    
    print("SimpleSyntenyViewer Dependency Checker")
    print("="*60)
    print("\nRequired tools:")
    required_installed = all(tools_status.get(tool, False) for tool in REQUIRED_TOOLS)
    for tool in REQUIRED_TOOLS:
        installed = tools_status.get(tool, False)
        status = "✓ INSTALLED" if installed else "✗ NOT FOUND"
        print(f"  {tool:15} {status}")
    
    print("\nOptional tools (recommended for faster indexing):")
    for tool in OPTIONAL_TOOLS:
        installed = tools_status.get(tool, False)
        status = "✓ INSTALLED" if installed else "○ NOT FOUND (optional)"
        print(f"  {tool:15} {status}")
    
    if required_installed:
        print("\n✓ All required tools are installed and available in PATH!")
        if args.check_only:
            return 0
        print("No installation needed.")
        return 0
    
    if args.check_only:
        print("\n⚠ Some tools are missing. Run without --check-only to install.")
        return 1
    
    if args.remove:
        conda_path = find_conda()
        if conda_path and conda_env_exists(conda_path):
            print(f"\nRemoving environment '{ENV_NAME}'...")
            subprocess.run(
                [str(conda_path), "env", "remove", "-y", "-n", ENV_NAME],
                check=False
            )
            print("✓ Environment removed.")
        else:
            print("No environment to remove.")
        return 0
    
    # Try to install
    conda_path = find_conda()
    if conda_path:
        print(f"\nFound {conda_path.name}. Attempting automatic installation...")
        if install_with_conda(conda_path, force=args.force, include_optional=not args.no_optional):
            print("\n✓ Installation complete!")
            print("\n⚠ Remember to activate the environment or add it to PATH before running the Flask app.")
            return 0
        else:
            print("\n⚠ Automatic installation failed.")
    else:
        print("\n⚠ No conda/mamba found. Cannot install automatically.")
    
    print_manual_instructions()
    return 1


if __name__ == "__main__":
    sys.exit(main())
