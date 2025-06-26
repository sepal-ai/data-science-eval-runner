import json
from pathlib import Path

import jsonschema
import pytest


@pytest.mark.validate_env
def test_metadata_conforms_to_schema(problems_metadata_path):
    """Test that the problems-metadata.json file conforms to the defined schema."""
    # Load the schema
    schema_path = Path(__file__).parent / "problems-metadata-schema.json"
    with open(schema_path) as f:
        # Our schema file contains a meta-schema that defines what a problem set should look like
        meta_schema = json.load(f)

    # Extract the actual schema for the problem_set object
    problem_set_schema = {"type": "object", **meta_schema["problem_set"]}

    # Load the metadata file
    with open(problems_metadata_path) as f:
        metadata = json.load(f)

    # Validate the metadata against the schema
    jsonschema.validate(instance=metadata["problem_set"], schema=problem_set_schema)
