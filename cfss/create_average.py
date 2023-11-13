from pathlib import Path
from typing import List, Union

import numpy as np
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy
from vtkmodules.vtkFiltersGeneral import (
    vtkMultiBlockDataGroupFilter,
    vtkTransformPolyDataFilter,
)
from vtkmodules.vtkFiltersHybrid import vtkProcrustesAlignmentFilter

from cfss.utils import calculate_normals, read_mesh, write_mesh


# https://github.com/Kitware/VTK/blob/master/Filters/Hybrid/Testing/Python/TestPCA.py


def create(filenames: List[Union[str, Path]], output: Path, ref_index=0):
    polys = [read_mesh(str(fn)) for fn in filenames]

    group = vtkMultiBlockDataGroupFilter()
    for poly in polys:
        group.AddInputData(poly)
    procrustes = vtkProcrustesAlignmentFilter()
    procrustes.SetInputConnection(group.GetOutputPort())
    procrustes.GetLandmarkTransform().SetModeToRigidBody()  # TODO: maybe affine
    procrustes.Update()

    polys = [procrustes.GetOutput().GetBlock(i) for i in range(len(polys))]
    poly_points = [vtk_to_numpy(poly.GetPoints().GetData()).copy() for poly in polys]
    all_points = np.stack(poly_points)
    mean_poly = polys[ref_index]
    mean_points = all_points.mean(axis=0)
    mean_poly.GetPoints().SetData(numpy_to_vtk(mean_points))
    write_mesh(output, calculate_normals(mean_poly))
