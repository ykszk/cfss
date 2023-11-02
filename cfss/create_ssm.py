# %%
from pathlib import Path

import numpy as np
from utils import read_mesh, write_mesh
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy


indir = Path('../result/dev1031/register')
filenames = sorted(indir.glob('*.vtp'))

polys = [read_mesh(fn) for fn in filenames]
ref_poly = polys[0]
ref_points = vtk_to_numpy(ref_poly.GetPoints().GetData()).copy()
# poly1 = read_mesh('../result/dev1031/register/CHUH0002.vtp')
# poly2 = read_mesh('../result/dev1031/register/CHUH0015.vtp')

# tgt_points = vtk_to_numpy(poly1.GetPoints().GetData()).copy()
# src_points = vtk_to_numpy(poly2.GetPoints().GetData()).copy()
# print(tgt_points.shape, src_points.shape)
# %%


def calc_bb(points: np.ndarray):
    return [points.min(axis=0), points.max(axis=0)]


def calc_align_bb(tgt_points: np.ndarray, src_points: np.ndarray):
    '''
    Calculate scaling matrix and translation vector to align bounding boxes from src to tgt
    '''
    tgt_bb = calc_bb(tgt_points)
    src_bb = calc_bb(src_points)
    tgt_size = tgt_bb[1] - tgt_bb[0]
    src_size = src_bb[1] - src_bb[0]
    scale = tgt_size / src_size
    m_scale = np.diag(scale)
    v_tr = tgt_bb[0] - scale * src_bb[0]
    return m_scale, v_tr


def align_bb(tgt_points: np.ndarray, src_points: np.ndarray):
    '''
    Align bounding boxes of given point sets
    '''
    m_scale, v_tr = calc_align_bb(tgt_points, src_points)
    return src_points @ m_scale + v_tr


aligned_points = []
for i in range(len(polys)):
    moving_points = vtk_to_numpy(polys[i].GetPoints().GetData()).copy()
    if i == 0:
        moved_points = moving_points
    else:
        moved_points = align_bb(ref_points, moving_points)
    aligned_points.append(moved_points)
# moved_points = align_bb(tgt_points, src_points)
# calc_bb(moved_points), calc_bb(tgt_points)
# %%
# dists = np.linalg.norm(tgt_points - moved_points, axis=1)
# vtk_dists = numpy_to_vtk(dists)
# poly1.GetPointData().SetScalars(vtk_dists)
# write_mesh('mesh_w_dists.vtp', poly1)
from vtkmodules.vtkFiltersCore import vtkPolyDataNormals


all_points = np.stack(aligned_points)
average_points = all_points.mean(axis=0)
ref_poly.GetPoints().SetData(numpy_to_vtk(average_points))
normal = vtkPolyDataNormals()
normal.SetInputData(ref_poly)
normal.Update()
write_mesh('average_shape.vtp', normal.GetOutput())
