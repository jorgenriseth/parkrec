import subprocess
import re
import logging

from pathlib import Path
from typing import List, Iterator

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def as_str(path_iter: Iterator[Path]) -> str:
    return " ".join(map(str, path_iter))


def is_T1_mgz(p: Path) -> bool:
    return (re.search("[0-9]{8}_[0-9]{6}.mgz", p.name) is not None)


def patient_create_template(subject_dir: Path) -> Path:
    volumes = sorted(filter(is_T1_mgz, (subject_dir / "RESAMPLED").iterdir()))
    template = subject_dir / "REGISTERED" / "template.mgz"
    template.parent.mkdir(exist_ok=True)
    if template.exists():
        return template

    template_command = f"mri_robust_template \
            --mov {as_str(volumes)}\
            --average 1 \
            --template {template}\
            --satit \
            --inittp 1  \
            --fixtp  \
            --subsample 200  \
        "
    subprocess.run(template_command, shell=True)
    return template


def patient_register(subject_dir: Path) -> Path:
    volumes = sorted(filter(is_T1_mgz, (subject_dir / "RESAMPLED").iterdir()))
    output_dir=  subject_dir / "REGISTERED"
    lta_dir = subject_dir / "LTA"
    lta_dir.mkdir(exist_ok=True)

    for volume in volumes:
        register_command = f"mri_robust_register \
                --mov {volume} \
                --dst {output_dir / 'template.mgz'} \
                --lta {lta_dir / volume.with_suffix('.lta').name} \
                --mapmov {output_dir / volume.name} \
                --iscale \
                --satit  \
                --iscale  \
                --maxit 10 \
                --subsample 200  \
            "
        logger.info(register_command)
        subprocess.run(register_command, shell=True)
    return output_dir



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("patientid", help="Patient ID on the form PAT_XXX")
    args = parser.parse_args()

    patpath = Path(f"DATA/{args.patientid}")

    patient_create_template(patpath)
    patient_register(patpath)
