import json
import subprocess

import pytest


@pytest.mark.validate_env
def test_docker_python_availability(problems_metadata_path):
    """Test that a docker container has Python available as 'python' command."""
    with open(problems_metadata_path) as f:
        metadata = json.load(f)

    bash_problems_images = [p["image"] for p in metadata["problem_set"]["problems"] if "bash" in p["required_tools"]]

    if not bash_problems_images:
        pytest.skip("No problems require bash tool")

    for image in bash_problems_images:
        # Check if 'python' command exists
        result = subprocess.run(
            [
                "docker",
                "run",
                "-i",
                image,
                "which",
                "python",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # If 'python' doesn't exist, check if 'python3' exists
            python3_result = subprocess.run(
                [
                    "docker",
                    "run",
                    "-i",
                    image,
                    "which",
                    "python3",
                ],
                capture_output=True,
                text=True,
            )

            if python3_result.returncode == 0:
                raise AssertionError(
                    f"The container {image} must have `python` on the path. "
                    f"You can probably alias `python3` to `python` in your container, as `python3` exists in the container"
                )
            else:
                raise AssertionError(f"The container {image} must have `python` on the path")
        else:
            assert result.stdout.strip(), f"The container {image} must have `python` on the path"

        print(f"✓ Python command found in {image}")
