import argparse
import sys

from utils import write_mesh
from vtkmodules.vtkFiltersCore import (
    vtkPolyDataNormals,
    vtkQuadricDecimation,
    vtkWindowedSincPolyDataFilter,
)
from vtkmodules.vtkFiltersGeneral import vtkDiscreteMarchingCubes
from vtkmodules.vtkIOImage import vtkMetaImageReader


def main():
    parser = argparse.ArgumentParser(description='Fast marching (level set).')
    parser.add_argument('input', help='Input segmentation filename', metavar='<input>')
    parser.add_argument('output', help='Output vtp filename', metavar='<output>')
    parser.add_argument('--reduction', help='Target reduction rate. default: %(default)s', type=float, default=0.95)
    args = parser.parse_args()

    reader = vtkMetaImageReader()
    reader.SetFileName(args.input)
    reader.Update()
    discrete = vtkDiscreteMarchingCubes()
    discrete.SetInputData(reader.GetOutput())
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
    decimate.SetTargetReduction(args.reduction)
    decimate.SetInputData(smoother.GetOutput())
    decimate.Update()

    normals = vtkPolyDataNormals()
    normals.SetInputData(decimate.GetOutput())
    normals.Update()

    write_mesh(args.output, normals.GetOutput())


if __name__ == '__main__':
    sys.exit(main())
