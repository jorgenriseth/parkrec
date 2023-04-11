import time as pytime
from pathlib import Path
from typing import Dict, List, Any

import dolfin as df
import numpy as np
import ufl
from dolfin import inner, grad


import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
df.set_log_level(df.LogLevel.WARNING)

from pantarei.boundary import (
    DirichletBoundary,
    process_dirichlet,
    indexed_boundary_conditions,
)
from pantarei.fenicsstorage import FenicsStorage, delete_dataset
from pantarei.interpolator import vectordata_interpolator
from pantarei.timekeeper import TimeKeeper
from pantarei.utils import assign_mixed_function


def print_progress(t, T, rank=0):
    if rank != 0:
        return
    progress = int(40 * t / T)
    print(f"[{'=' * progress}{' ' * (40 - progress)}]", end="\r", flush=True)


def read_concentration_data(filepath) -> List[df.Function]:
    store = FenicsStorage(filepath, "r")
    tvec = store.read_timevector("cdata")
    c = store.read_function("cdata", idx=0)
    C = [df.Function(c.function_space()) for _ in range(tvec.size)]
    for idx in range(len(C)):
        store.read_checkpoint(C[idx], "cdata", idx)
    return tvec, C

def read_function_element(filepath, funcname) -> df.FunctionSpace:
    store = FenicsStorage(filepath, "r")
    el = store.read_element(funcname)
    store.close()
    return el

def compartment_form(
    idx_j: int,
    u: ufl.Argument,
    v: ufl.Argument,
    c0: df.Function,
    D: Dict[str, float],
    phi: Dict[str, float],
    alpha: float,
    P: float, 
    compartments: List[str],
) -> df.Form:
    j = compartments[idx_j]
    sj = sum(
        [
            (alpha * P / phi[j]) * (u[idx_i] - u[idx_j])
            for idx_i, i in enumerate(compartments)
            if idx_i != idx_j
        ]
    )
    return (
        (u[idx_j] - c0[idx_j] - dt * sj) * v[idx_j] 
        + dt * inner(D[j] * grad(u[idx_j]), grad(v[idx_j]))
    )


def multicomp_diffusion_form(
    V: df.FunctionSpace,
    coefficients: Dict[str, Any],
    c0: df.Function,
    compartments: List[str],
) -> df.Form:
    dx = df.Measure("dx", domain=V.mesh())
    u = df.TrialFunction(V)
    v = df.TestFunction(V)
    D = coefficients["diffusion_coefficient"]
    phi = coefficients["porosity"]
    alpha = coefficients["alpha"]
    P = coefficients["permeability"]
    return (
        sum(
            [
                compartment_form(idx_j, u, v, c0, D, phi, alpha, P,compartments)
                for idx_j, _ in enumerate(compartments)
            ]
        )
        * dx
    )


def get_default_coefficients() -> Dict[str, Any]:
    return {
        "porosity": {
            "ecs": 0.14,
            "pvs": 0.05,
        },
        "diffusion_coefficient": {
            "ecs": 1.65e-4,
            "pvs": 1.3e-3
        },
        "alpha": 5.0,
        "permeability": 1e-4,
    }

if __name__ == "__main__":
    compartments = ["ecs", "pvs"]
    # FIXME: Get proper values here.
    coefficients = get_default_coefficients()

    data_file = "DATA/PAT_002/FENICS/cdata_32.hdf"
    logger.info(f"Reading data from {data_file}")
    timevec, data = read_concentration_data(data_file)
    interpolator = vectordata_interpolator(data, timevec)
    c0 = data[0].copy(deepcopy=True)

    domain = c0.function_space().mesh()
    el = read_function_element(data_file, "cdata")
    element = df.MixedElement([el] * 2)
    V = df.FunctionSpace(domain, element)

    dt = 3600
    T = timevec[-1]  # FIXME: Only here for testing, switch to timevec[-1].
    time = TimeKeeper(dt=dt, endtime=T)

    # Define boundary conditions
    u_interp = {
        compartment: c0.copy(deepcopy=True)
        for compartment in compartments
    }
    phi = coefficients["porosity"]
    phi_tot = sum(phi.values())
    for key, val in u_interp.items():
        val.vector()[:] = (1.0 / phi_tot) * interpolator(0.0)

    boundary_data = {
        idx: [DirichletBoundary(u_interp[compartment], "everywhere")]
        for idx, compartment in enumerate(compartments)
    }
    boundaries = indexed_boundary_conditions(boundary_data)
    bcs = process_dirichlet(V, domain, boundaries)

    # Define variational problem
    u0 = assign_mixed_function(u_interp, V, compartments)
    F = multicomp_diffusion_form(V, coefficients, u0, compartments)
    a = df.lhs(F)
    l = df.rhs(F)
    A = df.assemble(a)

    u = df.Function(V)
    u.assign(u0)
    storage = FenicsStorage("DATA/PAT_002/FENICS/cdata_32.hdf", "a")
    storage.write_function(u, "multidiffusion", overwrite=True)
 
    logger.info("Starting time loop...")
    tic = pytime.time()
    time.reset()
    for ti in time:
        print_progress(float(ti), time.endtime, rank=df.MPI.comm_world.rank)
        for j, uj in u_interp.items():
            uj.vector()[:] = ((1.0 / phi_tot)) * interpolator(float(ti))
        b = df.assemble(l)
        for bc in bcs:
            bc.apply(A, b)
        df.solve(A, u.vector(), b, "gmres", "hypre_amg")
        storage.write_checkpoint(u, "multidiffusion", float(ti))
        u0.assign(u)
    storage.close()
    logger.info("Time loop finished.")
    toc = pytime.time()

    df.MPI.comm_world.barrier()
    if df.MPI.comm_world.rank == 0:
        logger.info(f"Elapsed time in loop: {toc - tic:.2f} seconds.")
    file = FenicsStorage(storage.filepath, "r")
    logger.info("Writing XDMF files for each compartment.")
    file.to_xdmf("multidiffusion", compartments)
    file.close()
