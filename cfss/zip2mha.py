import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import tqdm
from logzero import logger
from utils import find_binary

def main():
    parser = argparse.ArgumentParser(description='Convert (zipped) dicom into mha files')
    parser.add_argument('indir', help='Input directory:', metavar='<indir>')
    parser.add_argument('outdir', help='Output directory:', metavar='<outdir>')
    parser.add_argument(
        '--bin_dir',
        help='Directory containing binary executables'
    )


    args = parser.parse_args()

    script_dir = Path(__file__).parent
    # logger.setLevel('DEBUG')
    BIN = 'dcm2itk'
    if args.bin_dir:
        bin_dir = args.bin_dir
    else:
        bin_dir = '/bin'

    BIN = find_binary(bin_dir, 'dcm2itk')


    root = Path(args.indir)
    outdir = Path(args.outdir)
    dirs = sorted([fn for fn in root.glob('*') if fn.is_dir()])
    logger.debug(dirs)
    for indir in dirs:
        hosp_name = indir.name
        (outdir / indir.name).mkdir(parents=True, exist_ok=True)
        all_args = []
        logger.info(str(indir))
        for pid_dir in sorted(indir.glob('*')):
            pid = pid_dir.name
            for i, fn in enumerate(sorted(pid_dir.glob('*.zip'))):
                (outdir / hosp_name / pid).mkdir(parents=True, exist_ok=True)
                outfn = outdir / hosp_name / pid / '{}.mha'.format(i + 1)
                if outfn.exists():
                    logger.info('Skip: %s', fn)
                    continue
                args = [BIN, fn, outfn]
                args = [str(e) for e in args]
                all_args.append(args)
                src = fn.with_suffix('.json')
                dst = outfn.with_suffix('.json')
                try:
                    shutil.copyfile(src, dst)
                except Exception as e:
                    print(e)
                # print(args)
        from joblib import Parallel, delayed

        Parallel(n_jobs=7)(delayed(subprocess.check_call)(arg) for arg in tqdm.tqdm(all_args))
        # break
        # subprocess.check_call(args)


if __name__ == '__main__':
    sys.exit(main())
