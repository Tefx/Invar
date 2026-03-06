from __future__ import annotations

import warnings

from returns.result import Success

from invar.shell.config import find_config_file, find_project_root, load_config


def test_find_config_file_warns_for_deprecated_invar_config(tmp_path) -> None:
    invar_dir = tmp_path / ".invar"
    invar_dir.mkdir()
    (invar_dir / "config.toml").write_text("[guard]\nmax_file_lines = 123\n", encoding="utf-8")

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = find_config_file(tmp_path)

    assert isinstance(result, Success)
    assert result.unwrap()[1] == "default"
    assert any("deprecated .invar/config.toml" in str(w.message) for w in captured)


def test_load_config_uses_invar_toml_fallback_when_pyproject_has_no_guard(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
    (tmp_path / "invar.toml").write_text("[guard]\nmax_file_lines = 321\n", encoding="utf-8")

    result = load_config(tmp_path)

    assert isinstance(result, Success)
    assert result.unwrap().max_file_lines == 321


def test_load_config_ignores_deprecated_invar_config_with_warning(tmp_path) -> None:
    invar_dir = tmp_path / ".invar"
    invar_dir.mkdir()
    (invar_dir / "config.toml").write_text("[guard]\nmax_file_lines = 123\n", encoding="utf-8")

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        result = load_config(tmp_path)

    assert isinstance(result, Success)
    assert result.unwrap().max_file_lines == 500
    assert any("deprecated .invar/config.toml" in str(w.message) for w in captured)


def test_find_project_root_does_not_use_invar_directory_marker(tmp_path) -> None:
    root = tmp_path / "project"
    child = root / "child"
    invar_dir = root / ".invar"
    invar_dir.mkdir(parents=True)
    child.mkdir()

    assert find_project_root(child) == child
