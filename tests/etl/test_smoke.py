from pathlib import Path
from src.etl.loader import RAW_DIR, SUPPORTING_DIR, CORE_FILES, SUPPORTING_FILES


def test_core_files_exist():
    """Verify all 7 core Excel files exist in data/raw/."""
    for f in CORE_FILES:
        assert (RAW_DIR / f).exists(), f"Missing core file: {f}"


def test_supporting_files_exist():
    """Verify all 5 supporting Excel files exist in data/supporting/."""
    for f in SUPPORTING_FILES:
        assert (SUPPORTING_DIR / f).exists(), f"Missing supporting file: {f}"
