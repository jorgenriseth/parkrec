#!/usr/bin/env/python
from functools import partial
from itertools import chain, repeat
from datetime import datetime
from multiprocessing.pool import Pool

from pathlib import Path

import shutil
import pydicom

from typing import Tuple, Iterator, Dict, Optional


def main(inputdir, outputdir, sequences):
    for protocol, protocol_out in sequences.items():
        filemap = create_protocol_filemap(inputdir, outputdir, protocol, protocol_out)
        copy_files(filemap)

def copy_files(filemap: Dict[Path, Path]) -> None:
    for src, dest in filemap.items():
        dest.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(src, dest)

def create_protocol_filemap(inputdir: Path, outputdir: Path, protocol: str, protocol_out: str, n_jobs=None) -> Dict[Path, Path]:
    """Runs through the folder structure with the MRI data we receive from the hosptial, and creates a dictionary mapping a src-path sorts them according to
    patient - study_datetime - protocol. Runs in parallel for each of the """
    pool = Pool(n_jobs)
    task = partial(create_study_filemap, output_dir=outputdir, protocol=protocol, protocol_out=protocol_out)
    results = pool.map(task, study_iterator(inputdir))
    return dict(chain(*(x.items() for x in results)))


def study_iterator(inputdir: Path) -> Iterator[Path]:
    return (x for patient in inputdir.iterdir() for date in patient.iterdir() for x in date.iterdir())

def create_study_filemap(study_dir, output_dir, protocol, protocol_out):
    date_dir = study_dir.parent
    patient = date_dir.parent.stem
    study_data = study_dir / "DICOM" / "DICOM"
    date = datetime.strptime(date_dir.stem, "%Y_%m_%d").strftime("%Y%m%d")
    timestamp = find_timestamp(study_dir)
    study_target = output_dir / patient / f"{date}_{timestamp}"
    print(f"Entering {study_data}\n")
    return filemap_study(study_data, study_target, protocol, protocol_out)

def filemap_study(study_input: Path, study_output: Path, protocol: str, protocol_out: Optional[str] = None) -> Dict[Path, Path]:
    """Given the path to a specific study, returns a dictionary mapping paths in the original structure
    to the designated new path. Note that the files are NOT copied by this function."""
    filemap = {}
    for imfile, offset in study_imfiles(study_input):
        if is_protocol(imfile, protocol):
            filemap[imfile] = study_output / protocol_out / renumber_imfile(imfile, offset)
    return filemap


def renumber_imfile(imfile: Path, offset: int) -> Path:
    """Relabel a file from a subdirectory 000000000N/IM_XXXX -> IM_{2048 * N + XXXX}"""
    return f"IM_{int(imfile.stem.split('_')[1]) + offset * 2048:04d}"


def is_protocol(file: Path, protocol: str) -> bool:
    with pydicom.dcmread(file) as f:
        return protocol == f.ProtocolName

    
def find_timestamp(x: Path) -> str:
    """TODO: Correct this function."""
    return x.stem.split('__')[1]

def study_imfiles(study_path: Path):
    return chain(
        study_level_imfiles(study_path),
        *(subdirectory_imfiles(subdir) for subdir in filter(is_image_subdirectory, study_path.iterdir()))        
    )


def is_image_subdirectory(path: Path) -> bool:
    """Checks if path is a directory named as a directory,
    meant to find folders which might contain IM_XXXX-files."""
    return path.is_dir() and path.stem.isdigit()


def study_level_imfiles(study_data_path) -> Iterator[Tuple[Path, int]]:
    """Returns a list of string-representations of the filenames at the top-level of
    of a specific study."""
    return zip(filter(is_imfile, study_data_path.iterdir()), repeat(0))

def subdirectory_imfiles(subdir: Path) -> Iterator[Tuple[Path, int]]:
    return zip(filter(is_imfile, subdir.iterdir()), repeat(int(subdir.stem)))


def is_imfile(path: Path) -> bool:
    """Checks if path is a dicom IM-file."""
    return path.is_file() and path.stem[:3] == "IM_"


if __name__ == "__main__":
    inputdir = Path("GRIP")
    outputdir = Path("GRIP_SORTED")
    sequences = {
        "WIP PDT1_3D 08mm": "T1",
        "WIP DelRec - WIP 2beatpause1mm 3000 HR 21": "Look-Locker",
        "WIP 07mmTE565 3D TSE": "T2"
    }
    main(inputdir, outputdir, sequences)