import logging
from pathlib import Path

from pydantic_ai_harness import Skills

logger = logging.getLogger(__name__)

# Client-specific and cross-client skill libraries, scanned in the user's home
# directory and the current working directory. See
# https://agentskills.io/client-implementation/adding-skills-support
_LIBRARIES = (".vercade/skills", ".agents/skills")


def load_skills() -> Skills | None:
    """
    Load the Agent Skills found in the standard user-level and project-level locations.

    Returns:
        The skills, or None if none of the standard skill directories exist.
    """

    directories = [
        directory
        for scope in (Path.home(), Path.cwd())
        for library in _LIBRARIES
        if (directory := scope / library).is_dir()
    ]
    if not directories:
        return None
    logger.info("Loading skills from %s", ", ".join(map(str, directories)))
    return Skills(directories)
