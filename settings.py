import dataclasses
from pathlib import Path
from pydantic import BaseSettings, BaseModel
from string import Template


class Settings(BaseSettings):
    rawdata = Path(__file__).parent / "GRIP"
    datapath = Path(__file__).parent / "data"


class PatientDataSettings(BaseModel):
    t1raw: Path
    resampled: Path
    registered: Path
    lta: Path
    looklocker: Path
    t2: Path
    dti: Path
    concentrations: Path
    fenics: Path


def patient_data_settings(datapath: Path, patientid: str) -> PatientDataSettings:
    patient_path = Path(datapath) / patientid
    return PatientDataSettings(
        t1raw=patient_path / "T1",
        resampled=patient_path / "RESAMPLED",
        registered=patient_path / "NORMALIZED",
        lta=patient_path / "LTA",
        looklocker=patient_path / "LOOKLOCKER",
        t2=patient_path / "T2",
        dti=patient_path / "DTI",
        concentrations=patient_path / "CONCENTRATIONS",
        fenics=patient_path / "FENICS",
    )


class DICOMSettings(BaseModel):
    patient_dicompath: Path
    paths: PatientDataSettings
    sequences: dict[str, str] = {
        "T1": ["WIP PDT1_3D 08mm", "WIP PDT1_3D 1mm"],
        "T2": ["WIP 07mmTE565 3D TSE", "WIP T2W 3D TSE TE565"],
        "LookLocker": [
            "WIP DelRec - LookLocker 1mm 3000 HR 21",
            "WIP DelRec - WIP 2beatpause1mm 3000 HR 21",
        ],
        "DTI": None
    }
