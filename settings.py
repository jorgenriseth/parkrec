from pathlib import Path

from pydantic import BaseModel, BaseSettings


class Settings(BaseSettings):
    rawdata = Path(__file__).parent / "GRIP"
    datapath = Path(__file__).parent / "data"


class PatientDataSettings(BaseModel):
    dicompath: Path
    patient_root: Path
    t1raw: Path
    resampled: Path
    registered: Path
    lta: Path
    looklocker: Path
    t2: Path
    dti: Path
    concentrations: Path
    fenics: Path


def patient_data_default_settings():
    return dict(
        t1raw="T1",
        resampled="RESAMPLED",
        registered="REGISTERED",
        normalized="NORMALIZED",
        lta="LTA",
        looklocker="LOOKLOCKER",
        t2="T2",
        dti="DTI",
        concentrations="CONCENTRATIONS",
        fenics="FENICS",
    )


def patient_data_settings(patientid: str) -> PatientDataSettings:
    default = patient_data_default_settings()
    patient_path = Settings().datapath / patientid
    return PatientDataSettings(
        dicompath=Settings().rawdata / patientid,
        patient_root=patient_path,
        **{data: patient_path / datadir for data, datadir in default.items()}
    )


class DICOMSettings(BaseModel):
    paths: PatientDataSettings
    patterns: dict[str, str] = {
        "T1": r"(DICOM_\d+_\d+[_ ])(.*(PDT1_3D).*)",
        "T2": r"(DICOM_\d+_\d+[_ ])(.*(TE565).*)",
        "LookLocker": r"(DICOM_\d+_3[_ ])(.*(LookLocker|2beatpause).*)",
    }
