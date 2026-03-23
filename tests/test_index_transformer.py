from typer.testing import CliRunner
from gide_search_v2.cli import app
from pathlib import Path
import json
runner = CliRunner()


def test_index_transform_default(tmpdir):


    result = runner.invoke(
        app, [ "data", "transform-to-index", str(Path(__file__).parent / "data/gide_search_ro_crate"), "-o", str(tmpdir) ]
    )

    assert result.exit_code == 0

    with open(tmpdir / "index.json") as f:
        output_index = json.loads(f.read())
    
    expected_index_path = Path(__file__).parent / "data/index_document/example_ro_crate_index.json"
    with open(expected_index_path) as f:
        expected_index = json.loads(f.read())

    assert expected_index == output_index


