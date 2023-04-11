#!/usr/bin/env python
from argparse import ArgumentParser
from pathlib import Path

import SVMTK

from pantarei.meshprocessing import stl2hdf

parser = ArgumentParser(
    description="""
                geo2dolfin
                --------------
                Convert a pair of stl-files ('brain.stl', 'ventricles.stl') representing the brain and ventricles of
                a ratbrain into a dolfin mesh, where the ventricles are excluded. Assumes the stl-files are stored in
                the same directory, given by the '--inputdir'-argument."""
)
meshdir = f"{Path(__file__).resolve().parent}"
parser.add_argument("--resolution", type=int, required=True, nargs="+")
parser.add_argument("--patid", type=str)
args = parser.parse_args()

# Parse paths
patdir = Path(f"DATA/{args.patid}")
inputdir = patdir / "SLICER"
outputdir = patdir / "FENICS"
tmpdir = patdir / "FENICS/domain"
# TODO: Allow for differently named output-files? Need to decide how to combine with multiple resolution inputs.
# if args.outfile != meshdir:
#     outfile = Path(args.outfile).resolve()
#     assert outfile.suffix == "h5", "output file should be of type .h5"
#     assert length(args.resolution)

surfaces = [inputdir / "CSFSegments_Parenchyma.stl", inputdir / "CSFSegments_Ventricles_and_CSF.stl"]

# Define subdomains
smap = SVMTK.SubdomainMap()
smap.add("10", 1)  # Brain matter
smap.add("01", 2)  # Ventricles
smap.add("11", 2)  # Possible overlap between the two are labelled as ventricles.
for res in args.resolution:
    print()
    print(f"Creating mesh with resolution {res}.")
    output = outputdir / f"mesh{res}.h5"
    tmpdir = Path()
    stl2hdf(surfaces, output, res, subdomain_map=smap, remove_subdomains=2, tmpdir=tmpdir)

