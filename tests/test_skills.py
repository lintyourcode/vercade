from pathlib import Path

import pytest

from vercade.skills import load_skills


def make_skill(library: Path, name: str, description: str = "Do something") -> Path:
    skill = library / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\nInstructions for {name}.\n"
    )
    return skill


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    return home


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    return project


def test_load_skills_without_standard_directories_returns_none(home, project):
    assert load_skills() is None


def test_load_skills_scans_standard_user_and_project_directories(home, project):
    libraries = [
        home / ".vercade" / "skills",
        home / ".agents" / "skills",
        project / ".vercade" / "skills",
        project / ".agents" / "skills",
    ]
    for index, library in enumerate(libraries):
        make_skill(library, f"skill-{index}")
    # Not a standard location
    make_skill(home / ".claude" / "skills", "claude-only")

    skills = load_skills()

    assert skills is not None
    assert list(skills.directories) == libraries


def test_load_skills_skips_missing_standard_directories(home, project):
    make_skill(project / ".agents" / "skills", "only-one")

    skills = load_skills()

    assert skills is not None
    assert list(skills.directories) == [project / ".agents" / "skills"]


def test_load_skills_with_duplicate_names_raises(home, project):
    make_skill(home / ".agents" / "skills", "dupe")
    make_skill(project / ".agents" / "skills", "dupe")

    with pytest.raises(ValueError, match="Duplicate skill name 'dupe'"):
        load_skills()
