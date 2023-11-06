# %%
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from utils import read_mesh, write_mesh
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy


indir = Path('../result/lm_aligned')
filenames = sorted(indir.glob('*.vtk'))

polys = [read_mesh(str(fn)) for fn in filenames]
poly_points = [vtk_to_numpy(poly.GetPoints().GetData()).copy() for poly in polys]


all_points = np.stack(poly_points)
all_data = all_points.reshape(len(all_points), -1)


# %%
class PCAStats:
    def __init__(self, X):
        pca = PCA()
        self.all_coefs = pca.fit_transform(X)
        self.components = pca.components_.reshape(len(pca.components_), -1, 3)
        self.mean = pca.mean_.reshape(-1, 3)
        self.pca = pca

    def get_points(self, pid: int):
        pts = self.mean[pid] + self.all_coefs @ self.components[:, pid, :]
        return pts

    def dists_between(self, pid1: int, pid2: int):
        p1 = self.get_points(pid1)
        p2 = self.get_points(pid2)
        diff = p1 - p2
        return np.linalg.norm(diff, axis=1)


pca_stats = PCAStats(all_data)
pca_stats.dists_between(0, 2)
# %%
