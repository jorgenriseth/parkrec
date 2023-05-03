import json
import logging
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

import pydicom

from settings import DICOMSettings, Settings, patient_data_settings

logger = logging.getLogger(__name__)


def patient_dicom2nii(
    patientdir: Path,
    t1dir: Path,
    t2dir: Path,
    looklockerdir: Path,
    patterns: dict[str, str],
    dtidir: Optional[Path] = None,
):
    for idx, studydir in enumerate(study_iterator(patientdir)):
        dicom2nii(studydir, t1dir, "T1", patterns["T1"])
        dicom2nii(studydir, looklockerdir, "LookLocker", patterns["LookLocker"])
        if idx == 0:
            dicom2nii(studydir, t2dir, "T2", patterns["T2"])
        if dtidir is not None:
            raise NotImplementedError("Need to find correct DTI sequence.")


def dicom2nii(studydir, outputdir, label, pattern):
    outputdir.mkdir(exist_ok=True, parents=True)
    tempdir = Path(f"/tmp/parkrec_convert-{studydir.stem}-{uuid4()}")
    tempdir.mkdir()

    path = find_sequencedir(studydir, pattern)
    conversion_command = f'\
        dcm2niix -f {label} -o "{tempdir}" "{path}/DICOM"\
        1>> {tempdir}/log.txt \
    '.strip(
        "\t"
    )
    logger.info(f"Running conversion command: {conversion_command}")
    subprocess.run(conversion_command, shell=True)

    for nii_file in filter(is_niifile, tempdir.iterdir()):
        datedir = studydir.parent
        with open(nii_file.with_suffix(".json")) as f:
            info = json.load(f)
        timestamp = datetime.strptime(info["AcquisitionTime"], "%H:%M:%S.%f").strftime(
            "%H%M%S"
        )
        outputname = f"{datedir.stem.replace('_', '')}_{timestamp}"

        if "LookLocker" in nii_file.stem:
            outputname += f"_t{info['TriggerDelayTime']}"
        nii_file.rename(outputdir / f"{outputname}.nii")


def find_sequencedir(studydir: Path, pattern: str) -> Path:
    paths = [x for x in sorted(studydir.glob("DICOM_*")) if re.match(pattern, x.name)]
    if len(paths) == 0:
        raise ValueError(
            f"No DICOM directory found in {studydir} matching '{pattern}'."
        )
    if len(paths) > 1:
        logger.warning(
            f"Multiple DICOM directories found in {studydir} matching '{pattern}': \
            {paths}".strip(
                "\t"
            )
        )
    return paths[-1]


def is_datedir(dirpath: Path) -> bool:
    match = re.search("[0-9]{4}_[0-9]{2}_[0-9]{2}", dirpath.stem)
    if match is None:
        return False
    return True


def is_niifile(p: Path) -> bool:
    return p.suffix == ".nii"


def find_timestamp_from_dicom(dicom_file: Path) -> Optional[str]:
    with pydicom.dcmread(dicom_file) as f:
        timestamp = f.StudyTime
    return timestamp


def study_iterator(patient_dir: Path) -> list[Path]:
    return [
        x
        for date in sorted(filter(is_datedir, patient_dir.iterdir()))
        for x in sorted(date.iterdir())
    ]


if __name__ == "__main__":
    from argparse import ArgumentParser

    patient_parser = ArgumentParser()
    patient_parser.add_argument(
        "patientid", type=str, help="Patient ID on format PAT_XXX"
    )
    patient_args, remaining_args = patient_parser.parse_known_args()

    paths = patient_data_settings(patientid=patient_args.patientid)
    settings = DICOMSettings(paths=paths)

    parser = ArgumentParser()
    parser.add_argument("--dicomdir", type=str, default=paths.dicompath)
    parser.add_argument("--t1_outputdir", type=str, default=paths.t1raw)
    parser.add_argument("--t2_outputdir", type=str, default=paths.t2)
    parser.add_argument("--ll_outputdir", type=str, default=paths.looklocker)
    args = parser.parse_args(remaining_args)

    patient_dicom2nii(
        patientdir=args.dicomdir,
        t1dir=args.t1_outputdir,
        t2dir=args.t2_outputdir,
        looklockerdir=args.ll_outputdir,
        patterns=settings.patterns,
    )

    for path in Path("/tmp").iterdir():
        if "parkrec_convert" in path.stem:
            shutil.rmtree(path)
