import json
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

RENDERER_PATH = Path(__file__).with_name("render_manual.py")
RENDERER_SPEC = importlib.util.spec_from_file_location("render_manual", RENDERER_PATH)
assert RENDERER_SPEC is not None and RENDERER_SPEC.loader is not None
render_manual = importlib.util.module_from_spec(RENDERER_SPEC)
sys.modules["render_manual"] = render_manual
RENDERER_SPEC.loader.exec_module(render_manual)


def minimal_analysis() -> dict[str, Any]:
    return {
        "app_name": "testapp",
        "version": "1.0.0",
        "framework_hint": "vue3",
        "dev_server_url": "http://localhost:5173",
        "app_purpose": "测试用应用",
        "routes": [
            {
                "path": "/users",
                "title": "用户管理",
                "accessible": True,
                "discovered_via": "menu",
                "elements": [
                    {"element_id": "el_001", "type": "button", "text": "新建", "action": "open_create_modal"}
                ],
                "flows": [
                    {
                        "flow_id": "flow_001",
                        "name": "新建用户",
                        "steps": [{"action": "click", "element_id": "el_001", "expected_outcome": "弹窗打开"}],
                    }
                ],
            }
        ],
        "auth": None,
        "faqs": [],
        "generated_at": "2026-06-21T10:00:00Z",
    }


def sample_analysis_3_steps() -> dict[str, Any]:
    data = minimal_analysis()
    data["routes"][0]["elements"] = [
        {"element_id": "el_001", "type": "button", "text": "新建", "action": "open_create_modal"},
        {"element_id": "el_002", "type": "input", "placeholder": "姓名", "action": "fill_name"},
        {"element_id": "el_003", "type": "button", "text": "保存", "action": "submit"},
    ]
    data["routes"][0]["flows"][0]["steps"] = [
        {"action": "click", "element_id": "el_001", "expected_outcome": "弹窗打开"},
        {"action": "fill", "element_id": "el_002", "expected_outcome": "输入完成"},
        {"action": "click", "element_id": "el_003", "expected_outcome": "保存成功"},
    ]
    return data


def default_fingerprint() -> dict[str, Any]:
    return {
        "chapter_depth": 2,
        "step_density": "medium",
        "screenshot_frequency": "medium",
        "table_preference": "minimal",
        "faq_style": "short",
        "sources": {
            "chapter_depth": "default",
            "step_density": "default",
            "screenshot_frequency": "default",
            "table_preference": "default",
            "faq_style": "default",
        },
    }


def locator(value: str) -> dict[str, str]:
    return {"strategy": "text", "value": value}


def manifest_with_n_screenshots(n: int, status: str = "success", title: str = "用户管理", path: str = "/users") -> dict[str, Any]:
    actions = []
    for i in range(n):
        actions.append(
            {
                "action_id": f"shot_{i}",
                "type": "screenshot",
                "status": status,
                "output_path": f"imgs/users_{i}.png",
                "primary_locator": None,
                "elapsed_ms": 100,
                **({"error": "selector timeout"} if status == "failed" else {}),
            }
        )
        if i > 0:
            actions.append(
                {
                    "action_id": f"act_{i}",
                    "type": "click",
                    "status": "success",
                    "output_path": None,
                    "primary_locator": locator("新建"),
                    "elapsed_ms": 50,
                }
            )
    if n == 1:
        actions.append(
            {
                "action_id": "act_1",
                "type": "click",
                "status": "success",
                "output_path": None,
                "primary_locator": locator("新建"),
                "elapsed_ms": 50,
            }
        )
    return {
        "app_name": "testapp",
        "executor_error": None,
        "tasks": [{"task_id": "task_001", "page_title": title, "url": f"http://localhost:5173{path}", "actions": actions}],
    }


def write_inputs(tmp_path: Path, analysis: dict[str, Any], manifest: dict[str, Any], fingerprint: dict[str, Any]) -> Path:
    input_dir = tmp_path / "input"
    input_dir.mkdir(parents=True)
    (input_dir / "analysis.json").write_text(json.dumps(analysis, ensure_ascii=False), encoding="utf-8")
    (input_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (input_dir / "style-fingerprint.json").write_text(json.dumps(fingerprint, ensure_ascii=False), encoding="utf-8")
    return input_dir


def run_renderer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    analysis: dict[str, Any],
    manifest: dict[str, Any],
    fingerprint: dict[str, Any],
) -> Path:
    input_dir = write_inputs(tmp_path, analysis, manifest, fingerprint)
    output_dir = tmp_path / "output"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "render_manual.py",
            "--analysis",
            str(input_dir / "analysis.json"),
            "--manifest",
            str(input_dir / "manifest.json"),
            "--style-fingerprint",
            str(input_dir / "style-fingerprint.json"),
            "--output-dir",
            str(output_dir),
        ],
    )
    assert render_manual.main() == 0
    return output_dir


def read_chunks(output_dir: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in (output_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]


def test_minimal_analysis_produces_all_schema_valid_outputs(tmp_path, monkeypatch):
    output_dir = run_renderer(tmp_path, monkeypatch, minimal_analysis(), manifest_with_n_screenshots(1), default_fingerprint())

    assert (output_dir / "操作手册.md").exists()
    assert (output_dir / "chunks.jsonl").exists()
    assert (output_dir / "llms.txt").exists()
    chunks = read_chunks(output_dir)
    assert chunks
    assert all("page_content" in chunk and "metadata" in chunk for chunk in chunks)
    assert (output_dir / "llms.txt").read_text(encoding="utf-8").splitlines()[0].startswith("# ")
    assert (output_dir / "操作手册.md").read_text(encoding="utf-8").splitlines()[0].startswith("# ")


def test_three_step_flow_produces_page_load_and_three_step_chunks(tmp_path, monkeypatch):
    output_dir = run_renderer(tmp_path, monkeypatch, sample_analysis_3_steps(), manifest_with_n_screenshots(4), default_fingerprint())

    chunks = read_chunks(output_dir)
    assert len([chunk for chunk in chunks if chunk["metadata"]["module"] == "用户管理"]) == 4
    assert [chunk["metadata"]["subsection"] for chunk in chunks] == ["page_load", "step", "step", "step"]
    assert chunks[1]["metadata"]["screenshots"] == ["imgs/users_1.png"]
    assert chunks[2]["metadata"]["screenshots"] == ["imgs/users_2.png"]
    assert chunks[3]["metadata"]["screenshots"] == ["imgs/users_3.png"]
    assert "保存" in chunks[3]["metadata"]["element_texts"]


def test_failed_screenshot_renders_placeholder_and_empty_chunk_screenshots(tmp_path, monkeypatch):
    manifest = manifest_with_n_screenshots(1, status="failed")
    output_dir = run_renderer(tmp_path, monkeypatch, minimal_analysis(), manifest, default_fingerprint())

    md = (output_dir / "操作手册.md").read_text(encoding="utf-8")
    chunks = read_chunks(output_dir)
    step_chunk = next(chunk for chunk in chunks if chunk["metadata"]["subsection"] == "step")
    assert "> ⚠️ 截图失败：selector timeout" in md
    assert step_chunk["metadata"]["screenshots"] == []


def test_deterministic_outputs_are_byte_identical(tmp_path, monkeypatch):
    analysis = sample_analysis_3_steps()
    manifest = manifest_with_n_screenshots(4)
    fingerprint = default_fingerprint()
    first = run_renderer(tmp_path / "a", monkeypatch, analysis, manifest, fingerprint)
    second = run_renderer(tmp_path / "b", monkeypatch, analysis, manifest, fingerprint)

    for name in ("操作手册.md", "chunks.jsonl", "llms.txt"):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_atomic_rollback_removes_temps_and_finals_on_partial_failure(tmp_path, monkeypatch):
    analysis = minimal_analysis()
    manifest = manifest_with_n_screenshots(1)
    fingerprint = default_fingerprint()
    render_manual.validate_analysis(analysis)
    render_manual.validate_manifest(manifest)
    ir = render_manual.build_ir(analysis, manifest, fingerprint)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    def fail_chunks(_ir: dict[str, Any], _output_path: Path) -> int:
        raise OSError("disk full")

    monkeypatch.setattr(render_manual, "render_chunks", fail_chunks)
    with pytest.raises(OSError):
        render_manual.write_outputs_atomic(ir, output_dir)

    assert not list(output_dir.glob("*.tmp"))
    assert not (output_dir / "操作手册.md").exists()
    assert not (output_dir / "chunks.jsonl").exists()
    assert not (output_dir / "llms.txt").exists()


def test_consistency_error_prevents_final_rename(tmp_path, monkeypatch):
    analysis = minimal_analysis()
    manifest = manifest_with_n_screenshots(1)
    fingerprint = default_fingerprint()
    ir = render_manual.build_ir(analysis, manifest, fingerprint)
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    def bad_llms(_ir: dict[str, Any], output_path: Path) -> int:
        output_path.write_text("# testapp 操作手册\n\n## 主要功能模块\n", encoding="utf-8")
        return 3

    monkeypatch.setattr(render_manual, "render_llms_txt", bad_llms)
    with pytest.raises(render_manual.ConsistencyError):
        render_manual.write_outputs_atomic(ir, output_dir)

    assert not list(output_dir.glob("*.tmp"))
    assert not (output_dir / "操作手册.md").exists()
    assert not (output_dir / "chunks.jsonl").exists()
    assert not (output_dir / "llms.txt").exists()


def test_auth_metadata_does_not_render_login_module_when_login_route_excluded(tmp_path, monkeypatch):
    analysis = minimal_analysis()
    analysis["auth"] = {
        "login_route": "/login",
        "form_fields": [{"name": "username", "placeholder": "用户名", "type": "text"}],
        "post_login_route": "/dashboard",
    }
    output_dir = run_renderer(tmp_path, monkeypatch, analysis, manifest_with_n_screenshots(1), default_fingerprint())

    md = (output_dir / "操作手册.md").read_text(encoding="utf-8")
    chunks = read_chunks(output_dir)
    assert "模块1：登录" not in md
    assert all(chunk["metadata"]["subsection"] != "auth" for chunk in chunks)
    assert all(chunk["metadata"]["module"] != "登录" for chunk in chunks)


def test_renderer_is_stateless_and_renders_all_routes_from_new_analysis(tmp_path, monkeypatch):
    analysis = minimal_analysis()
    routes = []
    tasks = []
    for i in range(4):
        route = json.loads(json.dumps(analysis["routes"][0]))
        route["path"] = f"/module-{i}"
        route["title"] = f"模块{i}"
        route["elements"][0]["element_id"] = f"el_{i}"
        route["flows"][0]["steps"][0]["element_id"] = f"el_{i}"
        routes.append(route)
        task_manifest = manifest_with_n_screenshots(1, title=f"模块{i}", path=f"/module-{i}")
        tasks.append(task_manifest["tasks"][0])
    analysis["routes"] = routes
    manifest = {"app_name": "testapp", "executor_error": None, "tasks": tasks}
    output_dir = run_renderer(tmp_path, monkeypatch, analysis, manifest, default_fingerprint())

    md = (output_dir / "操作手册.md").read_text(encoding="utf-8")
    chunks = read_chunks(output_dir)
    assert md.count("### 模块") == 4
    assert len({chunk["metadata"]["module"] for chunk in chunks if chunk["metadata"]["subsection"] == "page_load"}) == 4


def test_cli_help_works_under_pytest_config():
    result = subprocess.run(
        ["uv", "run", "python", "scripts/render_manual.py", "--help"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--analysis" in result.stdout
    assert "--manifest" in result.stdout
