"""
Skill management for Invar extension skills.

LX-07: Extension Skills Architecture
- List available extension skills from registry
- Add/remove skills to/from project
- Update installed skills from templates
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from returns.result import Failure, Result, Success

if TYPE_CHECKING:
    from rich.console import Console


SKILLS_REGISTRY = "extensions/_registry.yaml"
SKILLS_DIR = "extensions"
PROJECT_SKILLS_DIR = ".claude/skills"


@dataclass
class SkillInfo:
    """Information about an extension skill."""

    name: str
    description: str
    tier: str
    isolation: bool
    status: str  # "available", "pending_discussion", "installed"
    files: list[str]


def get_templates_path() -> Path:
    """Get the path to Invar templates directory."""
    # Navigate from this file to templates/skills/
    return Path(__file__).parent.parent / "templates" / "skills"


def load_registry() -> Result[dict, str]:
    """Load the extension skills registry."""
    registry_path = get_templates_path() / SKILLS_REGISTRY

    if not registry_path.exists():
        return Failure(f"Registry not found: {registry_path}")

    try:
        content = registry_path.read_text()
        data = yaml.safe_load(content)
        return Success(data)
    except Exception as e:
        return Failure(f"Failed to parse registry: {e}")


# @shell_complexity: Iterates registry entries and checks installed status
def list_skills(
    project_path: Path, console: Console
) -> Result[list[SkillInfo], str]:
    """
    List all available extension skills.

    Returns both available and installed skills with their status.
    """
    registry_result = load_registry()
    if isinstance(registry_result, Failure):
        return registry_result

    registry = registry_result.unwrap()
    extensions = registry.get("extensions", {})

    # Check which skills are installed
    installed_dir = project_path / PROJECT_SKILLS_DIR
    installed_skills = set()
    if installed_dir.exists():
        for skill_dir in installed_dir.iterdir():
            if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
                # Check if it's an extension (not a core skill)
                if (skill_dir / "SKILL.md").exists():
                    installed_skills.add(skill_dir.name)

    skills = []
    for name, info in extensions.items():
        status = info.get("status", "available")
        if name in installed_skills:
            status = "installed"

        skills.append(
            SkillInfo(
                name=name,
                description=info.get("description", ""),
                tier=info.get("tier", "T0"),
                isolation=info.get("isolation", False),
                status=status,
                files=info.get("files", ["SKILL.md"]),
            )
        )

    return Success(skills)


# @shell_complexity: Validates skill, copies files/directories with error recovery
def add_skill(
    skill_name: str, project_path: Path, console: Console
) -> Result[str, str]:
    """
    Add an extension skill to the project.

    Copies skill files from templates to .claude/skills/<name>/
    """
    # Load registry to validate skill exists
    registry_result = load_registry()
    if isinstance(registry_result, Failure):
        return registry_result

    registry = registry_result.unwrap()
    extensions = registry.get("extensions", {})

    if skill_name not in extensions:
        available = ", ".join(extensions.keys())
        return Failure(f"Unknown skill: {skill_name}. Available: {available}")

    skill_info = extensions[skill_name]

    # Check status
    if skill_info.get("status") == "pending_discussion":
        return Failure(
            f"Skill '{skill_name}' is pending discussion (T1). "
            "It will be available in a future release."
        )

    # Source and destination paths
    source_dir = get_templates_path() / SKILLS_DIR / skill_name
    dest_dir = project_path / PROJECT_SKILLS_DIR / skill_name

    if not source_dir.exists():
        return Failure(f"Skill template not found: {source_dir}")

    if dest_dir.exists():
        return Failure(
            f"Skill already installed: {skill_name}. "
            "Use 'invar skill update' to update or 'invar skill remove' first."
        )

    # Copy skill files
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)

        for file_path in skill_info.get("files", ["SKILL.md"]):
            src = source_dir / file_path
            dst = dest_dir / file_path

            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                console.print(f"  [dim]Copied: {file_path}[/dim]")
            elif src.is_dir():
                # Handle directory (e.g., patterns/)
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                console.print(f"  [dim]Copied: {file_path}/[/dim]")

        return Success(f"Skill '{skill_name}' installed successfully")

    except Exception as e:
        # Clean up on failure
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        return Failure(f"Failed to install skill: {e}")


def remove_skill(
    skill_name: str, project_path: Path, console: Console
) -> Result[str, str]:
    """
    Remove an extension skill from the project.
    """
    dest_dir = project_path / PROJECT_SKILLS_DIR / skill_name

    if not dest_dir.exists():
        return Failure(f"Skill not installed: {skill_name}")

    # Protect core skills
    core_skills = {"develop", "review", "investigate", "propose", "guard", "audit"}
    if skill_name in core_skills:
        return Failure(
            f"Cannot remove core skill: {skill_name}. "
            "Only extension skills can be removed."
        )

    try:
        shutil.rmtree(dest_dir)
        return Success(f"Skill '{skill_name}' removed successfully")
    except Exception as e:
        return Failure(f"Failed to remove skill: {e}")


# @shell_complexity: Validates and copies multiple files/directories
def update_skill(
    skill_name: str, project_path: Path, console: Console
) -> Result[str, str]:
    """
    Update an installed extension skill from templates.

    Replaces skill files with latest versions from Invar templates.
    """
    dest_dir = project_path / PROJECT_SKILLS_DIR / skill_name

    if not dest_dir.exists():
        return Failure(
            f"Skill not installed: {skill_name}. "
            "Use 'invar skill add' to install first."
        )

    # Load registry
    registry_result = load_registry()
    if isinstance(registry_result, Failure):
        return registry_result

    registry = registry_result.unwrap()
    extensions = registry.get("extensions", {})

    if skill_name not in extensions:
        return Failure(
            f"Skill '{skill_name}' is not an extension skill. "
            "Only extension skills can be updated this way."
        )

    skill_info = extensions[skill_name]
    source_dir = get_templates_path() / SKILLS_DIR / skill_name

    if not source_dir.exists():
        return Failure(f"Skill template not found: {source_dir}")

    try:
        # Update each file
        for file_path in skill_info.get("files", ["SKILL.md"]):
            src = source_dir / file_path
            dst = dest_dir / file_path

            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                console.print(f"  [dim]Updated: {file_path}[/dim]")
            elif src.is_dir():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                console.print(f"  [dim]Updated: {file_path}/[/dim]")

        return Success(f"Skill '{skill_name}' updated successfully")

    except Exception as e:
        return Failure(f"Failed to update skill: {e}")
