import os
from pathlib import Path


DOIT_CONFIG = {
    'default_tasks': ['default'],
    'verbosity': 2,
}


ID_LIST_FILENAME = os.environ.get('ID_LIST_FILENAME', 'cfss/filenames.txt')
SEG_DIR = Path(os.environ.get('SEG_DIR', 'data/manual_segmentation'))
OUT_DIR = Path(os.environ.get('OUT_DIR', 'result'))
SRC_DIR = Path(__file__).parent / 'cfss'

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
        yield {'name': data_id, 'actions': [f'python {script} {infn} {outfn}'], 'file_dep': [infn], 'targets': [outfn]}


MESH_OUTDIR = OUT_DIR / 'mesh'


def task_mesh():
    '''
    Create mesh
    '''
    script = SRC_DIR / 'create_mesh.py'
    MESH_OUTDIR.mkdir(exist_ok=True, parents=True)

    for data_id in id_list:
        infn = LEVELSET_OUTDIR / f'{data_id}.mha'
        outfn = MESH_OUTDIR / f'{data_id}.vtp'
        yield {'name': data_id, 'actions': [f'python {script} {infn} {outfn}'], 'file_dep': [infn], 'targets': [outfn]}


REG_OUTDIR = OUT_DIR / 'register'


def task_register():
    '''
    Register meshes
    '''
    script = SRC_DIR / 'pcl_registration.py'
    srcfn = MESH_OUTDIR / f'{id_list[0]}.vtp'
    for data_id in id_list[1:]:
        tgtfn = MESH_OUTDIR / f'{data_id}.vtp'
        outfn = REG_OUTDIR / f'{data_id}.vtp'
        print(f'python {script} {srcfn} {tgtfn} {outfn}')
        yield {
            'name': data_id,
            'actions': [f'python {script} {srcfn} {tgtfn} {outfn}'],
            'file_dep': [srcfn, tgtfn],
            'targets': [outfn],
        }
