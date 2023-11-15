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
FINAL_MESH_EXT = os.environ.get('FINAL_MESH_EXT', '.vtp')  # file extension for mesh that has no further processing
N_MESH_POINTS = int(os.environ.get('N_MESH_POINTS', '80000'))

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

    for data_id in id_list:
        infn = LEVELSET_OUTDIR / f'{data_id}.mha'
        outfn = MESH_OUTDIR / f'{data_id}{MESH_EXT}'
        yield {
            'name': f'{data_id}',
            'actions': [f'python {script} {infn} {outfn} --points {N_MESH_POINTS}'],
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
    targets = [str(ALIGN_LM_OUTDIR / f'{data_id}{FINAL_MESH_EXT}') for data_id in id_list]  # mesh format is vtp
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
from cfss import create_average, irtk_reg


def task_register():
    '''
    Register meshes
    '''
    # if os.name != 'nt':
    #     print('Run this task in windows!')
    #     return
    BIN_DIR = TOOL_DIR / 'bin'
    N_REG_ITER = 3
    N_ITER = 1000  # Number of 3D registration iterations
    FINAL_DS = 16  # Control point spacing
    FINAL_TOLERANCE = 0.0001  # Value for espilon
    REG_OUTDIR.mkdir(exist_ok=True, parents=True)
    ref_fn = (ALIGN_OUTDIR / f'{REF_ID}{MESH_EXT}').absolute()
    file_dep = []  # TODO: file_dep[bb alignemnt]
    for i in range(N_REG_ITER):
        if i == (N_REG_ITER - 1):
            outdir = REG_OUTDIR
        else:
            outdir = REG_OUTDIR / f'iter{i}'
        outdir.mkdir(parents=True, exist_ok=True)
        all_target = []
        tol = FINAL_TOLERANCE * (2 ** (N_REG_ITER - i - 1))
        ds = FINAL_DS * (2 ** (N_REG_ITER - i - 1))
        for data_id in id_list:
            logdir = outdir / 'log' / data_id
            logdir.mkdir(parents=True, exist_ok=True)
            mesh = ALIGN_OUTDIR / f'{data_id}{MESH_EXT}'
            output = outdir / f'{data_id}{MESH_EXT}'
            all_target.append(output)
            args = (BIN_DIR, ref_fn, mesh, output, logdir, tol, N_ITER, ds)
            yield {
                'name': f'{data_id}-iter{i}',
                'actions': [(irtk_reg.register, args)],
                'file_dep': file_dep,
                'targets': [output],
            }
        ref_fn = outdir / 'average_surface.vtk'
        args = (all_target, ref_fn)
        yield {
            'name': f'average-iter{i}',
            'actions': [(create_average.create, args)],
            'file_dep': all_target,
            'targets': [ref_fn],
        }
        file_dep = [ref_fn]


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


PRESET_FILENAME = OUT_DIR / 'camera_presets.json'


def task_presets():
    '''
    Create camera presets
    '''
    script = SRC_DIR / 'landmark.py'
    lmfn = LANDMARK_DIR / f'{REF_ID}.mrk.json'
    return {'actions': [f'python {script} {lmfn} {PRESET_FILENAME}'], 'targets': [PRESET_FILENAME], 'file_dep': [lmfn]}


def task_browse():
    '''
    Open cfdb browser
    '''
    script = SRC_DIR / 'shape_stats.py'
    return {
        'actions': [f'python {script} -i {ALIGN_LM_OUTDIR} --cameras {PRESET_FILENAME}'],
        'file_dep': [PRESET_FILENAME],
        'uptodate': [False],
    }


def task_dcm2mha():
    '''
    Convert zipped dicom files to mha files
    '''
    script = SRC_DIR / 'zip2mha.py'
    dicom_dir = 'data/dicom'
    mha_dir = 'data/mha'
    return {
        'actions': [f'python {script} {dicom_dir} {mha_dir}'],
    }


# def task_remove_bed():
#     '''
#     Remove bed from CT images (mha)
#     '''
#     script = SRC_DIR / 'remove_bed.py'
#     return {
#         'actions': [f'python {script}'],
#     }


# def task_segment_bone():
#     '''
#     Segment bone
#     '''
#     script = SRC_DIR / 'segment_bone.py'
#     return {
#         'actions': [f'python {script}'],
#     }
