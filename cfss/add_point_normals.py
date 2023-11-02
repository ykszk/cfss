import argparse
import sys

from utils import calculate_normals, read_mesh, write_mesh


def main():
    parser = argparse.ArgumentParser(description='Calculate point normals from polygon data.')
    parser.add_argument('input', help='Input mesh filename')
    parser.add_argument('output', help='Output mesh filename')

    args = parser.parse_args()

    mesh = read_mesh(args.input)
    mesh_w_normals = calculate_normals(mesh)

    write_mesh(args.output, mesh_w_normals)


if __name__ == '__main__':
    sys.exit(main())
