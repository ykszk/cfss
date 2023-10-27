#%%
from pathlib import Path
import SimpleITK as sitk
from szkmipy import boundingbox
import numpy as np
import itertools
from logzero import logger

out_dir = Path('fast_marching')
out_dir.mkdir(parents=True, exist_ok=True)
# ct_dir = Path('./data/mha/')
# FNS = ['CHUH0001', 'CHUH0002','CHUH0004', 'CHUH0014', 'CHUH0015', 'CHUH0020']
FNS = ['CHUH0020']
for fn in FNS:
    logger.info('Start %s', fn)
    seg_fn = f'../data/suzuki_manual/{fn}.nii.gz'
    outname = out_dir / f"{fn}.mha"
    # if outname.exists() and (outname.stat().st_mtime > Path(seg_fn).stat().st_mtime):
    #     logger.info("skip: %s", seg_fn)
    #     continue

    inputImage = sitk.ReadImage(seg_fn)  #, sitk.sitkFloat32)

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
    #%%

    seg_arr = sitk.GetArrayFromImage(resampled)
    bmin, bmax = boundingbox.bbox(seg_arr)
    bmin = np.clip(bmin - 1, 0, None)
    bmax = np.clip(bmax + 1, None, seg_arr.shape)
    bmid = np.round((bmin + bmax) / 2).astype(int)
    bbox = [bmin, bmid, bmax]

    dist_filter = sitk.SignedMaurerDistanceMapImageFilter()
    dist_image = dist_filter.Execute(resampled)
    # sitk.WriteImage(dist_image, "distance.mhd")
    # %%
    fastMarching = sitk.FastMarchingImageFilter()

    # seedPosition = [86, 59, 200]
    # seedPosition = [43,51,160]
    timeThreshold, stoppingTime = 100, 100

    seedValue = 0
    # trialPoint = (seedPosition[0], seedPosition[1], seedPosition[2], seedValue)
    for x, y, z in itertools.product([0, 1, 2], [0, 1, 2], [0, 1, 2]):
        if x == 1 and y == 1 and z == 1:
            continue
        trialPoint = (int(bbox[x][0]), int(bbox[y][1]), int(bbox[z][2]),
                      seedValue)
        fastMarching.AddTrialPoint(trialPoint)

    # fastMarching.AddTrialPoint((183, 216, 263, seedValue))
    fastMarching.SetNormalizationFactor(200)

    fastMarching.SetStoppingValue(stoppingTime)

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

    sitk.WriteImage(result, str(outname), useCompression=True)

#%%
# sitk.WriteImage(fastMarchingOutput, 'fs_output.mhd')