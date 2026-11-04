"""加载 CityEye 专用系统提示词。"""

from pathlib import Path

PROMPT_FILE = Path(__file__).with_name("prompts") / "cityeye_system.md"


def load_system_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8").strip()
