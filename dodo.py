import os
from pathlib import Path

from cfss import utils


DOIT_CONFIG = {
    # 'default_tasks': ['default'],
    'verbosity': 2,
}


ID_LIST_FILENAME = os.environ.get('ID_LIST_FILENAME', 'cfss/filenames.txt')
SEG_DIR = Path(os.environ.get('SEG_DIR', 'data/manual_segmentation'))
LANDMARK_DIR = Path(os.environ.get('LANDMARK_DIR', 'data/landmarks'))
OUT_DIR = Path(os.environ.get('OUT_DIR', 'result'))
SRC_DIR = Path(__file__).parent / 'cfss'

MESH_EXT = os.environ.get('MESH_EXT', '.vtk')

REF_ID = os.environ.get('REF_ID', '')  # optional

with open(ID_LIST_FILENAME) as f:
    id_list = [l.rstrip() for l in f.readlines()]

if REF_ID == '':
    REF_ID = id_list[0]
    target_list = id_list[1:]
else:  # reference id is specified
    target_list = id_list.copy()
    target_list.remove(REF_ID)


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
    # for outdir, reduction in [(MESH_OUTDIR, 0.99), (FINE_MESH_OUTDIR, 0.98)]:
    for outdir, reduction in [(MESH_OUTDIR, 0.90)]:
        outdir.mkdir(exist_ok=True, parents=True)

        for data_id in id_list:
            infn = LEVELSET_OUTDIR / f'{data_id}.mha'
            outfn = outdir / f'{data_id}{MESH_EXT}'
            yield {
                'name': f'{data_id}-{outdir.name}',
                'actions': [f'python {script} {infn} {outfn} --reduction {reduction}'],
                'file_dep': [infn],
                'targets': [outfn],
                'clean': True,
            }


ALIGN_OUTDIR = OUT_DIR / 'aligned'


def task_align():
    '''
    Align meshes
    '''
    script = SRC_DIR / 'align_meshes.py'
    reffn = MESH_OUTDIR / f'{REF_ID}{MESH_EXT}'
    ALIGN_OUTDIR.mkdir(exist_ok=True, parents=True)
    moving_names = [
        str(MESH_OUTDIR / f'{data_id}{MESH_EXT}') for data_id in id_list
    ]  # use id_list instead of target_list to copy reference data
    targets = [str(ALIGN_OUTDIR / f'{data_id}{MESH_EXT}') for data_id in id_list]
    return {
        'actions': [f'python {script} {reffn} {ALIGN_OUTDIR} {" ".join(moving_names)}'],
        'file_dep': moving_names,
        'targets': targets,
        'clean': True,
    }


REG_OUTDIR = OUT_DIR / 'register'


def task_register():
    '''
    Register meshes
    '''
    script = SRC_DIR / 'pcl_registration.py'
    srcfn = MESH_OUTDIR / f'{REF_ID}{MESH_EXT}'
    REG_OUTDIR.mkdir(exist_ok=True, parents=True)
    for data_id in target_list:
        tgtfn = FINE_MESH_OUTDIR / f'{data_id}{MESH_EXT}'
        outfn = REG_OUTDIR / f'{data_id}{MESH_EXT}'
        yield {
            'name': data_id,
            'actions': [f'python {script} {srcfn} {tgtfn} {outfn}'],
            'file_dep': [srcfn, tgtfn],
            'targets': [outfn],
            'clean': True,
        }


def task_show_landmarks():
    '''
    Show landmark points. Landmark data (.mrk.json craeted using 3d slicer) is required for the reference mesh.
    '''
    script = SRC_DIR / 'qt_show_landmarks.py'
    meshfn = MESH_OUTDIR / f'{REF_ID}{MESH_EXT}'
    lmfn = LANDMARK_DIR / f'{REF_ID}.mrk.json'
    return {
        'actions': [f'python {script} {meshfn} {lmfn}'],
        # 'file_dep': [meshfn],
    }
