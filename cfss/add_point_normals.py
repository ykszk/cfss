import argparse
import sys
from pathlib import Path

from logzero import logger
from utils import calculate_normals, read_mesh, write_mesh


def process(infile, outfile):
    mesh = read_mesh(infile)
    mesh_w_normals = calculate_normals(mesh)

    write_mesh(outfile, mesh_w_normals)


def main():
    parser = argparse.ArgumentParser(description='Calculate point normals from polygon data.')
    parser.add_argument('input', help='Input mesh filename')
    parser.add_argument('output', help='Output mesh filename. Overwrite input file by default', nargs='?')
    parser.add_argument('--ext', help='Input file extension. default: %(default)s', default='.vtk')

    args = parser.parse_args()
    if args.output is None:
        output = args.input
    else:
        output = args.output
    if Path(args.input).is_dir():
        logger.info('Processing directory: %s', args.input)
        indir = Path(args.input)
        outdir = Path(output)
        for fn in indir.glob('*' + args.ext):
            logger.info(str(fn))
            outfile = outdir / fn.name
            process(str(fn), str(outfile))
    else:
        process(args.input, output)


if __name__ == '__main__':
    sys.exit(main())
