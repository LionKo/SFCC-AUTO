from pathlib import Path
import runpy

TARGET = Path(__file__).resolve().parent / "tools" / "make_save_list_template.py"
runpy.run_path(str(TARGET), run_name="__main__")
