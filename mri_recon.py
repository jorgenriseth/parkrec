"""
1. Move start-time T1-volume into DATA/PAT_XXX/mri/orig
2. Execute recon-all -all -sd DATA -s PAT_XXX
3. Check for T2 or Flair-input, and improve pial-surface.
"""
import argparse
import logging
import subprocess
from pathlib import Path
from typing import Optional

from parkrec.settings import patient_data_settings
from parkrec.filters import is_T1_mgz

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def run_recon_all(
    subject: str, subjects_dir: Path, t1: Path, t2: Optional[Path], parallel: bool
) -> None:
    recon_all_cmd = (
        "recon-all"
        + f" -sd {subjects_dir}"
        + f" -s {subject}"
        + f" -i {t1}"
        + (t2 is not None) * f" -T2 {t2} -T2pial"
        + parallel * " -parallel"
        + " -all"
    )
    logger.info(f"Running cmd: '{recon_all_cmd}'")
    subprocess.run(recon_all_cmd, shell=True).check_returncode()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("patientid", help="Patient ID on the form PAT_XXX")
    parser.add_argument("-T2", action="store_true")
    parser.add_argument("-parallel", action="store_true")
    args = parser.parse_args()
    paths = patient_data_settings(patientid=args.patientid)

    t1 = sorted(filter(is_T1_mgz, paths.resampled.iterdir()))[0]
    t2 = paths.resampled / "T2.mgz" if args.T2 else None
    run_recon_all(
        subject=args.patientid,
        subjects_dir=paths.datapath,
        t1=t1,
        t2=t2,
        parallel=args.parallel,
    )
