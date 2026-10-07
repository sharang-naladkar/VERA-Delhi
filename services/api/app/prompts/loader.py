"""Prompt Loader and Versioning Manager for VERA Investigator."""

from functools import lru_cache
from pathlib import Path

PROMPTS_ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=32)
def load_prompt_template(category: str, template_name: str) -> tuple[str, str]:
    """
    Loads a versioned prompt template from the app/prompts directory.

    Args:
        category: Subdirectory name (e.g., 'investigator')
        template_name: Filename without extension (e.g., 'entity_extraction_v1')

    Returns:
        tuple[str, str]: (raw_template_string, version_string)
    """
    prompt_path = PROMPTS_ROOT / category / f"{template_name}.txt"
    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt template '{prompt_path}' does not exist.")

    template_content = prompt_path.read_text(encoding="utf-8")

    # Extract version string (e.g. 'v1' from 'entity_extraction_v1')
    version = "v1"
    parts = template_name.split("_")
    if parts and parts[-1].startswith("v") and parts[-1][1:].isdigit():
        version = parts[-1]

    return template_content, version


def format_prompt(category: str, template_name: str, **kwargs: str) -> tuple[str, str]:
    """
    Loads and formats a versioned prompt template.

    Returns:
        tuple[str, str]: (formatted_prompt_text, version_string)
    """
    raw_template, version = load_prompt_template(category, template_name)
    formatted = raw_template.format(**kwargs)
    return formatted, version
