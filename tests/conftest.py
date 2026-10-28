"""The modules under test (logic, render, tv) import no Home Assistant code."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "custom_components" / "frame_daily_plan"))
