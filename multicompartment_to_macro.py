from pantarei.fenicsstorage import FenicsStorage, delete_dataset
from multidiffusion_model import get_default_coefficients, print_progress
import dolfin as df

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
df.set_log_level(df.LogLevel.WARNING)

if __name__ == "__main__":
    phi = [phi_j for phi_j in get_default_coefficients()["porosity"].values()]
    phi_tot = sum(phi)
    compartments = ["ecs", "pvs"]
    data_file = "DATA/PAT_002/FENICS/cdata_32.hdf"

    logger.info(f"Reading 'multidiffusion' from {data_file}")
    storage = FenicsStorage(data_file, "a")
    timevec = storage.read_timevector("multidiffusion")
    u = storage.read_function("multidiffusion", idx=0)

    logger.info(f"Computing macroscopic concentration at t={timevec[0]}")
    c = df.Function(u.function_space().sub(0).collapse())
    c.vector()[:] = sum([phi[j] * uj.vector() for j, uj in enumerate(u.split(deepcopy=True))])
    storage.write_function(c, "/multidiffusion_total", overwrite=True)

    for idx, ti in enumerate(timevec[1:]):
        print_progress(float(ti), timevec[-1], rank=df.MPI.comm_world.rank)
        u = storage.read_checkpoint(u, "multidiffusion", idx=idx+1)
        c.vector()[:] = sum([phi[j] * uj.vector() for j, uj in enumerate(u.split(deepcopy=True))])
        storage.write_checkpoint(c, "/multidiffusion_total", ti)
    storage.close()

    file = FenicsStorage(storage.filepath, "r")
    file.to_xdmf("multidiffusion_total", "total")
    file.close()