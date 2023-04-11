import argparse
import subprocess
import logging
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("patientid", help="Patient ID on the form PAT_###")
args = parser.parse_args()

logger = logging.getLogger(__name__)

def is_datetime_dir(path: Path) -> bool:
    return path.stem.split("_")[0].isdigit() and path.stem.split("_")[1].isdigit()

def find_t2(pat_dir):
    init_study = sorted(filter(is_datetime_dir, (pat_dir / "VOLUMES").iterdir()))[0]
    t2_volume = init_study / "T2.nii"
    assert t2_volume.exists(), f"Path {t2_volume} does not exist."
    return t2_volume

patientdir = Path("DATA/") / args.patientid

# Resample/Conform T2 images 
t2_volume = find_t2(patientdir)
t2_conformed = patientdir / "mri/orig/T2raw.mgz"
if not t2_conformed.exists():
    subprocess.run(f"mri_convert --conform {t2_volume} {t2_conformed}", shell=True)

# Perform surface-improvement.
t2_recon_cmd = f"recon-all -sd DATA -s {patientdir.stem} -T2pial -autorecon3"
logger.info(f"Running cmd: '{t2_recon_cmd}'")
subprocess.run(t2_recon_cmd, shell=True)
