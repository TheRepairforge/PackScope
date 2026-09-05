"""Config tests: app-data dir + settings round-trip."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packscope import config


def test_app_data_dir_uses_appdata(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    d = config.app_data_dir()
    if sys.platform.startswith("win"):
        assert d == tmp_path / "PackScope"
    assert d.exists()


def test_portable_marker_redirects_data_next_to_exe(tmp_path, monkeypatch):
    exe = tmp_path / "PackScope.exe"
    exe.write_text("")
    (tmp_path / "portable.txt").write_text("")
    monkeypatch.setattr(config.sys, "frozen", True, raising=False)
    monkeypatch.setattr(config.sys, "executable", str(exe))
    d = config.app_data_dir()
    assert d == tmp_path / "data"
    assert d.exists()


def test_no_portable_marker_uses_appdata(tmp_path, monkeypatch):
    exe = tmp_path / "PackScope.exe"
    exe.write_text("")
    monkeypatch.setattr(config.sys, "frozen", True, raising=False)
    monkeypatch.setattr(config.sys, "executable", str(exe))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setattr(config.Path, "home", classmethod(lambda cls: tmp_path / "home"))
    d = config.app_data_dir()
    assert d != tmp_path / "data"


def test_settings_roundtrip_preserves_unknown_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setattr(config.Path, "home", classmethod(lambda cls: tmp_path))

    s = config.Settings(serial_port="COM7", temp_unit="F", csv_columns="makita")
    s.extra = {"future_key": 123}
    config.save_settings(s)

    s2 = config.load_settings()
    assert s2.serial_port == "COM7"
    assert s2.temp_unit == "F"
    assert s2.csv_columns == "makita"
    assert s2.extra.get("future_key") == 123
    assert s2.resolved_db_path() == config.default_db_path()


def test_defaults_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    s = config.load_settings()
    assert s.serial_port == ""
    assert s.temp_unit == "C"
    assert s.csv_columns == "full"
