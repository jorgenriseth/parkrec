import logging
from pathlib import Path

import nibabel
import numpy as np

from parkrec import filters



logger = logging.getLogger(__name__)


def normalize_image(
    image_path: Path, ref_mask: np.ndarray, ref_transform: np.ndarray, output_dir: Path
) -> Path:
    image = nibabel.load(image_path)
    image_affine = image.affine
    assert np.allclose(
        ref_transform, image_affine
    ), "Poor match between reference and image-transform."
    image_data = image.get_fdata()

    normalized_image_data = image_data / np.median(image_data[ref_mask])
    normalized_image = nibabel.Nifti1Image(normalized_image_data, ref_transform)

    newfile = output_dir / image_path.name
    nibabel.save(normalized_image, newfile)
    return newfile


def normalize_subject_images(subject_dir: Path) -> Path:
    registered_dir = subject_dir / "REGISTERED"
    output_dir = subject_dir / "NORMALIZED"
    refroi_path = subject_dir / "refroi.nii"
    if not refroi_path.exists():
        raise OSError(
            f"""{refroi_path} does not exists.
            Remember to create reference ROI using freeview."""
        )
    output_dir.mkdir(exist_ok=True)

    refroi = nibabel.load(refroi_path)
    refroi_affine = refroi.affine
    refroi_mask = refroi.get_fdata().astype(bool)

    images = sorted(filter(filters.is_T1_mgz, registered_dir.iterdir()))
    for imagepath in images:
        logger.info("Normalizing image {imagepath}")
        normalize_image(imagepath, refroi_mask, refroi_affine, output_dir)

    return output_dir


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("patientid", help="Patient ID on the form PAT_###")
    args = parser.parse_args()

    subject_dir = Path("data/") / args.patientid
    normalize_subject_images(subject_dir)
