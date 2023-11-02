# %%
from pathlib import Path

import cc3d
import tqdm
import utils
from joblib import Parallel, delayed
from logzero import logger
from szkmipy import mhd


# indir = Path('../data/mha/chuh/CHUH0002')
indir = Path('../data/mha')
fns = sorted(indir.glob('**/*_wo_bed.mha'))
# for mha_fn in indir.glob('*_bed.mha'):
#     fid = mha_fn.name.split('_')[0]
#     fcsv_fn = mha_fn.parent / f'{fid}.fcsv'
#     print(mha_fn, fcsv_fn)
#     d = {}
#     rows = []
#     with open(fcsv_fn) as f:
#         for line in f:
#             if line.startswith('#'):
#                 line = line[1:] # remove *
#                 line = line.strip()
#                 key_value = line.split(' = ')
#                 assert len(key_value)==2
#                 d[key_value[0]] = key_value[1]
#             else:
#                 rows.append(line)
#         df = pd.read_csv(StringIO('\n'.join(rows)), header=None, names=d['columns'].split(','))

# %%
import numpy as np
from scipy import ndimage


def segment_bone(mha_fn: str, out_fn: str):
    if Path(out_fn).exists():
        logger.info('Skip: %s', mha_fn)
        return
    vol, h = mhd.read(mha_fn)
    if vol.dtype != np.int16:
        logger.info('Skip (not int16 image): %s', mha_fn)
        return

    logger.info('Process: %s', mha_fn)

    try:
        body, dilated_body = utils.segment_body(vol)
    except Exception as e:
        logger.error('Failed to segment body from %s: %s', mha_fn, e)
        return

    iterations = 3
    eroded = ndimage.binary_erosion(body, structure=np.ones((3, 3, 3)), iterations=iterations)
    h['CompressedData'] = True
    thresh = 400
    bone = vol > thresh
    bone[eroded == 0] = 0

    filled = ndimage.binary_fill_holes(bone, structure=np.ones((3, 3, 3)))

    largest = cc3d.largest_k(filled, k=1, connectivity=6) > 0

    VC_THRESH = 800

    st2d = ndimage.generate_binary_structure(2, 1)

    def fill2d(s):
        filled = ndimage.binary_fill_holes(s, structure=st2d)
        holes = np.logical_xor(filled, s)
        labels_out = cc3d.connected_components(holes)
        stats = cc3d.statistics(labels_out)
        for i, vc in enumerate(stats['voxel_counts'][1:], 1):
            if vc > VC_THRESH:
                filled[labels_out == i] = 0
        return filled

    f2d = [fill2d(s) for s in largest]
    f2d = np.stack(f2d).astype(np.uint8)
    st = ndimage.generate_binary_structure(3, 1)
    filled = ndimage.binary_fill_holes(f2d, structure=st)

    mhd.write(out_fn, filled, h)


args = [(str(fn), str(fn.parent / '{}_auto_skull.mha'.format(fn.stem.replace('_wo_bed', '')))) for fn in fns]


logger.info('start')
Parallel(n_jobs=4)(delayed(segment_bone)(*arg) for arg in tqdm.tqdm(args))
logger.info('done')
