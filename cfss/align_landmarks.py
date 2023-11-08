import argparse
import sys

import landmark
import vtkmodules.vtkRenderingFreeType
import vtkmodules.vtkRenderingOpenGL2
from utils import calculate_normals, read_mesh, write_mesh
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonTransforms import vtkLandmarkTransform
from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter


# https://github.com/Kitware/VTK/blob/master/Filters/Hybrid/Testing/Python/TestPCA.py


def main():
    parser = argparse.ArgumentParser(description='Align two meshes using lanrmark points.')
    parser.add_argument('fixed', help='Input mesh filename')
    parser.add_argument('landmark', help='Lanrmark filename (.mrk.json)')
    parser.add_argument('moving', help='Input mesh filename')
    parser.add_argument('output', help='Output mesh filename')
    parser.add_argument(
        '--mode',
        help='Transformation mode. default: %(default)s',
        default='rigid',
        choices=['rigid', 'similarity', 'affine'],
    )

    args = parser.parse_args()

    landmark_labels = ['Menton', 'Lamda', 'Bregma', 'GonionL', 'GonionR', 'ZygionL', 'ZygionR']

    fixed_mesh = read_mesh(args.fixed)
    landmarks = landmark.load_landmarks(args.landmark)
    landmark_idx = [i for i, lm in enumerate(landmarks) if lm.label in landmark_labels]
    all_lm_pts_idx = landmark.locate_landmarks(fixed_mesh, landmarks)
    lm_pts_idx = [all_lm_pts_idx[i] for i in landmark_idx]
    moving_mesh = read_mesh(args.moving)

    lms = []
    for mesh in [fixed_mesh, moving_mesh]:
        vtklm = vtkPoints()
        for idx in lm_pts_idx:
            pts = mesh.GetPoint(idx)
            vtklm.InsertNextPoint(pts)
        lms.append(vtklm)

    ltf = vtkLandmarkTransform()
    ltf.SetSourceLandmarks(lms[1])
    ltf.SetTargetLandmarks(lms[0])
    if args.mode == 'rigid':
        ltf.SetModeToRigidBody()
    elif args.mode == 'similarity':
        ltf.SetModeToSimilarity()
    elif args.mode == 'affine':
        ltf.SetModeToAffine()
    else:
        raise RuntimeError(f'Invalid mode: {args.mode}')
    ltf.Update()

    tf = vtkTransformPolyDataFilter()
    tf.SetTransform(ltf)
    tf.SetInputData(moving_mesh)
    tf.Update()
    tfed = calculate_normals(tf.GetOutput())
    write_mesh(args.output, tfed)


if __name__ == '__main__':
    sys.exit(main())
