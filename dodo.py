import os
from pathlib import Path

from cfss import utils


DOIT_CONFIG = {
    # 'default_tasks': ['default'],
    'verbosity': 2,
}

ROOT_DIR = Path(__file__).parent
SRC_DIR = ROOT_DIR / 'cfss'
TOOL_DIR = ROOT_DIR / 'tools'


ID_LIST_FILENAME = os.environ.get('ID_LIST_FILENAME', 'cfss/filenames.txt')
SEG_DIR = Path(os.environ.get('SEG_DIR', 'data/manual_segmentation'))
LANDMARK_DIR = Path(os.environ.get('LANDMARK_DIR', 'data/landmarks'))
OUT_DIR = Path(os.environ.get('OUT_DIR', 'result'))

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
ALIGN_LM_OUTDIR = OUT_DIR / 'lm_aligned'


def task_align_bb():
    '''
    Align bounding boxes (middle of the bb top) of meshes
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


def task_align_landmarks():
    '''
    Align landmarks on meshes
    '''
    script = SRC_DIR / 'align_landmarks.py'
    reffn = REG_OUTDIR / f'{REF_ID}{MESH_EXT}'
    lmfn = LANDMARK_DIR / f'{REF_ID}.mrk.json'
    ALIGN_LM_OUTDIR.mkdir(exist_ok=True, parents=True)
    moving_names = [
        str(REG_OUTDIR / f'{data_id}{MESH_EXT}') for data_id in id_list
    ]  # use id_list instead of target_list to copy reference data
    targets = [str(ALIGN_LM_OUTDIR / f'{data_id}{MESH_EXT}') for data_id in id_list]
    for moving, target in zip(moving_names, targets):
        yield {
            'name': Path(moving).stem,
            'actions': [f'python {script} {reffn} {lmfn} {moving} {target}'],
            # 'file_dep': [moving],
            'targets': [target],
            'clean': True,
        }


REG_OUTDIR = OUT_DIR / 'register'


# def task_register():
#     '''
#     Register meshes
#     '''
#     script = SRC_DIR / 'pcl_registration.py'
#     srcfn = MESH_OUTDIR / f'{REF_ID}{MESH_EXT}'
#     REG_OUTDIR.mkdir(exist_ok=True, parents=True)
#     for data_id in target_list:
#         tgtfn = FINE_MESH_OUTDIR / f'{data_id}{MESH_EXT}'
#         outfn = REG_OUTDIR / f'{data_id}{MESH_EXT}'
#         yield {
#             'name': data_id,
#             'actions': [f'python {script} {srcfn} {tgtfn} {outfn}'],
#             'file_dep': [srcfn, tgtfn],
#             'targets': [outfn],
#             'clean': True,
#         }


def task_register():
    '''
    Register meshes
    '''
    # if os.name != 'nt':
    #     print('Run this task in windows!')
    #     return
    bat = TOOL_DIR / 'SSM/PairwiseCorrespondence/SurfaceBasedPairwiseCorrespondence.bat'
    N_PTS = 10000  # irrelevant?
    FINAL_TOLERANCE = 0.0001
    MID_TOLERANCE = 0.01
    REG_OUTDIR.mkdir(exist_ok=True, parents=True)
    pathlist = REG_OUTDIR / 'idpathlist.txt'
    ref_fn = (ALIGN_OUTDIR / f'{REF_ID}{MESH_EXT}').absolute()
    mesh_fns = [(ALIGN_OUTDIR / f'{data_id}{MESH_EXT}').absolute() for data_id in id_list]
    with open(pathlist, 'w') as f:
        for fn in mesh_fns:
            f.write(f'{fn.stem} {fn}\n')
    targets = [str(REG_OUTDIR / f'{data_id}{MESH_EXT}') for data_id in id_list]
    # TODO: No file_dep for now

    return {
        'actions': [f'{bat} {pathlist} {N_PTS} {ref_fn} {REG_OUTDIR} {FINAL_TOLERANCE} {MID_TOLERANCE}'],
        'targets': targets,
    }


SSM_OUTDIR = OUT_DIR / 'ssm'


def task_ssm():
    '''
    Create ssm
    '''
    # if os.name != 'nt':
    #     print('Run this task in windows!')
    #     return
    bin = TOOL_DIR / 'SSM/BuildHierarchicalSSM.exe'
    SSM_OUTDIR.mkdir(exist_ok=True, parents=True)
    pathlist = SSM_OUTDIR / 'surfacelist.txt'
    mesh_fns = [(ALIGN_LM_OUTDIR / f'{data_id}{MESH_EXT}').absolute() for data_id in id_list]
    outfn = SSM_OUTDIR / 'ssm.xml'
    with open(pathlist, 'w') as f:
        for fn in mesh_fns:
            f.write(f'{fn}\n')
    # TODO: No file_dep for now

    return {
        'actions': [f'{bin} {pathlist} {outfn}'],
        # 'targets': targets,
        # 'file_dep': [align_lm_results]
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


def task_dcm2mha():
    '''
    Convert zipped dicom files to mha files
    '''
    script = SRC_DIR / 'zip2mha.py'
    # TODO: implement
    meshfn = MESH_OUTDIR / f'{REF_ID}{MESH_EXT}'
    lmfn = LANDMARK_DIR / f'{REF_ID}.mrk.json'
    return {
        'actions': [f'python {script} {meshfn} {lmfn}'],
        # 'file_dep': [meshfn],
    }


def task_remove_bed():
    '''
    Remove bed from CT images (mha)
    '''
    script = SRC_DIR / 'remove_bed.py'
    # TODO: implement
    meshfn = MESH_OUTDIR / f'{REF_ID}{MESH_EXT}'
    lmfn = LANDMARK_DIR / f'{REF_ID}.mrk.json'
    return {
        'actions': [f'python {script} {meshfn} {lmfn}'],
        # 'file_dep': [meshfn],
    }


def task_segment_bone():
    '''
    Remove bed from CT images (mha)
    '''
    script = SRC_DIR / 'segment_bone.py'
    # TODO: implement
    meshfn = MESH_OUTDIR / f'{REF_ID}{MESH_EXT}'
    lmfn = LANDMARK_DIR / f'{REF_ID}.mrk.json'
    return {
        'actions': [f'python {script} {meshfn} {lmfn}'],
        # 'file_dep': [meshfn],
    }
