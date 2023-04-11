import pandas as pd
import logging
import numpy as np
import nibabel
import re
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_mri_dataframe(
    filepath: Path,
    dtype: type,
    valname: str,
):
    mri_vol = nibabel.load(filepath)
    im = mri_vol.get_fdata().astype(dtype)
    IJK = np.array(list(np.ndindex(im.shape)))
    #    vox2ras = mri_vol.header.get_vox2ras()  # Kept until first commit, for reference
    #    XYZ = nibabel.affines.apply_affine(vox2ras, IJK)
    df = pd.DataFrame(
        {
            **{
                key: pd.Series(IJK[:, num], dtype=int)
                for num, key in enumerate(("i", "j", "k"))
            },
            valname: pd.Series(im.reshape(-1), dtype=dtype),
        }
    )
    return df


def is_patient_dir(path: Path):
    return path.is_dir() and (re.match("PAT_\d{3}", path.name) is not None)


def read_concentrations_file(filepath: Path, *args, **kwargs):
    concentrations_file = Path(filepath)
    columns = pd.read_csv(concentrations_file, index_col=0, nrows=0).columns.tolist()
    # TODO: Move this to a separate function
    dtypes = {
        key: (np.ushort if key in ("i", "j", "k", "aseg") else np.single)
        for key in columns
    }
    return pd.read_csv(concentrations_file, dtype=dtypes, *args, **kwargs)


def flatten_dataframe(dataframe: pd.DataFrame) -> pd.Series:
    mi = pd.MultiIndex.from_product([dataframe.columns, dataframe.index])
    return pd.Series(dataframe.to_numpy().flatten(order="F"), index=mi)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("patientid", type=str)
    parser.add_argument("concentration_dirname", type=str)
    args = parser.parse_args()

    patdir = Path("DATA") / args.patientid
    concdir = patdir / args.concentration_dirname
    assert patdir.exists(), f"Patient dir {patdir} does not exist"
    assert concdir.exists(), f"Concentration dir {concdir} does not exist"

    statsdir = patdir / "STATISTICS"
    statsdir.mkdir(exist_ok=True)

    aseg_volume = patdir / "mri" / "aseg.mgz"
    aseg_series = pd.Series(
        nibabel.load(aseg_volume).get_fdata().astype(int).reshape(-1)
    )
    df = create_mri_dataframe(aseg_volume, np.ushort, "aseg")
    for concfile in sorted(concdir.glob("*.mgz")):
        logger.info(f"Adding '{concfile}' to dataframe")
        timestamp = datetime.strptime(concfile.stem, "%Y%m%d_%H%M%S")
        im = nibabel.load(concfile).get_fdata().astype(np.single)

        df = df.assign(
            **{str(pd.to_datetime(timestamp)): pd.Series(im.reshape(-1), dtype=float)}
        )
    print(df.head())
    logger.info(f"Saving dataframe to {statsdir / 'concentrations.csv'} ...")
    df.to_csv(statsdir / "concentrations.csv", index=False)
    df.head(10).to_csv(statsdir / "concentrations_test.csv", index=False)
    logger.info("Done.")
