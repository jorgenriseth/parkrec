import subprocess
import logging
import meshio
from pathlib import Path

import dolfin as df
import SVMTK as svmtk

from meshprocessing import xdmf2hdf, mesh2xdmf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_patient_mesh(patientdir, resolution):
    fenics_path = patientdir / "FENICS"
    fenics_path.mkdir(exist_ok=True)
    surfaces = ("lh.pial", "rh.pial", "lh.white", "rh.white", "ventricles")
    surfaces = [patientdir / "surf" / surf for surf in surfaces]
    stls = [fenics_path / f"{surf.name}.stl" for surf in surfaces]

    for surface, stl in zip(surfaces, stls):
        if "ventricles" in surface.name:
            continue
        subprocess.run(f"mris_convert {surface} {stl}", shell=True)

    return create_brain_mesh(
        stls,
        fenics_path / f"brain{resolution}.mesh",
        resolution,
        remove_ventricles=True,
    )


def create_ventricle_surface(patientdir):
    input = patientdir / "mri/wmparc.mgz"
    output = patientdir / "FENICS/ventricles.stl"
    if not output.exists():
        subprocess.run(
            f"bash scripts/extract-ventricles.sh {input} {output}", shell=True
        )


def create_brain_mesh(stls, output, resolution=32, remove_ventricles=True):
    """Taken from original mri2fem-book:
    https://github.com/kent-and/mri2fem/blob/master/mri2fem/mri2fem/chp4/fullbrain-five-domain.py
    """
    logger.info(f"Creating brain mesh from surfaces {stls}")
    surfaces = [svmtk.Surface(str(stl)) for stl in stls]
    # FIXME: Remove numbered references as this is very change sensitive
    # Merge lh rh surface, and drop the latter.
    surfaces[2].union(surfaces[3])
    surfaces.pop(3)

    # Define identifying tags for the different regions
    tags = {"pial": 1, "white": 2, "ventricle": 3}

    # Label the different regions
    smap = svmtk.SubdomainMap()
    smap.add("1000", tags["pial"])
    smap.add("0100", tags["pial"])
    smap.add("1010", tags["white"])
    smap.add("0110", tags["white"])
    smap.add("1110", tags["white"])
    smap.add("1011", tags["ventricle"])
    smap.add("0111", tags["ventricle"])
    smap.add("1111", tags["ventricle"])

    # Generate mesh at given resolution
    domain = svmtk.Domain(surfaces, smap)
    domain.create_mesh(resolution)

    # Remove ventricles perhaps
    if remove_ventricles:
        domain.remove_subdomain(tags["ventricle"])

    # Save mesh
    domain.save(str(output))
    #subprocess.run(f"meshio convert {output} {output.with_suffix('.xdmf')}", shell=True)
    xdmfdir = patientdir / "FENICS/mesh_xdmf"
    xdmfdir.mkdir(exist_ok=True)
    mesh2xdmf(output, xdmfdir)
    return xdmf2hdf(xdmfdir, output.with_suffix(".h5"))


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("patientid", help="Patient ID on the form PAT_###")
    parser.add_argument("resolution", help="SVMTK mesh resolution.", type=int)
    args = parser.parse_args()

    patientdir = Path("DATA") / args.patientid
    logger.info(f"Working in {patientdir}")
    create_ventricle_surface(patientdir)
    meshfile = create_patient_mesh(patientdir, args.resolution)
    logger.info(f"Generated mesh in file {meshfile}")
