import json
import subprocess

import pytest


@pytest.mark.validate_env
def test_docker_computer_deps(problems_metadata_path):
    """Test that a docker container has computer use dependencies installed if problems exist that require computer use."""
    with open(problems_metadata_path) as f:
        metadata = json.load(f)

    cu_problems_images = [p["image"] for p in metadata["problem_set"]["problems"] if "computer" in p["required_tools"]]

    if not cu_problems_images:
        pytest.skip("No problems require computer tool")

    # Required executables (commands to check with `which`)
    required_executables = [
        "convert",  # ImageMagick's main command
        "scrot",  # Screenshot tool
        "xdotool",  # X11 automation tool
    ]

    for image in cu_problems_images:
        # Check each executable
        for executable in required_executables:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "-i",
                    image,
                    "which",
                    executable,
                ],
                capture_output=True,
                text=True,
            )

            assert result.returncode == 0, (
                f"'{executable}' not found in {image}, this needs to be installed in your Docker image"
            )
            assert result.stdout.strip(), (
                f"'{executable}' command returned empty path in {image}, this needs to be installed in your Docker image"
            )
        print(f"✓ All required executables found in {image}")
