from pathlib import Path

from tooling.sync_versions import (
    update_file,
    update_json,
    update_composer_json,
    update_yaml_pubspec,
    update_xml_csproj,
    update_c_source,
    update_lua_rockspec,
)
import tooling.sync_versions as sync_versions


def test_update_json_changes_version():
    inp = '{\n  "name": "foo",\n  "version": "1.2.3"\n}\n'
    out = update_json(inp, "3.0.0", Path("dummy"))
    assert '"version": "3.0.0"' in out


def test_update_composer_json_replace_and_insert():
    inp = '{"name": "pkg", "version": "0.0.1"}\n'
    out = update_composer_json(inp, "3.0.0", Path("dummy"))
    assert '"version": "3.0.0"' in out

    inp2 = '{"name": "pkg"}\n'
    out2 = update_composer_json(inp2, "3.0.0", Path("dummy"))
    assert '"version": "3.0.0"' in out2


def test_update_yaml_pubspec_replaces_line():
    inp = "name: example\nversion: 1.2.3\n"
    out = update_yaml_pubspec(inp, "3.0.0", Path("dummy"))
    assert "version: 3.0.0" in out


def test_update_xml_csproj_replace_and_insert():
    inp = "<Project>\n  <PropertyGroup>\n    <Version>0.1.2</Version>\n  </PropertyGroup>\n</Project>"
    out = update_xml_csproj(inp, "3.0.0", Path("dummy"))
    assert "<Version>3.0.0</Version>" in out

    inp2 = "<Project>\n  <PropertyGroup>\n    <Some>v</Some>\n  </PropertyGroup>\n</Project>"
    out2 = update_xml_csproj(inp2, "3.0.0", Path("dummy"))
    assert "<Version>3.0.0</Version>" in out2


def test_update_c_source_returns_replaced():
    inp = 'const char *strling_version(void) { return "1.0.0"; }\n'
    out = update_c_source(inp, "3.0.0", Path("dummy"))
    assert 'return "3.0.0"' in out


def test_update_lua_rockspec_revision():
    inp = 'version = "1.2.3-1"\n'
    out = update_lua_rockspec(inp, "3.0.0", Path("dummy"))
    assert 'version = "3.0.0-1"' in out

    inp2 = 'version = "1.2.3"\n'
    out2 = update_lua_rockspec(inp2, "3.0.0-2", Path("dummy"))
    # when a revision is provided in the source version, it is preserved
    assert 'version = "3.0.0-2"' in out2


def test_update_file_dry_run_reports_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_versions, "ROOT_DIR", tmp_path)
    target = tmp_path / "package.json"
    target.write_text('{"version": "1.0.0"}\n', encoding="utf-8")

    assert not update_file(
        "package.json",
        "3.0.0",
        dry_run=True,
        updater_func=update_json,
    )
    assert target.read_text(encoding="utf-8") == '{"version": "1.0.0"}\n'


def test_update_file_dry_run_accepts_exact_content(tmp_path, monkeypatch):
    monkeypatch.setattr(sync_versions, "ROOT_DIR", tmp_path)
    target = tmp_path / "package.json"
    target.write_text('{"version": "3.0.0"}\n', encoding="utf-8")

    assert update_file(
        "package.json",
        "3.0.0",
        dry_run=True,
        updater_func=update_json,
    )
