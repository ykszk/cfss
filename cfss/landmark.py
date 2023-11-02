# %%
from pathlib import Path
from typing import List, Tuple, Union

from pydantic import BaseModel
from vtkmodules.vtkCommonDataModel import vtkPointLocator, vtkPolyData


class ControlPoint(BaseModel):
    id: str
    label: str
    position: Tuple[float, float, float]


Landmarks = List[ControlPoint]


class Markup(BaseModel):
    type: str
    coordinateUnits: str
    controlPoints: Landmarks
    measurements: List
    display: dict


class SlicerMarkups(BaseModel):
    markups: List[Markup]


def load_landmarks(filename: Union[str, Path]) -> Landmarks:
    markups = SlicerMarkups.parse_file(filename)
    landmarks = markups.markups[0].controlPoints
    return landmarks


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
