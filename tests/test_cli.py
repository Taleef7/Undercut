import sys
import pytest
from ingest.run_pipeline import build_parser, main


def test_parser_bootstrap_command():
    parser = build_parser()
    args = parser.parse_args(["bootstrap", "--source", "jolpica", "--seasons", "2024"])
    assert args.command == "bootstrap"
    assert args.source == "jolpica"
    assert args.seasons == [2024]


def test_parser_fetch_weekend_with_force():
    parser = build_parser()
    args = parser.parse_args(["fetch-weekend", "--season", "2024", "--round", "21", "--force"])
    assert args.command == "fetch-weekend"
    assert args.force is True


def test_parser_normalize_with_session():
    parser = build_parser()
    args = parser.parse_args(["normalize", "--season", "2024", "--round", "21", "--session", "Q"])
    assert args.command == "normalize"
    assert args.session == "Q"


def test_parser_normalize_defaults_to_race():
    parser = build_parser()
    args = parser.parse_args(["normalize", "--season", "2024", "--round", "21"])
    assert args.session == "R"


def test_parser_build_race_state():
    parser = build_parser()
    args = parser.parse_args(["build-race-state", "--season", "2024", "--round", "21"])
    assert args.command == "build-race-state"


def test_parser_validate():
    parser = build_parser()
    args = parser.parse_args(["validate", "--season", "2024", "--round", "21"])
    assert args.command == "validate"


def test_main_requires_command(capsys):
    with pytest.raises(SystemExit):
        main([])
