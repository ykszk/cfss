# noinspection PyUnresolvedReferences
import vtkmodules.vtkInteractionStyle

# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from landmark import load_landmarks, locate_landmarks
from utils import read_mesh, write_mesh
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkPoints, vtkStringArray
from vtkmodules.vtkCommonDataModel import vtkPointLocator, vtkPolyData
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkActor2D,
    vtkDataSetMapper,
    vtkGlyph3DMapper,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkTextMapper,
    vtkTextProperty,
)
from vtkmodules.vtkRenderingLabel import vtkLabeledDataMapper


# https://examples.vtk.org/site/Python/GeometricObjects/IsoparametricCellsDemo/
# https://examples.vtk.org/site/Cxx/Visualization/LabelContours/


def main():
    mesh = read_mesh('../result/mesh/CHUH0001.vtp')
    landmarks = load_landmarks('../data/landmarks/CHUH0001.mrk.json')
    landmark_ids = locate_landmarks(mesh, landmarks)
    vtk_points = vtkPoints()
    vtk_points.Resize(len(landmark_ids))
    for lid in landmark_ids:
        vtk_points.InsertNextPoint(mesh.GetPoint(lid))
    landmark_poly = vtkPolyData()
    landmark_poly.SetPoints(vtk_points)

    colors = vtkNamedColors()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(mesh)

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(colors.GetColor3d('lightyellow'))
    actor.GetProperty().SetOpacity(0.5)
    # actor.GetProperty().SetRepresentationToWireframe()

    # Create a rendering window and renderer
    ren = vtkRenderer()
    renWin = vtkRenderWindow()
    renWin.AddRenderer(ren)
    renWin.SetWindowName('Craniofacial landmarks')

    # Create a renderwindowinteractor
    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(renWin)

    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    # Assign actor to the renderer
    ren.AddActor(actor)

    # Create one sphere for all
    sphere = vtkSphereSource()
    sphere.SetPhiResolution(11)
    sphere.SetThetaResolution(11)
    sphere.SetRadius(1)

    pointMapper = vtkGlyph3DMapper()
    pointMapper.SetInputData(landmark_poly)
    pointMapper.SetSourceConnection(sphere.GetOutputPort())
    pointMapper.ScalingOff()
    pointMapper.ScalarVisibilityOff()

    pointActor = vtkActor()
    pointActor.SetMapper(pointMapper)
    pointActor.GetProperty().SetDiffuseColor(colors.GetColor3d('Red'))
    pointActor.GetProperty().SetSpecular(0.6)
    pointActor.GetProperty().SetSpecularColor(1.0, 1.0, 1.0)
    pointActor.GetProperty().SetSpecularPower(100)
    ren.AddViewProp(pointActor)

    # Texts
    labels = vtkStringArray()
    labels.SetName('Names')
    for lm in landmarks:
        labels.InsertNextValue(lm.label)

    landmark_poly.GetPointData().AddArray(labels)

    labelMapper = vtkLabeledDataMapper()
    labelMapper.SetInputData(landmark_poly)
    labelMapper.SetFieldDataArray(0)
    labelMapper.SetLabelModeToLabelFieldData()
    labelActor = vtkActor2D()
    labelActor.SetMapper(labelMapper)
    ren.AddViewProp(labelActor)

    # Enable user interface interactor
    iren.Initialize()
    renWin.Render()

    ren.SetBackground(colors.GetColor3d('AliceBlue'))
    # ren.GetActiveCamera().SetPosition(-0.5, -100, -20.0)
    # ren.GetActiveCamera().SetViewUp(0.0, 0.0, 1.0)
    renWin.Render()
    iren.Start()


if __name__ == "__main__":
    main()
