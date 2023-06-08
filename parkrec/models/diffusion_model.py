import dolfin as df
from dolfin import grad, inner
from pantarei.boundary import DirichletBoundary, process_dirichlet
from pantarei.fenicsstorage import FenicsStorage
from pantarei.interpolator import vectordata_interpolator
from pantarei.timekeeper import TimeKeeper


def print_progress(t, T, rank=0):
    if rank != 0:
        return
    progress = int(40 * t / T)
    print(f"[{'=' * progress}{' ' * (40 - progress)}]", end="\r", flush=True)


def read_concentration_data(filepath, funcname="data") -> list[df.Function]:
    store = FenicsStorage(filepath, "r")
    tvec = store.read_timevector(funcname)
    c = store.read_function(funcname, idx=0)
    C = [df.Function(c.function_space()) for _ in range(tvec.size)]
    for idx in range(len(C)):
        store.read_checkpoint(C[idx], funcname, idx)
    return tvec, C


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("patientid", help="Patient ID on the form PAT_###")
    args = parser.parse_args()

    datapath = f"data/{args.patientid}/FENICS/data.hdf"
    timevec, data = read_concentration_data(datapath)
    u0 = data[0].copy(deepcopy=True)
    u_interp = u0.copy(deepcopy=True)
    interpolator = vectordata_interpolator(data, timevec)

    V = u0.function_space()
    domain = V.mesh()

    dt = 3600
    T = timevec[-1]
    time = TimeKeeper(dt=dt, endtime=T)

    boundaries = [DirichletBoundary(u_interp, "everywhere")]
    bcs = process_dirichlet(V, domain, boundaries)

    D = 1.65e-4  # mm^2/s
    dx = df.Measure("dx", V.mesh())
    u = df.TrialFunction(V)
    v = df.TestFunction(V)
    F = ((u - u0) * v + dt * (inner(D * grad(u), grad(v)))) * dx  # type: ignore
    a = df.lhs(F)
    l = df.rhs(F)
    A = df.assemble(a)

    u = df.Function(V)
    u.assign(u0)
    storage = FenicsStorage(datapath, "a")
    storage.write_function(u, "diffusion", overwrite=True)

    time.reset()
    for ti in time:
        print_progress(float(ti), time.endtime, rank=df.MPI.comm_world.rank)
        u_interp.vector()[:] = interpolator(float(ti))
        b = df.assemble(l)
        for bc in bcs:
            bc.apply(A, b)
        df.solve(A, u.vector(), b, "gmres", "hypre_amg")
        storage.write_checkpoint(u, "diffusion", float(ti))
        u0.assign(u)
    storage.close()

    file = FenicsStorage(storage.filepath, "r")
    file.to_xdmf("diffusion", "diffusion")
    file.close()
