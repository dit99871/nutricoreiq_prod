import sys
from pathlib import Path

# добавляем корень проекта в путь
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))
