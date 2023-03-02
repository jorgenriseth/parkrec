"""
1. Move start-time T1-volume into DATA/PAT_XXX/mri/orig
2. Execute recon-all -all -sd DATA -s PAT_XXX
3. Check for T2 or Flair-input, and improve pial-surface.
""" 
import argparse
import re
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

def is_T1_mgz(p: Path) -> bool:
    return (re.search("[0-9]{8}_[0-9]{6}.mgz", p.name) is not None)

parser = argparse.ArgumentParser()
parser.add_argument("patientid", help="Patient ID on the form PAT_XXX")
parser.add_argument('-T2', action='store_true')
args = parser.parse_args()

patientdir = Path("DATA/") / args.patientid
reference_volume = sorted(filter(is_T1_mgz, (patientdir / "REGISTERED").iterdir()))[0]
target = patientdir / "mri/orig/001.mgz"
target.parent.mkdir(exist_ok=True, parents=True)
logger.info(f"Copying file {reference_volume} to {target}." )
shutil.copy(reference_volume, target)

recon_all_cmd = f"recon-all -sd DATA -s {patientdir.stem} -all"
logger.info(f"Running cmd: '{recon_all_cmd}'")
subprocess.run(recon_all_cmd, shell=True)

if args.T2:
    T2volume = patientdir / "RESAMPLED" / "T2.mgz"
    shutil.copy(T2volume, target.parent / "T2raw.mgz")
    t2_recon_cmd = f"recon-all -sd DATA -s {patientdir.stem} -T2pial -autorecon3"
    logger.info(f"Running cmd: '{t2_recon_cmd}'")
    subprocess.run(t2_recon_cmd, shell=True)
