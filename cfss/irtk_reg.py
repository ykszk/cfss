import subprocess
from pathlib import Path


ADOF = 'areg.dof'
NDOF = 'nreg.dof'


def register(
    bin_dir: Path, moving: Path, fixed: Path, output: Path, log_dir: Path, epsilon: float, iterations: int, ds: int
):
    sareg = bin_dir / 'sareg.exe'
    snreg = bin_dir / 'snreg.exe'
    strans = bin_dir / 'stransformation.exe'
    locator = 0  # cell
    adof = log_dir / ADOF
    ndof = log_dir / NDOF

    common_opts = ['-epsilon', epsilon, '-symmetric', '-iterations', iterations]

    args = [sareg, moving, fixed, '-locator', locator, '-dofout', adof] + common_opts
    print([str(a) for a in args])
    subprocess.check_call([str(a) for a in args])

    args = [snreg, moving, fixed, '-locator', locator, '-dofin', adof, '-dofout', ndof, '-ds', ds] + common_opts
    print(' '.join([str(a) for a in args]))
    subprocess.check_call([str(a) for a in args])

    args = [strans, moving, output, '-dofin', ndof]
    subprocess.check_call([str(a) for a in args])
