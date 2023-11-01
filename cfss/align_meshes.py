import argparse
import sys
from pathlib import Path

import numpy as np
from utils import read_mesh, write_mesh
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy


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


from vtkmodules.vtkCommonDataModel import vtkPolyData


class TopMiddleAlign:
    @staticmethod
    def calc_rep_point(points: np.ndarray):
        bb = calc_bb(points)
        bb[0][2] = bb[1][2]
        return (bb[0] + bb[1]) / 2

    def __init__(self, ref: vtkPolyData):
        ref_points = vtk_to_numpy(ref.GetPoints().GetData())
        self.ref = self.calc_rep_point(ref_points)

    def align(self, moving: vtkPolyData):
        points = vtk_to_numpy(moving.GetPoints().GetData())
        rep = self.calc_rep_point(points)
        tr = rep - self.ref
        moved_points = points - tr
        moving.GetPoints().SetData(numpy_to_vtk(moved_points))
        return moving


def main():
    parser = argparse.ArgumentParser(description='argparse example.')
    parser.add_argument('reference', help='Reference/Fixed mesh filename')
    parser.add_argument('output', help='Output directory')
    parser.add_argument('meshes', help='Moving mesh filenames', nargs='+')

    args = parser.parse_args()

    ref_mesh = read_mesh(args.reference)
    aligner = TopMiddleAlign(ref_mesh)
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    for fn in args.meshes:
        moving_mesh = read_mesh(fn)
        moved = aligner.align(moving_mesh)
        outname = outdir / Path(fn).name
        write_mesh(str(outname), moved)


if __name__ == '__main__':
    sys.exit(main())
