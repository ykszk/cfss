# %%
from pathlib import Path
import sys
import argparse
import logzero
import utils
from logzero import logger
from tqdm import tqdm



def main():
    parser = argparse.ArgumentParser(
        description='Remove bed')
    parser.add_argument('input', help='Input directory')
    args = parser.parse_args()


    indir = Path(args.input)
    fns = sorted(indir.glob('**/*.mha'))
    fns = [fn for fn in fns if 'wo_bed' not in fn.name]
    print(len(fns), 'files')


    def do(fn):
        utils.logger.setLevel(logzero.INFO)
        output = fn.with_name(fn.stem + '_wo_bed.mha')
        if output.exists():
            logger.info('Skip: %s', fn)
            return
        logger.info('Process: %s', fn)
        try:
            utils.remove_bed(fn, output)
        except Exception as e:
            print(fn)
            print(e)


    from joblib import Parallel, delayed


    Parallel(n_jobs=8)(delayed(do)(fn) for fn in tqdm(fns))



if __name__ == '__main__':
    sys.exit(main())