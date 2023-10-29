import sys
import argparse
import logzero
from logzero import logger
import cc3d
from scipy import ndimage
import numpy as np
from szkmipy import mhd
from szkmipy import boundingbox as bb
from vtkmodules.vtkIOXML import vtkXMLPolyDataReader, vtkXMLPolyDataWriter
from vtkmodules.vtkCommonDataModel import vtkPolyData
import shutil

def read_mesh(filename: str) -> vtkPolyData:
    reader = vtkXMLPolyDataReader()
    reader.SetFileName(filename)
    reader.Update()
    return reader.GetOutput()


def write_mesh(filename: str, mesh):
    writer = vtkXMLPolyDataWriter()
    writer.SetFileName(filename)
    writer.SetInputData(mesh)
    writer.Update()


def segment_body(vol):
    iterations = 3
    body = vol > 0
    bbox = bb.bbox(body)
    body = bb.crop(body, bbox, margin=iterations + 1)
    logger.debug('closing')
    body = ndimage.binary_closing(body, structure=np.ones((3, 3, 3)))
    logger.debug('fill holes')
    # body = ndimage.binary_fill_holes(body, structure=np.ones((1, 3, 3)))
    for i in range(len(body)):
        ndimage.binary_fill_holes(body[i],
                                  structure=np.ones((3, 3)),
                                  output=body[i])
    logger.debug('largest')
    labels_out = cc3d.largest_k(body, k=1)
    logger.debug('dilation')
    dilated = ndimage.binary_dilation(labels_out,
                                      structure=np.ones((3, 3, 3)),
                                      iterations=iterations)
    body = bb.uncrop(body,
                     vol.shape,
                     bbox,
                     margin=iterations + 1,
                     constant_values=0)
    dilated = bb.uncrop(dilated,
                        vol.shape,
                        bbox,
                        margin=iterations + 1,
                        constant_values=0)
    return body, dilated


def remove_bed(input_filename, output=None, mask=None):

    logger.debug('Load input image')
    vol, h = mhd.read(input_filename)
    body, dilated = segment_body(vol)
    min_value, max_value = -1000, 2000
    vol = np.clip(vol, min_value, max_value)
    vol[dilated == 0] = min_value
    if mask:
        logger.debug('Save mask')
        mhd.write(mask, body.astype(np.uint8), h)
    if output:
        logger.debug('Save output')
        mhd.write(output, vol, h)

def del_dirs(exec: bool, ds: list):
    if exec:
        print('Deleting directories...')
        for d in ds:
            print(d)
            shutil.rmtree(d)
    else:
        print('This is a dryrun. Following directories are listed for deletion...')
        for d in ds:
            print(' -',d)
        print('Execute command with `--exec` option to actually execute the deletion.')

def main():
    parser = argparse.ArgumentParser(description='CFDB utilities.')
    parser.add_argument('-v',
                        '--verbose',
                        help='Debug output',
                        action='store_true')

    subparsers = parser.add_subparsers()
    sub_remove = subparsers.add_parser('remove_bed',
                                       help="Remove bed from CT image")
    sub_remove.add_argument('input', help='Input filename')
    sub_remove.add_argument('output', help='Output filename', nargs='?')
    sub_remove.add_argument('-m',
                            '--mask',
                            help='Save maks image',
                            metavar='filename')

    def command_remove_bed(args):
        if args.output is None and args.mask is None:
            print(
                'At least either one of --output or --mask needs to be specified.'
            )
            sys.exit(1)
        return remove_bed(args.input, args.output, args.mask)

    sub_remove.set_defaults(handler=command_remove_bed)
    args = parser.parse_args()

    if args.verbose:
        logzero.loglevel(logzero.DEBUG)

    if not hasattr(args, 'handler'):
        print('No command was specified.')
        parser.print_help()
        sys.exit(1)
    return (args.handler(args))


if __name__ == '__main__':
    sys.exit(main())
