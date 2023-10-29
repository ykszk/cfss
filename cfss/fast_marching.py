import argparse
import itertools
import sys

import numpy as np
import SimpleITK as sitk
from logzero import logger
from szkmipy import boundingbox


def main():
    parser = argparse.ArgumentParser(description='Fast marching (level set).')
    parser.add_argument('input', help='Input filename', metavar='<input>')
    parser.add_argument('output', help='Output filename', metavar='<output>')
    parser.add_argument('--factor', help='Normalization factor. default: %(default)s', default=200)
    parser.add_argument('--stop', help='Stopping time. default: %(default)s', default=100)

    args = parser.parse_args()

    inputImage = sitk.ReadImage(args.input)

    resample = sitk.ResampleImageFilter()
    resample.SetInterpolator(sitk.sitkLinear)
    resample.SetOutputDirection(inputImage.GetDirection())
    resample.SetOutputOrigin(inputImage.GetOrigin())
    orig_spacing = np.array(inputImage.GetSpacing())
    new_spacing = (2 * orig_spacing).tolist()
    resample.SetOutputSpacing(new_spacing)
    orig_size = np.array(inputImage.GetSize())
    new_size = np.ceil(orig_size / 2).astype(int).tolist()
    resample.SetSize(new_size)
    resampled = resample.Execute(inputImage)

    seg_arr = sitk.GetArrayFromImage(resampled)
    bmin, bmax = boundingbox.bbox(seg_arr)
    bmin = np.clip(bmin - 1, 0, None)
    bmax = np.clip(bmax + 1, None, seg_arr.shape)
    bmid = np.round((bmin + bmax) / 2).astype(int)
    bbox = [bmin, bmid, bmax]

    dist_filter = sitk.SignedMaurerDistanceMapImageFilter()
    dist_image = dist_filter.Execute(resampled)
    fastMarching = sitk.FastMarchingImageFilter()

    timeThreshold = 100

    seedValue = 0
    for x, y, z in itertools.product([0, 2], [0, 2], [0, 2]):
        if x == 1 and y == 1 and z == 1:
            continue
        trialPoint = (int(bbox[x][0]), int(bbox[y][1]), int(bbox[z][2]), seedValue)
        fastMarching.AddTrialPoint(trialPoint)

    fastMarching.SetNormalizationFactor(args.factor)

    fastMarching.SetStoppingValue(args.stop)

    fastMarchingOutput = fastMarching.Execute(dist_image)

    thresholder = sitk.BinaryThresholdImageFilter()
    thresholder.SetLowerThreshold(0.0)
    thresholder.SetUpperThreshold(timeThreshold)
    thresholder.SetOutsideValue(1)
    thresholder.SetInsideValue(0)
    threshed = thresholder.Execute(fastMarchingOutput)

    erosion = sitk.BinaryErodeImageFilter()
    erosion.SetBackgroundValue(0)
    erosion.SetForegroundValue(1)
    erosion.SetKernelRadius(1)
    result = erosion.Execute(threshed)

    sitk.WriteImage(result, args.output, useCompression=True)


if __name__ == '__main__':
    sys.exit(main())
