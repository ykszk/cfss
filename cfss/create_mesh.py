import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkFiltersCore import vtkWindowedSincPolyDataFilter, vtkQuadricDecimation, vtkPolyDataNormals
from vtkmodules.vtkFiltersGeneral import vtkDiscreteMarchingCubes
from vtkmodules.vtkIOImage import (
    vtkMetaImageReader, )
from vtkmodules.vtkIOXML import vtkXMLPolyDataWriter
from pathlib import Path

with open('filenames.txt') as f:
    filenames = [l.rstrip() for l in f.readlines()]

indir = Path('fast_marching')
for outdir, reduction in [('mesh', .95), ('mesh_fine', .90)]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for fn in filenames:
        print(fn, reduction)
        reader = vtkMetaImageReader()
        reader.SetFileName(f'./fast_marching/{fn}.mha')
        reader.Update()
        discrete = vtkDiscreteMarchingCubes()
        discrete.SetInputData(reader.GetOutput())
        # discrete.GenerateValues(n, 1, n)
        discrete.SetValue(0, 1)

        smoothing_iterations = 15
        pass_band = 0.001
        feature_angle = 120.0

        smoother = vtkWindowedSincPolyDataFilter()
        smoother.SetInputConnection(discrete.GetOutputPort())
        smoother.SetNumberOfIterations(smoothing_iterations)
        smoother.BoundarySmoothingOff()
        smoother.FeatureEdgeSmoothingOff()
        smoother.SetFeatureAngle(feature_angle)
        smoother.SetPassBand(pass_band)
        smoother.NonManifoldSmoothingOn()
        smoother.NormalizeCoordinatesOn()
        smoother.Update()

        decimate = vtkQuadricDecimation()
        decimate.SetTargetReduction(reduction)
        decimate.SetInputData(smoother.GetOutput())
        decimate.Update()

        normals = vtkPolyDataNormals()
        normals.SetInputData(decimate.GetOutput())
        normals.Update()

        outname = outdir / f'{fn}.vtp'
        writer = vtkXMLPolyDataWriter()
        writer.SetInputData(normals.GetOutput())
        writer.SetFileName(str(outname))
        writer.Update()