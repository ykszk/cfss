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
3. Create average shape

Step 1 and 2 can be omitted if you already have segmented skulls.

## Step 1
```shell
doit segment_bone
```

Internals:
- Convert zipped dicoms to mha format
- Remove bed from the image
- Segment skulls

## Step 2
Manually correct segmentation errros in `data/*/*/1_auto_skull.mha` files.

### Note
- Close [foramen magnum](https://en.wikipedia.org/wiki/Foramen_magnum) to fill up cranial cavity in the subsequent process
- Remove:
    - vertebrae
    - metal artifacts (around teeth)
    - (maybe [temporal styloid process](https://en.wikipedia.org/wiki/Temporal_styloid_process))
        - I unintentionally did.

## Step 3
```shell
doit align_bb
```

Internals:
- Apply levelset segmentation to segment and create mesh files from levelset segmentations.
- Align meshes so that the mid points of bounding boxes of align. The alignment is only done by translation.

```shell
doit register
```

Internals:
- Perform mesh-to-mesh non-rigid registration

```shell
doit align_landmarks
```

Internals:
- Apply similarity transforms.

```shell
doit ssm
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
- Use [MmgTools](https://github.com/MmgTools/mmg) for mesh creation/decimation.
- Improve levelset segmentation. Currently, segmented area is somewhat bloated.
- Make `doit register` portable. Currently, it's relying on windows-only binaries.