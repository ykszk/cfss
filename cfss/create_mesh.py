import argparse
import sys

import pyacvd
import pyvista as pv
from utils import calculate_normals, write_mesh
from vtkmodules.vtkFiltersCore import vtkWindowedSincPolyDataFilter
from vtkmodules.vtkFiltersGeneral import vtkDiscreteMarchingCubes
from vtkmodules.vtkIOImage import vtkMetaImageReader, vtkNIFTIImageReader


def main():
    parser = argparse.ArgumentParser(description='Fast marching (level set).')
    parser.add_argument('input', help='Input segmentation filename', metavar='<input>')
    parser.add_argument('output', help='Output vtp/xml filename', metavar='<output>')
    parser.add_argument('--points', help='Number of pints in the mesh. default: %(default)s', type=int, default=80000)
    args = parser.parse_args()

    if args.input.endswith('.nii.gz'):
        reader = vtkNIFTIImageReader()
    else:
        reader = vtkMetaImageReader()
    reader.SetFileName(args.input)
    reader.Update()
    discrete = vtkDiscreteMarchingCubes()
    discrete.SetInputData(reader.GetOutput())
    discrete.SetValue(0, 1)

    smoothing_iterations = 20
    pass_band = 0.001
    feature_angle = 45.0

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

    pv_mesh = pv.wrap(smoother.GetOutput())
    clus = pyacvd.Clustering(pv_mesh)
    # mesh is not dense enough for uniform remeshing
    # clus.subdivide(3)
    clus.cluster(args.points)
    remeshed = clus.create_mesh()

    normals = calculate_normals(remeshed)

    write_mesh(args.output, normals)


if __name__ == '__main__':
    sys.exit(main())
