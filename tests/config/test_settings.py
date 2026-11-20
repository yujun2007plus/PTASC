from pathlib import Path

import pytest

from ptasc.config.parse import parse_yaml_subset
from ptasc.config.paths import project_root
from ptasc.config.settings import load_settings, settings_from_mapping


def test_quoted_ramp_keeps_hash():
    parsed = parse_yaml_subset('ramp: " .:-=+*#%@"\ninvert: false\n')

    assert parsed["ramp"] == " .:-=+*#%@"
    assert parsed["invert"] is False


def test_settings_convert_whole_numbers():
    settings = settings_from_mapping(
        {"columns": 32, "char_aspect": 2, "ramp": " @", "invert": False}
    )

    assert settings.columns == 32
    assert settings.char_aspect == 2.0


def test_settings_reject_empty_ramp():
    with pytest.raises(ValueError):
        settings_from_mapping(
            {"columns": 32, "char_aspect": 2.0, "ramp": "", "invert": False}
        )


def test_repository_runtime_yaml_loads():
    root = project_root(Path(__file__))
    settings = load_settings(root / "configs" / "runtime.yaml")

    assert settings.columns == 80
    assert settings.char_aspect == 2.0
    assert settings.ramp.startswith(" ")
    assert settings.invert is False
    assert settings.video_fps == 8
    assert settings.video_max_frames == 120
    assert settings.video_max_edge == 480
