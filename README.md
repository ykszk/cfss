# cfss
Craniofacial shape statistics

# Setup
1. Setup python
2. Install dependencies
```shell
pip install -r requirements.txt
```

# Execute
Three steps:

1. Run automated segmentation process to create initial segmentation of skulls
2. Manually refine segmentations
3. Process mesh data and calculate craniofacial shape statistics

Step 1 and 2 can be omitted if you already have segmented skulls.

## Step 1: Bone segmentation
Goal: Create segmentation files (`.nii.gz`) of bone in `data/manual_segmentation`

## Step 1.1: Initial automated segmentation
```shell
doit segment_bone
```

Internals:
- Convert zipped dicoms to mha format
- Remove bed from the image
- Segment skulls

## Step 1.2: Manual refinement of segmentation
Manually correct segmentation errros in `data/*/*/1_auto_skull.mha` files.

### Note
- Close [foramen magnum](https://en.wikipedia.org/wiki/Foramen_magnum) to fill up cranial cavity in the subsequent process
- Remove:
    - vertebrae
    - metal artifacts (around teeth)
    - (maybe [temporal styloid process](https://en.wikipedia.org/wiki/Temporal_styloid_process))
        - I unintentionally did.

## Step 2: Process mesh data
Goal: Create `.vtp` files in `result/lm_aligned`

```shell
doit align_bb
```
- Input: `.nii.gz` files in `DATA/manual_segmentation`
- Intermediate output
  - levelset: `.mha` files in `RESULT/fast_marching`
  - mesh: `.vtk` files in `RESULT/mesh`
- Output: `.vtk` files in `RESULT/aligned`

Internals:
- Apply levelset segmentation to fillup empty spaces in the skulls (including cranial cavity) and create mesh files.
- Align meshes so that the mid points of bounding boxes of align. The alignment is only done by translation.

```shell
doit register
```

- Input: `.vtk` files in `RESULT/aligned`
- Output: `.vtk` files in `RESULT/register`

Internals:
- Perform mesh-to-mesh non-rigid registration

```shell
doit align_landmarks
```


- Input: `.vtk` files in `RESULT/register`
- Output: `.vtp` files in `RESULT/lm_aligned`


Internals:
- Apply rigid transformation to align pre-defined landmarks.

## Step 3: Browse data
```shell
doit browse
```

### ⚠️ Note

`file_dep`s are not well constructed (yet) due to tooling issues in this step.
This is why this step is made of several tasks instead of a one-shot task (e.g. `doit final_step`).

# Development
`vtk==9.2.6` is required to save in legacy vtk polydata format.

## 🚸 Info
[pydoit](https://pydoit.org/) is used as a task runner.
```shell
pip install doit
```

Try
```shell
doit list
```
to list available tasks and checkout `dodo.py` for any details.

## Data layout
- `cfss`: scripts
- `data`
    - `dicom`: zipped dicom files
    - `manual_segmentation`: skull segmentation
    - `landmarks`: landmark point file (.mrk.json) created using 3D Slicer
- `result`: results
- `tools`: external tools (for registration and ssm)


# TODO
- Improve levelset segmentation. Currently, segmented area is somewhat bloated.
- Make `doit register` portable. Currently, it's relying on windows-only binaries.
  - namely, `sareg`, `snreg` and `stransformation` from [IRTK](https://github.com/BioMedIA/IRTK)