#%%
from utils import read_mesh
from vtkmodules.util.numpy_support import vtk_to_numpy, numpy_to_vtk

poly1 = read_mesh('./registered/CHUH0002.vtp')
poly2 = read_mesh('./registered/CHUH0004.vtp')

tgt_points = vtk_to_numpy(poly1.GetPoints().GetData()).copy()
src_points = vtk_to_numpy(poly2.GetPoints().GetData()).copy()
print(tgt_points.shape, src_points.shape)
# %%

from vtkmodules.vtkFiltersCore import vtkPolyDataNormals
normals = vtkPolyDataNormals()
# %%
