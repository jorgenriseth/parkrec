from pathlib import Path

import nibabel
import numpy as np

CSF_LABELS = [
    4,
    5,
    14,
    15,
    24,
    43,
    44,
]


def parenchyma_mask(subject_dir: Path) -> Path:
    output_dir = subject_dir / "mri"
    output_file = output_dir / "parenchyma_mask.mgz"

    aseg_file = subject_dir / "mri" / "aseg.mgz"
    aseg = nibabel.load(aseg_file)
    aseg_data = aseg.get_fdata().astype(int)

    csf_mask = np.zeros(aseg_data.shape, dtype=bool)
    for csf_label in CSF_LABELS:
        csf_mask[(aseg_data == csf_label)] = True
    brain_mask = (aseg_data > 0) * (~csf_mask)

    image = nibabel.Nifti1Image(brain_mask.astype(float), aseg.affine)
    nibabel.save(image, output_file)

    return output_file


if __name__ == "__main__":
    parenchyma_mask(Path("FREESURFER/PAT_001/"))
