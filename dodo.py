import os
from pathlib import Path

from cfss import utils


DOIT_CONFIG = {
    # 'default_tasks': ['default'],
    'verbosity': 2,
}


ID_LIST_FILENAME = os.environ.get('ID_LIST_FILENAME', 'cfss/filenames.txt')
SEG_DIR = Path(os.environ.get('SEG_DIR', 'data/manual_segmentation'))
OUT_DIR = Path(os.environ.get('OUT_DIR', 'result'))
SRC_DIR = Path(__file__).parent / 'cfss'

REF_ID = os.environ.get('REF_ID', '')  # optional


with open(ID_LIST_FILENAME) as f:
    id_list = [l.rstrip() for l in f.readlines()]


def task_default():
    msg = 'Use command `list` to print the list of available commands'
    return {'actions': ['echo ' + msg]}


def task_ids():
    '''
    Print IDs
    '''
    return {'actions': [f"echo '\n'.join(id_list)"]}


LEVELSET_OUTDIR = OUT_DIR / 'fast_marching'


def task_levelset():
    '''
    Perform levelset segmentation
    '''
    script = SRC_DIR / 'fast_marching.py'
    LEVELSET_OUTDIR.mkdir(exist_ok=True, parents=True)
    for data_id in id_list:
        infn = SEG_DIR / f'{data_id}.nii.gz'
        outfn = LEVELSET_OUTDIR / f'{data_id}.mha'
        yield {
            'name': data_id,
            'actions': [f'python {script} {infn} {outfn}'],
            'file_dep': [infn],
            'targets': [outfn],
            'clean': True,
        }


MESH_OUTDIR = OUT_DIR / 'mesh'
FINE_MESH_OUTDIR = OUT_DIR / 'mesh_fine'


def task_mesh():
    '''
    Create mesh
    '''
    script = SRC_DIR / 'create_mesh.py'
    for outdir, reduction in [(MESH_OUTDIR, 0.99), (FINE_MESH_OUTDIR, 0.95)]:
        outdir.mkdir(exist_ok=True, parents=True)

        for data_id in id_list:
            infn = LEVELSET_OUTDIR / f'{data_id}.mha'
            outfn = outdir / f'{data_id}.vtp'
            yield {
                'name': f'{data_id}-{outdir.name}',
                'actions': [f'python {script} {infn} {outfn} --reduction {reduction}'],
                'file_dep': [infn],
                'targets': [outfn],
                'clean': True,
            }


REG_OUTDIR = OUT_DIR / 'register'


def task_register():
    '''
    Register meshes
    '''
    script = SRC_DIR / 'pcl_registration.py'
    if REF_ID == '':
        srcfn = MESH_OUTDIR / f'{id_list[0]}.vtp'
        target_list = id_list[1:]
    else:  # reference id is specified
        srcfn = MESH_OUTDIR / f'{REF_ID}.vtp'
        target_list = id_list.copy()
        target_list.remove(REF_ID)
    REG_OUTDIR.mkdir(exist_ok=True, parents=True)
    for data_id in target_list:
        tgtfn = FINE_MESH_OUTDIR / f'{data_id}.vtp'
        outfn = REG_OUTDIR / f'{data_id}.vtp'
        yield {
            'name': data_id,
            'actions': [f'python {script} {srcfn} {tgtfn} {outfn}'],
            'file_dep': [srcfn, tgtfn],
            'targets': [outfn],
            'clean': True,
        }


# def task_delete():
#     '''
#     Cleanup artifacts
#     '''
#     ds = [LEVELSET_OUTDIR, MESH_OUTDIR, REG_OUTDIR]
#     return {'actions':[(utils.del_dirs, [ds])],
#             'params':[{'name':'exec',
#                        'long':'exec',
#                        'type': bool,
#                        'default': False}],
#             }
