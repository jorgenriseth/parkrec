import subprocess

from pathlib import Path
from sort_mri import is_imfile


def is_datetime_dir(path: Path) -> bool:
    return path.stem.split("_")[0].isdigit() and path.stem.split("_")[1].isdigit()


def patient_reconstruct(patient_dir: Path, protocol: str = "T1"):
    subject_dir = patient_dir.parent.parent / "FREESURFER" / patient_dir.stem
    if not subject_dir.is_dir():
        raise OSError(
            f"{subject_dir} not found. Should run recon-all on subject first."
        )

    output_dir = subject_dir / "RESAMPLED"
    output_dir.mkdir(exist_ok=True, parents=False)
    for datedir in filter(is_datetime_dir, patient_dir.iterdir()):
        some_image = next(filter(is_imfile, (datedir / protocol).iterdir()))
        subprocess.run(
            f"mri_convert --conform -odt float {some_image} {output_dir/datedir.stem}.mgz",
            shell=True,
        )


if __name__ == "__main__":
    patient_reconstruct(Path("GRIP_SORTED/PAT_001"))
