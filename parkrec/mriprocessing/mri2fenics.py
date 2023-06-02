import dolfin as df
# from dolfin_adjoint import *
import datetime
# from datetime import datetime
import nibabel
import numpy
from nibabel.affines import apply_affine
import argparse
from pathlib import Path

import logging
from pantarei.fenicsstorage import FenicsStorage
from typing import List


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def read_image(filename, functionspace, data_filter=None):
    mri_volume = nibabel.load(filename)
    voxeldata = mri_volume.get_fdata()

    c_data = df.Function(functionspace, name="concentration")
    ras2vox_tkr_inv = numpy.linalg.inv(mri_volume.header.get_vox2ras_tkr())

    xyz = functionspace.tabulate_dof_coordinates()
    ijk = apply_affine(ras2vox_tkr_inv, xyz).T
    i, j, k = numpy.rint(ijk).astype("int")
    
    if data_filter is not None:
        voxeldata = data_filter(voxeldata, ijk, i, j, k)
        c_data.vector()[:] = voxeldata[i, j, k]
    else:
        if numpy.where(numpy.isnan(voxeldata[i, j, k]), 1,0).sum() > 0:
            print("No filter used, setting", numpy.where(numpy.isnan(voxeldata[i, j, k]), 1, 0).sum(), "/", i.size, " nan voxels to 0")
            voxeldata[i, j, k] = numpy.where(numpy.isnan(voxeldata[i, j, k]), 0, voxeldata[i, j, k])
        if numpy.where(voxeldata[i, j, k] < 0, 1,0).sum() > 0:
            print("No filter used, setting", numpy.where(voxeldata[i, j, k] < 0, 1, 0).sum(), "/", i.size, " voxels in mesh have value < 0")

        c_data.vector()[:] = voxeldata[i, j, k]

    return c_data

def image_timestamp(p: Path) -> datetime.datetime:
    return datetime.datetime.strptime(p.stem, "%Y%m%d_%H%M%S")

def injection_timestamp(injection_time_file: Path) -> datetime:
    with open(injection_time_file, "r") as f:
        time_string = f.read()
    return datetime.datetime.strptime(time_string, "%H.%M.%S").time()


def fenicsstorage2xdmf(filepath, funcname: str, subnames: str | List[str]) -> None:
    file = FenicsStorage(filepath, "r")
    file.to_xdmf(funcname, subnames)
    file.close()

if __name__ == "__main__":
    import argparse
    from pathlib import Path
    from pantarei.fenicsstorage import FenicsStorage
    import pantarei as pr

    parser = argparse.ArgumentParser()
    parser.add_argument("patientid", help="PatientID on the form PAT_XXX")
    parser.add_argument("resolution", type=int, help="Resolution of mesh to use.")
    parser.add_argument("--concentrationdir", type=str, default="CONCENTRATIONS")
    parser.add_argument("--femfamily", type=str, default="DG")
    parser.add_argument("--femdegree", type=int, default=0)
    args = parser.parse_args()

    patientdir = Path("DATA") / args.patientid
    meshfile = patientdir / f"FENICS/brain{args.resolution}.h5"

    from meshprocessing import hdf2fenics
    mesh, _, _ = hdf2fenics(meshfile)

    V = df.FunctionSpace(mesh, args.femfamily, args.femdegree)

    output = patientdir / f"FENICS/cdata_{args.resolution}.hdf"
    concentration_data = sorted((patientdir / args.concentrationdir).iterdir())#[1:]
    outfile = FenicsStorage(str(output), "w")
    outfile.write_domain(mesh)

    start_date = image_timestamp(concentration_data[0]).date()
    injection_time_of_day = injection_timestamp(patientdir / "injection_time.txt")
    t0 = datetime.datetime.combine(start_date, injection_time_of_day)

    for cfile in concentration_data:
        c_data_fenics = read_image(filename=cfile, functionspace=V, data_filter=None)
        ti = max(0, (image_timestamp(cfile) - t0).total_seconds())
        outfile.write_checkpoint(c_data_fenics, name="cdata", t=ti)
    outfile.close()
    fenicsstorage2xdmf(outfile.filepath, "cdata", "cdata")
