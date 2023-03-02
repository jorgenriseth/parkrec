import subprocess
import logging

from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def is_datetime_dir(path: Path) -> bool:
    return path.stem.split("_")[0].isdigit() and path.stem.split("_")[1].isdigit()


def is_nii(p: Path) -> bool:
    return p.suffix == ".nii"


def patient_reconstruct(patient_dir: Path, protocol: str = "T1"):
    volume_dir = patient_dir / "VOLUMES"
    output_dir = patient_dir / "RESAMPLED"
    output_dir.mkdir(exist_ok=True, parents=False)
    for datedir in filter(is_datetime_dir, volume_dir.iterdir()):
        volume = datedir / "T1.nii"
        subprocess.run(
            f"mri_convert --conform -odt float {volume} {output_dir/f'{datedir.stem}'}.mgz",
            shell=True,
        )
        # for volume in filter(is_nii, datedir.iterdir()):
        #     subprocess.run(
        #         f"mri_convert --conform -odt float {volume} {output_dir/f'{volume.stem}_{datedir.stem}'}.mgz",
        #         shell=True,
        #     )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("patientid", help="Patient ID on the form PAT_XXX")
    args = parser.parse_args()

    inputdir = Path("DATA/") / args.patientid
    patient_reconstruct(inputdir)
