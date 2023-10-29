import argparse
import sys

from logzero import logger
from probreg import cpd
from utils import read_mesh, write_mesh
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy


def main():
    parser = argparse.ArgumentParser(description='Fast marching (level set).')
    parser.add_argument('source', help='Source vtp filename', metavar='<input>')
    parser.add_argument('target', help='Target vtp filename', metavar='<output>')
    parser.add_argument('output', help='Output vtp filename', metavar='<output>')
    parser.add_argument('--reduction', help='Target reduction rate. default: %(default)s', default=0.95)
    args = parser.parse_args()

    source = read_mesh(args.source)
    target = read_mesh(args.target)

    tgt_points = vtk_to_numpy(target.GetPoints().GetData()).copy()
    src_points = vtk_to_numpy(source.GetPoints().GetData()).copy()
    print(tgt_points.shape, src_points.shape)

    logger.info('register: affine')
    tf_param, _, _ = cpd.registration_cpd(src_points, tgt_points, maxiter=50, tf_type_name='affine')
    logger.info('done')
    tfed_src = tf_param.transform(src_points.copy())

    logger.info('register: nonrigid')
    tf_param2, _, _ = cpd.registration_cpd(tfed_src, tgt_points, maxiter=100, tf_type_name='nonrigid', lmd=0.1)
    logger.info('done')

    tfed_src2 = tf_param2.transform(tfed_src.copy())
    pts = source.GetPoints()
    tfed_pts = numpy_to_vtk(tfed_src2)
    pts.SetData(tfed_pts)

    write_mesh(args.output, source)


if __name__ == '__main__':
    sys.exit(main())
