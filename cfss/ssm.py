from pathlib import Path
from typing import List, Tuple, Union

import numpy as np
from sklearn.decomposition import PCA
from utils import calculate_normals, read_mesh
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy
from vtkmodules.vtkCommonDataModel import vtkPolyData


class PCAStats:
    def __init__(self, X):
        pca = PCA()
        self.all_coefs = pca.fit_transform(X)
        self.components = pca.components_.reshape(len(pca.components_), -1, 3)
        self.mean = pca.mean_.reshape(-1, 3)
        self.pca = pca

    @staticmethod
    def from_files(filenames: List[Union[str, Path]]) -> Tuple['PCAStats', vtkPolyData]:
        '''
        returns stats and average shape
        '''
        polys = [read_mesh(str(fn)) for fn in filenames]
        poly_points = [vtk_to_numpy(poly.GetPoints().GetData()).copy() for poly in polys]

        all_points = np.stack(poly_points)
        all_data = all_points.reshape(len(all_points), -1)
        mean_poly = polys[0]
        mean_points = all_points.mean(axis=0)
        mean_poly.GetPoints().SetData(numpy_to_vtk(mean_points))
        return PCAStats(all_data), calculate_normals(mean_poly)

    def get_points(self, pid: int):
        pts = self.mean[pid] + self.all_coefs @ self.components[:, pid, :]
        return pts

    def dists_between(self, pid1: int, pid2: int) -> np.ndarray:
        p1 = self.get_points(pid1)
        p2 = self.get_points(pid2)
        diff = p1 - p2
        return np.linalg.norm(diff, axis=1)
