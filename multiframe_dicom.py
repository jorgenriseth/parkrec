from pathlib import Path
from uuid import uuid4
import re
import subprocess
import pydicom
import logging
from typing import Optional, Dict
from datetime import datetime, time
import json

from settings import Settings, patient_data_settings, DICOMSettings

logger = logging.getLogger(__name__)


def is_datedir(dirpath: Path) -> bool:
    match = re.search("[0-9]{4}_[0-9]{2}_[0-9]{2}", dirpath.stem)
    if match is None:
        return False
    return True


def patient_dicom2nii(
    patientdir: Path,
    t1dir: Path,
    t2dir: Path,
    looklockerdir: Path,
    sequences: dict[str, str],
    dtidir: Optional[Path] = None,
):
    for idx, studydir in enumerate(study_iterator(patientdir)):
        dicom2nii(studydir, t1dir, "T1", sequences["T1"])
        dicom2nii(studydir, looklockerdir, "LookLocker", sequences["LookLocker"])
        if idx == 0:
            dicom2nii(studydir, t2dir, "T2", sequences["T2"])
        if dtidir is not None:
            raise NotImplementedError("Need to find correct DTI sequence.")


def dicom2nii(studydir, outputdir, label, patterns):
    outputdir.mkdir(exist_ok=True, parents=True)
    tempdir = Path(f"/tmp/parkrec_convert-{studydir.stem}-{uuid4()}")
    tempdir.mkdir()

    path = find_dicomdir(studydir, patterns)
    conversion_command = f'\
        dcm2niix -f {label} -o "{tempdir}" "{path}/DICOM"\
        1>> {tempdir}/log.txt'.strip(
        "\t"
    )
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


def find_dicomdir(studydir: Path, patterns: list[str]) -> Path:
    paths = sorted(filter(lambda x: has_pattern(x, patterns), studydir.glob("DICOM_*")))
    if len(paths) == 0:
        raise ValueError(f"No DICOM directory found in {studydir} matching {patterns}.")
    if len(paths) > 1:
        # TODO: Verify behaviour.
        print(paths)
        return paths[-1]
        raise ValueError(
            f"Multiple DICOM directories found in {studydir} matching {patterns}: \
            {paths}"
        )
    return paths[0]


def has_pattern(dirname, patterns):
    for pattern in patterns:
        if pattern in dirname.stem:
            return True
    return False


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

    parser = ArgumentParser()
    parser.add_argument("patientid", type=str, help="Patient ID on format PAT_XXX")
    patient = parser.parse_args().patientid

    settings = DICOMSettings(
        patient_dicompath=Settings().rawdata / patient,
        paths=patient_data_settings(Settings().datapath, patient),
    )

    patient_dicom2nii(
        settings.patient_dicompath,
        settings.paths.t1raw,
        settings.paths.t2,
        settings.paths.looklocker,
        settings.sequences,
    )

    # dicom2nii(settings.raw, settings.paths.t2, "T2", settings.sequences["T2"])

    # inputdir = Path("GRIP")
    # outputdir = Path("GRIP_SORTED")
    # patient = "PAT_001"
    # sequences = {
    #     "WIP PDT1_3D 08mm": "T1",
    #     "WIP PDT1_3D 1mm": "T1",
    #     "WIP 07mmTE565 3D TSE": "T2",
    #     "WIP T2W 3D TSE TE565": "T2",
    #     "WIP DelRec - LookLocker 1mm 3000 HR 21": "LookLocker",
    #     "WIP DelRec - WIP 2beatpause1mm 3000 HR 21": "LookLocker"
    # }

    # patient_convert(inputdir, outputdir, patient, sequences)

    # # Cleanup
    # for path in Path("/tmp").iterdir():
    #     if "parkrec_convert" in path.stem:
    #         shutil.rmtree(path)
