import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_step(script_name):
    script_path = ROOT / "src" / script_name

    
    print(f"RUNNING: {script_name}")
    

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=ROOT,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{script_name} failed with exit code "
            f"{result.returncode}"
        )


def main():
    steps = [
        "clean_data.py",
        "feature_engineering.py",
        "create_target.py",
        "analyze_features.py",
        "scoring.py",
    ]

    

    for step in steps:
        run_step(step)

    
    

if __name__ == "__main__":
    main()