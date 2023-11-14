# %%
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Union

import numpy as np
from pydantic import BaseModel
from scipy.spatial.transform import Rotation as R
from vtkmodules.vtkCommonDataModel import vtkPointLocator, vtkPolyData


class ControlPoint(BaseModel):
    id: str
    label: str
    position: Tuple[float, float, float]


Landmarks = List[ControlPoint]
LandmarkDict = Dict[str, ControlPoint]


class Markup(BaseModel):
    type: str
    coordinateUnits: str
    controlPoints: Landmarks
    measurements: List
    display: dict


class SlicerMarkups(BaseModel):
    markups: List[Markup]


def load_landmarks(filename: Union[str, Path]) -> Landmarks:
    with open(filename) as f:
        markups = SlicerMarkups.model_validate_json(f.read())
    landmarks = markups.markups[0].controlPoints
    return landmarks


def to_dict(lms: Landmarks) -> LandmarkDict:
    return {lm.label: lm for lm in lms}


def locate_landmarks(mesh: vtkPolyData, landmarks: Landmarks) -> List[int]:
    '''
    Find closest point of lanrmarks on the mesh.

    return: point ids
    '''
    locator = vtkPointLocator()
    locator.SetDataSet(mesh)
    locator.SetNumberOfPointsPerBucket(1)
    locator.BuildLocator()

    point_ids = [locator.FindClosestPoint(landmark.position) for landmark in landmarks]
    return point_ids


class Camera(BaseModel):
    position: Tuple[float, float, float]
    focal_point: Tuple[float, float, float]
    view_up: Tuple[float, float, float]


class CameraPreset(BaseModel):
    name: str
    camera: Camera


class CameraPresets(BaseModel):
    presets: List[CameraPreset]


def create_camera_preset(landmarks: Landmarks) -> CameraPresets:
    d_lm = {l: np.array(lm.position) for l, lm in to_dict(landmarks).items()}

    focal_point = (d_lm['Lamda'] + d_lm['Subspinale']) / 2
    front_pos = focal_point.copy()  # coordinates are in xyz order
    front_pos[1] = (4 * (d_lm['Subspinale'] - d_lm['Lamda']))[1]
    view_up = d_lm['Bregma'] - focal_point
    view_up = view_up / np.linalg.norm(view_up)

    camera = Camera(position=front_pos, focal_point=focal_point, view_up=view_up)
    preset = CameraPreset(name='front', camera=camera)
    presets = [preset]
    for name, angle in [('left', 90), ('back', 180), ('right', -90)]:
        mag = np.tan(np.deg2rad(angle) / 4)
        r = R.from_mrp(view_up * mag)
        pos = r.apply(front_pos - focal_point) + focal_point
        camera = Camera(position=pos, focal_point=focal_point, view_up=view_up)
        preset = CameraPreset(name=name, camera=camera)
        presets.append(preset)
    return CameraPresets(presets=presets)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Create camera presets.')
    parser.add_argument('input', help='Input landmark filename')
    parser.add_argument('output', help='Output presets json filename')

    args = parser.parse_args()

    landmarks = load_landmarks(args.input)
    presets = create_camera_preset(landmarks)
    with open(args.output, 'w') as f:
        f.write(presets.model_dump_json())
    return 0


if __name__ == '__main__':
    sys.exit(main())
