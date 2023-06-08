import subprocess
import logging

from pathlib import Path

from multiframe_dicom import is_niifile

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def patient_reconstruct(
    t1_raw_dir: Path,
    t2_raw_dir: Path,
    outputdir: Path,
):
    outputdir.mkdir(exist_ok=True, parents=False)

    for file in filter(is_niifile, t1_raw_dir.iterdir()):
        subprocess.run(
            f"mri_convert --conform -odt float {file} {outputdir/f'{file.stem}'}.mgz",
            shell=True,
        )

    try:
        t2 = next(filter(is_niifile, t2_raw_dir.iterdir()))
        subprocess.run(
            f"mri_convert --conform -odt float {t2} {outputdir / 'T2.mgz'}",
            shell=True,
        )
    except StopIteration:
        raise RuntimeError(f"No nii-file found in {t2_raw_dir}")


if __name__ == "__main__":
    import argparse
    from parkrec.settings import patient_data_settings

    parser = argparse.ArgumentParser()
    parser.add_argument("patientid", help="Patient ID on the form PAT_XXX")
    args = parser.parse_args()
    paths = patient_data_settings(patientid=args.patientid)

    patient_reconstruct(
        paths.t1raw,
        paths.t2,
        paths.resampled,
    )
