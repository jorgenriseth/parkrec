#!/usr/bin/env/python
from functools import partial
from itertools import chain, repeat
from datetime import datetime
from multiprocessing.pool import Pool
import json

from pathlib import Path

import shutil
import pydicom

from typing import Tuple, Iterator, Dict


def main(input_dir: Path, output_dir: Path, sequences: Dict[str, str], add_metadata: bool = False) -> None:
    filemap = create_protocol_filemap(input_dir, output_dir, sequences)
    copy_files(filemap)
    if add_metadata:
        add_sorted_metadata(output_dir)


def copy_files(filemap: Dict[Path, Path]) -> None:
    for src, dest in filemap.items():
        dest.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(src, dest)


def create_protocol_filemap(
    input_dir: Path, output_dir: Path, sequences: Dict[str, str], n_jobs=None
) -> Dict[Path, Path]:
    """Runs through the folder structure with the MRI data we receive from the hospital, and creates a dictionary mapping a src-path sorts them according to
    patient - study_datetime - protocol. Runs in parallel for each of the studies."""
    pool = Pool(n_jobs)
    task = partial(
        create_study_filemap,
        output_dir=output_dir,
        sequences=sequences,
    )
    results = pool.map(task, study_iterator(input_dir))
    return dict(chain(*(x.items() for x in results)))


def study_iterator(input_dir: Path) -> Iterator[Path]:
    return (
        x
        for patient in input_dir.iterdir()
        for date in patient.iterdir()
        for x in date.iterdir()
    )


def create_study_filemap(
    study_dir: Path, output_dir: Path, sequences: Dict[str, str]
) -> Dict[Path, Path]:
    date_dir = study_dir.parent
    patient = date_dir.parent.stem
    study_data = study_dir / "DICOM" / "DICOM"
    date = datetime.strptime(date_dir.stem, "%Y_%m_%d").strftime("%Y%m%d")
    timestamp = find_timestamp(study_dir)
    study_target = output_dir / patient / f"{date}_{timestamp}"
    print(f"Entering {study_data}\n")  # TODO: Use python logging instead.
    return filemap_study(study_data, study_target, sequences)


def filemap_study(
    study_input: Path,
    study_output: Path,
    sequences: Dict[str, str],
) -> Dict[Path, Path]:
    """Given the path to a specific study, returns a dictionary mapping paths in the original structure
    to the designated new path. Note that the files are NOT copied by this function."""
    filemap = {}
    for imfile, offset in study_imfiles(study_input):
        with pydicom.dcmread(imfile) as f:
            file_protocol = f.ProtocolName
            if file_protocol in sequences:
                filemap[imfile] = (
                    study_output
                    / sequences[file_protocol]
                    / renumber_imfile(imfile, offset)
                )
    return filemap


def renumber_imfile(imfile: Path, offset: int) -> str:
    """Relabel a file from a subdirectory 000000000N/IM_XXXX -> IM_{2048 * N + XXXX}"""
    return f"IM_{int(imfile.stem.split('_')[1]) + offset * 2048:04d}"


def find_timestamp(x: Path) -> str:
    """TODO: Correct this function."""
    # TODO: Not correct timestamp.
    return x.stem.split("__")[1]


def study_imfiles(study_path: Path) -> Iterator[Path]:
    return chain(
        study_level_imfiles(study_path),
        *(
            subdirectory_imfiles(subdir)
            for subdir in filter(is_image_subdirectory, study_path.iterdir())
        ),
    )


def is_image_subdirectory(path: Path) -> bool:
    """Checks if path is a directory named as a directory,
    meant to find folders which might contain IM_XXXX-files."""
    return path.is_dir() and path.stem.isdigit()


def study_level_imfiles(study_data_path: Path) -> Iterator[Tuple[Path, int]]:
    """Returns a list of string-representations of the filenames at the top-level of
    of a specific study."""
    return zip(filter(is_imfile, study_data_path.iterdir()), repeat(0))


def subdirectory_imfiles(study_subdir_path: Path) -> Iterator[Tuple[Path, int]]:
    return zip(
        filter(is_imfile, study_subdir_path.iterdir()),
        repeat(int(study_subdir_path.stem)),
    )


def is_imfile(path: Path) -> bool:
    """Checks if path is a dicom IM-file."""
    return path.is_file() and path.stem[:3] == "IM_"


def sorted_study_iterator(sorted_dir: Path) -> Iterator[Path]:
    return (study for patient in sorted_dir.iterdir() for study in patient.iterdir())


def sorted_study_metadata(study_path):
    study_metadata = {}
    for path in filter(lambda x: x.is_dir(), study_path.iterdir()):
        print(path)
        protocol_filelist = list(
            map(lambda x: int(x.stem.split("_")[1]), filter(is_imfile, path.iterdir()))
        )
        study_metadata[path.stem] = {
            "min": min(protocol_filelist),
            "max": max(protocol_filelist),
            "num_files": len(protocol_filelist),
        }
    return study_metadata


def store_study_metadata(study_path: Path) -> None:
    filepath = study_path / "info.json"
    with open(filepath, "w") as f:
        json.dump(sorted_study_metadata(study_path), f, indent=4)


def add_sorted_metadata(output_dir: Path) -> None:
    for study in sorted_study_iterator(output_dir):
        store_study_metadata(study)


if __name__ == "__main__":
    inputdir = Path("GRIP")
    outputdir = Path("GRIP_SORTED")
    sequences = {
        "WIP PDT1_3D 08mm": "T1",
        "WIP DelRec - WIP 2beatpause1mm 3000 HR 21": "Look-Locker",
        "WIP 07mmTE565 3D TSE": "T2",
    }
    main(inputdir, outputdir, sequences, add_metadata=False)
