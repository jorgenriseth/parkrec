from pathlib import Path
from uuid import uuid4
import re
import subprocess
import pydicom
import logging
from typing import Optional, Dict
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)


def is_datedir(dirpath: Path) -> bool:
    match = re.search("[0-9]{4}_[0-9]{2}_[0-9]{2}", dirpath.stem)
    if match is None:
        return False
    return True


def patient_convert(inputdir, outputdir, patient: str, sequences) -> None:
    patientdir = inputdir / patient
    for datedir in filter(is_datedir, patientdir.iterdir()):
        for studydir in datedir.iterdir():
            date = datetime.strptime(datedir.stem, "%Y_%m_%d").strftime("%Y%m%d")
            timestamp = None  # Is set after reading first file of interest.
            tempdir = Path(f"/tmp/parkrec_convert-{studydir.stem}-{uuid4()}")
            tempdir.mkdir(parents=True)
            for path in studydir.iterdir():
                seq_label = search_for_relevant_sequence(path, sequences)
                if seq_label is not None:
                    imfile = path / "DICOM/IM_0002"  # FIXME: Potential bugsource.
                    if timestamp is None:
                        timestamp = find_timestamp(imfile)
                        study_target = (
                            outputdir / patientdir.stem / "VOLUMES" / f"{date}_{timestamp}"
                        )
                        study_target.mkdir(parents=True, exist_ok=True)
                        #(study_target / "LookLocker").mkdir(exist_ok=True)
                    conversion_command = f'\
                        dcm2niix -f {seq_label} -o "{tempdir}" "{path}/DICOM"\
                        1>> {tempdir}/log.txt'.strip("\t"),
                    logger.info(f"{conversion_command}")
                    subprocess.run(
                        conversion_command,
                        shell=True,
                    )

            for nii_file in filter(is_niifile, tempdir.iterdir()):
                if "LookLocker" in nii_file.name:
                    looklocker_target = (outputdir / patientdir.stem / "VOLUMES/LookLocker") / f"{date}_{timestamp}"
                    looklocker_target.mkdir(exist_ok=True, parents=True)
                    nii_file.rename(looklocker_target / nii_file.name)
                else: 
                    nii_file.rename(f"{study_target}/{nii_file.name}")
                # TODO: Probably don't need this.
                # subprocess.run(
                #     f'mri_convert \
                #         "{nii_file}" \
                #         "{study_target}/{nii_file.stem}.mgz"',
                #     shell=True,
                # )

def is_niifile(p: Path) -> bool:
    return p.suffix == ".nii"

def search_for_relevant_sequence(
    path: Path, sequences: Dict[str, str]
) -> Optional[str]:
    if path.is_dir():
        search_pattern = "DICOM_[0-9]+_[13][_ ]"
        split = re.split(search_pattern, path.stem)
        if len(split) > 1:
            if split[-1] in sequences:
                return sequences[split[-1]]
    return None


def find_timestamp(dicom_file: Path) -> Optional[str]:
    with pydicom.dcmread(dicom_file) as f:
        timestamp = f.StudyTime
    return timestamp


if __name__ == "__main__":
    inputdir = Path("GRIP")
    outputdir = Path("GRIP_SORTED")
    patient = "PAT_001"
    sequences = {
        "WIP PDT1_3D 08mm": "T1",
        "WIP PDT1_3D 1mm": "T1",
        "WIP 07mmTE565 3D TSE": "T2",
        "WIP T2W 3D TSE TE565": "T2",
        "WIP DelRec - LookLocker 1mm 3000 HR 21": "LookLocker",
        "WIP DelRec - WIP 2beatpause1mm 3000 HR 21": "LookLocker"
    }

    patient_convert(inputdir, outputdir, patient, sequences)

    # Cleanup
    for path in Path("/tmp").iterdir():
        if "parkrec_convert" in path.stem:
            shutil.rmtree(path)