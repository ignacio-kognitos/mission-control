"""Allow running as: uv run python -m mission_control"""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    main_py = Path(__file__).parent.parent / "main.py"
    subprocess.run([sys.executable, str(main_py)])
