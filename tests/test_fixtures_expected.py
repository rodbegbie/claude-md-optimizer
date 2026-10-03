import json
import shutil

import pytest
from test_fixtures_wellformed import CASES, CHECK_IDS, FIXTURES


@pytest.mark.parametrize("case", sorted(CASES))
def test_fixture_expected_ids(case, tmp_path, run_cli):
    project = tmp_path / "project"
    shutil.copytree(FIXTURES / case / "project", project)
    expected = json.loads((FIXTURES / case / "expected.json").read_text())
    ids = {f["check_id"] for f in run_cli(project)["findings"]}
    assert set(expected["must_include"]) <= ids
    assert not set(expected["must_exclude"]) & ids
    if case == "clean":
        assert not CHECK_IDS & ids
