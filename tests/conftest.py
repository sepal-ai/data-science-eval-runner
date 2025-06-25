import pytest


def pytest_addoption(parser):
    parser.addoption("--problems-metadata-path", default=None, help="The path to the problems metadata file")


@pytest.fixture
def problems_metadata_path(request):
    key = request.config.getoption("--problems-metadata-path")

    if not key:
        pytest.fail(
            "No problems metadata path provided, to run this test, you need to provide --problems-metadata-path when running pytest, e.g. `pytest --problems-metadata-path=path/to/problems-metadata.json`"
        )

    return key
