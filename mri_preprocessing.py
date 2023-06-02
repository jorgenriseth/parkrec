from argparse import ArgumentParser
import subprocess
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

parser = ArgumentParser()
parser.add_argument("patientid", type=str, help="Patient ID on format PAT_XXX")
args = parser.parse_args()


logging.info(f"Preprocessing MR-data for patient {args.patientid}")
logging.info(f"Converting DICOM data to .nii")
subprocess.run(f"python multiframe_dicom.py {args.patientid}", shell=True).check_returncode()

logging.info(f"Resampling and converting .nii-files to .mgz")
subprocess.run(f"python mri_convert.py {args.patientid}", shell=True).check_returncode()

logging.info(f"Registering within-patient MR-images to ")
subprocess.run(f"python mri_register.py {args.patientid}", shell=True).check_returncode()
