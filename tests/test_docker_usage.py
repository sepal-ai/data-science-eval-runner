import os
import subprocess
from pathlib import Path


def test_docker_hello_command():
    """Test that the 'hello' command works in the Docker container."""
    result = subprocess.run(
        [
            "docker",
            "run",
            "-i",
            "taiga",
            "uv",
            "--directory",
            "/mcp_server",
            "run",
            "taiga",
            "hello",
        ],
        capture_output=True,
        text=True,
    )

    assert "Hello, World!" in result.stdout
    assert result.returncode == 0


def test_mount_local_src():
    """Test the mount local src option with a simple command."""
    repo_root = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    result = subprocess.run(
        [
            "docker",
            "run",
            "-i",
            "-v",
            f"{repo_root}/src:/mcp_server/src",
            "taiga",
            "uv",
            "--directory",
            "/mcp_server",
            "run",
            "taiga",
            "hello",
        ],
        capture_output=True,
        text=True,
    )

    assert "Hello, World!" in result.stdout
    assert result.returncode == 0
