import os
import sys
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir)) 