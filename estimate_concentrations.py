import subprocess

from parkrec.settings import patient_data_settings


def main(patientid: str, resolution: int = 32):
    # Create brainmask and t1map
    subprocess.run(
        f"python3 parkrec/mriprocessing/t1maps.py {patientid} ", shell=True
    ).check_returncode()

    # Create concentration-images.
    create_concentration(patientid)

    # Create mesh
    subprocess.run(
        (
            "python3 parkrec/mriprocessing/mesh_generation.py"
            + f" {patientid}"
            + f" {resolution}"
        ),
        shell=True,
    ).check_returncode()

    # Map concentrations to mri.
    subprocess.run(
        (
            "python3 parkrec/mriprocessing/mri2fenics.py"
            + f" {patientid}"
            + f" DATA/{patientid}/MESH/brain{resolution}.hdf"
        ),
        shell=True,
    ).check_returncode()


def create_concentration(patientid: str):
    paths = patient_data_settings(patientid=patientid)
    estimate_c_cmd = (
        "python3 parkrec/mriprocessing/estimatec.py"
        + f" --inputfolder {paths.registered}"
        + f" --exportfolder {paths.concentrations}"
        + f" --t1map {paths.patient_root / 't1map.mgz'}"
        + f" --mask {paths.patient_root / 'brainmask.mgz'}"
    )
    subprocess.run(estimate_c_cmd, shell=True).check_returncode()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("patientid", type=str, help="Patient ID on format PAT_XXX")
    args = parser.parse_args()

    main(args.patientid)
