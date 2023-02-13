import subprocess

from pathlib import Path
from typing import List, Iterator


def is_reconned(patient_dir: Path) -> None:
    if not patient_dir.is_dir():
        raise OSError(f"{patient_dir} not found. Should run recon-all on subject first.")


def as_str(path_iter: Iterator[Path]) -> str:
    return " ".join(map(str, path_iter))


def patient_create_template(subject_dir: Path) -> Path:
    is_reconned(subject_dir)
    volumes = sorted((subject_dir / "RESAMPLED").iterdir())

    template = subject_dir / "REGISTERED" / "template.mgz"
    template.parent.mkdir(exist_ok=True)

    template_command = f"mri_robust_template --mov {as_str(volumes)} --average 1 --template {template} --satit --inittp 1 --fixtp --subsample 200"
    subprocess.run(template_command, shell=True)
    return template


def patient_register(subject_dir: Path) -> Path:
    is_reconned(subject_dir)

    volumes = sorted((subject_dir / "RESAMPLED").iterdir())
    output_dir=  subject_dir / "REGISTERED"
    lta_dir = subject_dir / "LTA"
    lta_dir.mkdir(exist_ok=True)

    for volume in volumes:
        volume_register(volume, output_dir / "template.mgz", output_dir / volume.name, lta_dir / volume.with_suffix(".lta").name)

    return output_dir


def volume_register(input_volume: Path, template: Path, output_volume: Path, output_lta: Path) -> None:
    register_command = f"mri_robust_register --mov {input_volume} --dst {template} --lta {output_lta} --mapmov {output_volume} --satit --subsample 200"
    subprocess.run(register_command, shell=True)


if __name__ == "__main__":
    patpath = Path("FREESURFER/PAT_001")
    # patient_create_template(patpath)
    patient_register(patpath)

    