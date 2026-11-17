"""Contracts for documentation staging, cleanup, and maintained CLI recipes."""

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

import docs
from docs_assets import DOC_FILES, GITHUB_DOC_FILES, STAGED_NAMES, GENERATED_DOC_FILES


@pytest.mark.parametrize("target,expected", [
    ("README.md#overview", "project_readme.md#overview"),
    ("./documentation/planning/GABM_Refactor_Plan.md", "GABM_Refactor_Plan.md"),
    ("documentation/guides/Code_Tour.md", "Code_Tour.md"),
    ("documentation/guides/AIRE_Quickstart.md", "AIRE_Quickstart.md"),
    ("src/cag/abm/attributes/politics.py", docs.REPOSITORY_URL + "src/cag/abm/attributes/politics.py"),
    ("tests/test_gabm_compatibility.py", docs.REPOSITORY_URL + "tests/test_gabm_compatibility.py"),
    ("requirements-dev.txt", "requirements-dev.txt"),
    ("#overview", "#overview"),
    ("https://example.org/README.md", "https://example.org/README.md"),
    ("missing-guide.md", "missing-guide.md"),
])
def test_staged_links(target, expected):
    assert docs.update_links(f"[link]({target})") == f"[link]({expected})"


def test_copy_and_cleanup_preserve_authored_sources(tmp_path, monkeypatch):
    root = tmp_path
    staged = root / "docs"
    staged.mkdir()
    index = staged / "README.md"
    index.write_text("Authored documentation index\n")
    (root / ".github").mkdir()
    for name in DOC_FILES:
        source = root / name
        source.parent.mkdir(parents=True, exist_ok=True)
        project_link = os.path.relpath(root / "README.md", source.parent).replace(os.sep, "/")
        source.write_text(
            "<!DOCTYPE html><html><body>Handover</body></html>\n"
            if name.endswith(".html") else f"# {name}\n\n[project]({project_link})\n"
        )
    for name in GITHUB_DOC_FILES:
        (root / ".github" / name).write_text(f"# {name}\n")
    monkeypatch.setattr(docs, "ROOT", str(root))
    monkeypatch.setattr(docs, "DOCS", str(staged))
    before = {root / name: (root / name).read_bytes() for name in DOC_FILES}
    docs.main()
    assert index.read_text() == "Authored documentation index\n"
    assert (staged / STAGED_NAMES["README.md"]).exists()
    assert (staged / "DEV_GUIDE.md").exists()
    assert "[project](project_readme.md)" in (staged / "AIRE_Quickstart.md").read_text()
    assert "[project](project_readme.md)" in (staged / "GABM_Refactor_Plan.md").read_text()
    for name in ("requirements.txt", "requirements-dev.txt"):
        mirror = (staged / name.replace(".txt", ".md")).read_text()
        assert "```text\n" + before[root / name].decode() + "\n```" in mirror
    for name in DOC_FILES:
        if name.startswith("documentation/"):
            if name.endswith(".html"):
                assert (staged / STAGED_NAMES[name]).read_bytes() == before[root / name]
                continue
            relative = os.path.relpath(
                staged / STAGED_NAMES["README.md"],
                (staged / STAGED_NAMES[name]).parent,
            ).replace(os.sep, "/")
            assert f"[project]({relative})" in (
                staged / STAGED_NAMES[name]
            ).read_text()

    script = Path(docs.__file__).with_name("docs-clean.py").read_text()
    script = script.replace(
        'ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))',
        f"ROOT = {str(root)!r}",
    )
    subprocess.run([sys.executable, "-c", script], check=True)
    assert index.read_text() == "Authored documentation index\n"
    assert all(not (staged / STAGED_NAMES.get(name, name)).exists() for name in DOC_FILES)
    assert all(not (staged / name).exists() for name in GENERATED_DOC_FILES)
    assert all(path.read_bytes() == content for path, content in before.items())


@pytest.mark.parametrize("target,expected", [
    ("AIRE_HPC_repo_primer.md", "AIRE_HPC_repo_primer.md"),
    ("../../DEV_QUICKSTART.md#setup", "DEV_QUICKSTART.md#setup"),
    ("../../scripts/hpc/aire/run.sh", docs.REPOSITORY_URL + "scripts/hpc/aire/run.sh"),
    ("Code_Tour.md", "Code_Tour.md"),
    ("Simulation_Configuration_Guide.md#layer-2", "Simulation_Configuration_Guide.md#layer-2"),
    ("../research/Model_Design.md", "Model_Design.md"),
    ("../../../outside.md", "../../../outside.md"),
])
def test_nested_authored_links(target, expected):
    assert docs.update_links(
        f"[link]({target})", "documentation/guides/AIRE_Quickstart.md",
    ) == f"[link]({expected})"


def test_staged_guide_names_are_unique():
    names = [STAGED_NAMES.get(name, name) for name in DOC_FILES]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("target,expected", [
    ("research_notes.md", "research_notes.md"),
    ("../guides/Run_Output_Guide.md", "Run_Output_Guide.md"),
    ("../../data/fixtures/cag_integration_baseline.json",
     docs.REPOSITORY_URL + "data/fixtures/cag_integration_baseline.json"),
    ("../../USER_GUIDE.md", "USER_GUIDE.md"),
    ("Climate%20Policy%20Research%20for%20Agent-Based%20Model.md",
     "supplementary_docs/Climate%20Policy%20Research%20for%20Agent-Based%20Model.md"),
])
def test_research_source_links(target, expected):
    assert docs.update_links(
        f"[link]({target})", "documentation/research/result_report.md",
    ) == f"[link]({expected})"


@pytest.mark.parametrize("target,expected", [
    ("../research/Model_Design.md#history", "../Model_Design.md#history"),
    ("../guides/Code_Tour.md", "../Code_Tour.md"),
    ("github_issues_v2.md", "github_issues_v2.md"),
    ("../research/Literature_Political_Exposure.md", "Literature_Political_Exposure.md"),
    ("../../src/cag/abm/agent.py", docs.REPOSITORY_URL + "src/cag/abm/agent.py"),
])
def test_nested_staged_archive_links(target, expected):
    assert docs.update_links(
        f"[link]({target})", "documentation/archive/github_issues.md",
    ) == f"[link]({expected})"


def _aire_submission_examples():
    root = Path(__file__).resolve().parents[1]
    examples = []
    for filename in ("AIRE_Quickstart.md", "AIRE_HPC_repo_primer.md"):
        text = (root / "documentation/guides" / filename).read_text()
        for block in re.findall(r"```bash\n(.*?)```", text, re.DOTALL):
            for line in block.replace("\\\n", " ").splitlines():
                tokens = shlex.split(line, comments=True)
                if "sbatch" not in tokens or "scripts/hpc/aire/run.sh" not in tokens:
                    continue
                index = tokens.index("scripts/hpc/aire/run.sh")
                examples.append((filename, tokens[index + 1:]))
    return examples


@pytest.mark.parametrize("filename,arguments", _aire_submission_examples())
def test_aire_documented_submissions_resolve_without_llm(filename, arguments):
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "-m", "cag", *arguments, "--dry-run"],
        cwd=root, capture_output=True, text=True,
    )
    assert result.returncode == 0, f"{filename}: {result.stderr}"
    config = json.loads(result.stdout)
    if "--preset" in arguments:
        preset = arguments[arguments.index("--preset") + 1]
        citizens, days = {"smoke": (10, 2), "r14_canonical": (50, 5)}[preset]
        if "--n-citizens" in arguments:
            citizens = int(arguments[arguments.index("--n-citizens") + 1])
        if "--days" in arguments:
            days = int(arguments[arguments.index("--days") + 1])
        peers = (
            int(arguments[arguments.index("--k-peers") + 1])
            if "--k-peers" in arguments else 0
        )
        assert (config["n_citizens"], len(config["days"])) == (citizens, days)
        assert config["k_peers_per_day"] == peers


def test_aire_archive_body_is_preserved():
    root = Path(__file__).resolve().parents[1]
    text = (root / "documentation/archive/RunningLLMsOnAire.md").read_text()
    assert "Historical Aire article draft" in text
    assert "John Hodrien, Jo Kershaw, Andy Turner" in text
    assert "UKRI2043" in text
