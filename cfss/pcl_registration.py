#%%
from vtkmodules.util.numpy_support import vtk_to_numpy, numpy_to_vtk
from logzero import logger
from utils import read_mesh, write_mesh
from pathlib import Path

# https://github.com/siavashk/pycpd/tree/master/examples

with open('./filenames.txt') as f:
    fns = [l.rstrip() for l in f.readlines()]
outdir = Path('registered')
outdir.mkdir(parents=True, exist_ok=True)
for fn in fns[1:]:
    print(fn)
    source = read_mesh('mesh/CHUH0001.vtp')
    target = read_mesh(f'mesh_fine/{fn}.vtp')

    tgt_points = vtk_to_numpy(target.GetPoints().GetData()).copy()
    src_points = vtk_to_numpy(source.GetPoints().GetData()).copy()
    print(tgt_points.shape, src_points.shape)

    #%%
    # from pycpd import DeformableRegistration
    # src_subset = src_points[::100]
    # # tgt_subset = tgt_points[::4]
    # reg = DeformableRegistration(**{'X': tgt_points, 'Y': src_subset})
    # reg.register()
    # logger.info('done')
    # #%%
    # YT = reg.transform_point_cloud(Y=src_points)
    # # %%

    #%%
    from probreg import cpd
    logger.info('register: affine')
    tf_param, _, _ = cpd.registration_cpd(src_points,
                                          tgt_points,
                                          maxiter=2,
                                          tf_type_name='affine')
    logger.info('done')
    tfed_src = tf_param.transform(src_points.copy())

    # pts = source.GetPoints()
    # tfed_pts = numpy_to_vtk(tfed_src)
    # pts.SetData(tfed_pts)
    # write_mesh('reged_affine.vtp', source)
    #%%

    logger.info('register: nonrigid')
    tf_param2, _, _ = cpd.registration_cpd(tfed_src,
                                           tgt_points,
                                           maxiter=100,
                                           tf_type_name='nonrigid',
                                           lmd=0.1)
    logger.info('done')

    #%%

    tfed_src2 = tf_param2.transform(tfed_src.copy())
    pts = source.GetPoints()
    tfed_pts = numpy_to_vtk(tfed_src2)
    pts.SetData(tfed_pts)

    # from vtkmodules.vtkFiltersCore import vtkPolyDataNormals
    # normals = vtkPolyDataNormals()
    # normals.SetInputData(source)
    # normals.Update()

    write_mesh(str(outdir / f'{fn}.vtp'), source)
