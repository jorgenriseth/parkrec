import argparse
import logging
import shutil
from pathlib import Path

from multiframe_dicom import patient_convert

parser = argparse.ArgumentParser()
parser.add_argument("patientid", help="Patient ID on the form PAT_XXX")
args = parser.parse_args()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# TODO: Move to  settings-class
inputdir = Path("GRIP")
outputdir = Path("DATA")
sequences = {
    "WIP PDT1_3D 08mm": "T1",
    "WIP PDT1_3D 1mm": "T1",
    "WIP 07mmTE565 3D TSE": "T2",
    "WIP T2W 3D TSE TE565": "T2",
}

logger.info(f"Converting {args.patientid} DICOM-files to nii")
patient_convert(inputdir, outputdir, args.patientid, sequences)

# Cleanup
logger.info(f"Cleaning up temporary files.")
for path in Path("/tmp").iterdir():
    if "parkrec_convert" in path.stem:
        shutil.rmtree(path)
