from pathlib import Path

def is_not_template(p: Path) -> bool:
    return p.suffix == ".mgz" and p.stem != "template"

def is_datetime_dir(path: Path) -> bool:
    return path.stem.split("_")[0].isdigit() and path.stem.split("_")[1].isdigit()