# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from utils import read_mesh
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkCommand, vtkIdTypeArray
from vtkmodules.vtkCommonDataModel import (
    vtkSelection,
    vtkSelectionNode,
    vtkUnstructuredGrid,
)
from vtkmodules.vtkFiltersCore import vtkGlyph3D
from vtkmodules.vtkFiltersExtraction import vtkExtractSelection
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkInteractionWidgets import vtkHoverWidget
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkHardwarePicker,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)


# https://github.com/pyvista/pyvista/discussions/4781


class HoverCallback:
    def __init__(self, data, iren: vtkRenderWindowInteractor):
        self.iren = iren
        self.data = data
        self.selected_mapper = vtkDataSetMapper()
        self.selected_actor = vtkActor()
        sphere_source = vtkSphereSource()
        self.source = sphere_source
        self.source.SetPhiResolution(11)
        self.source.SetThetaResolution(11)
        self.source.SetRadius(2)

        ids = vtkIdTypeArray()
        ids.SetNumberOfComponents(1)
        ids.SetNumberOfValues(1)
        self.ids = ids

        selection_node = vtkSelectionNode()
        selection_node.SetFieldType(vtkSelectionNode.POINT)
        selection_node.SetContentType(vtkSelectionNode.INDICES)
        selection_node.SetSelectionList(ids)

        selection = vtkSelection()
        selection.AddNode(selection_node)

        extract_selection = vtkExtractSelection()
        extract_selection.SetInputData(0, self.data)
        extract_selection.SetInputData(1, selection)
        self.extract_selection = extract_selection

        # In selection
        selected = vtkUnstructuredGrid()
        selected.ShallowCopy(extract_selection.GetOutput())
        self.selected = selected

        glyph3D = vtkGlyph3D()
        glyph3D.SetSourceConnection(self.source.GetOutputPort())
        glyph3D.SetInputData(selected)
        self.glyph3D = glyph3D

        colors = vtkNamedColors()

        self.selected_mapper.SetInputConnection(glyph3D.GetOutputPort())
        self.selected_actor.SetMapper(self.selected_mapper)
        self.selected_actor.GetProperty().SetColor(colors.GetColor3d('Red'))

        self.iren.GetRenderWindow().GetRenderers().GetFirstRenderer().AddActor(self.selected_actor)

        picker = vtkHardwarePicker()
        picker.SnapToMeshPointOn()
        picker.SetPixelTolerance(10)
        self.picker = picker

    def __call__(self, _widget, event_name):
        pos = self.iren.GetEventPosition()

        picker = self.picker
        picker.Pick(pos[0], pos[1], 0, self.iren.GetRenderWindow().GetRenderers().GetFirstRenderer())

        if picker.GetPointId() != -1:  # and not picker.GetNormalFlipped():
            # print(picker.GetPointId(), end=' ', flush=True)

            self.ids.SetValue(0, picker.GetPointId())
            self.ids.Modified()
            self.extract_selection.Update()

            # In selection
            self.selected.ShallowCopy(self.extract_selection.GetOutput())
            # self.selected.Modified()

            self.iren.GetRenderWindow().Render()


def main():
    colors = vtkNamedColors()

    mesh = read_mesh('../result/ssm/ssm.vtk')

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(mesh)

    actor = vtkActor()
    actor.GetProperty().SetColor(colors.GetColor3d('lightyellow'))
    actor.GetProperty().SetRepresentationToWireframe()
    actor.SetMapper(mapper)

    renderer = vtkRenderer()
    ren_win = vtkRenderWindow()
    ren_win.AddRenderer(renderer)
    ren_win.SetWindowName('PointPicking')
    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    renderer.AddActor(actor)
    renderer.SetBackground(colors.GetColor3d('AliceBlue'))

    callback = HoverCallback(mesh, iren)

    style = vtkInteractorStyleTrackballCamera()
    iren.SetInteractorStyle(style)

    hw = vtkHoverWidget()
    hw.SetInteractor(iren)
    hw.SetTimerDuration(5)  # Time (ms) required to trigger a hover event
    hw.AddObserver(vtkCommand.TimerEvent, callback)  # Start of hover
    hw.AddObserver(vtkCommand.EndInteractionEvent, callback)  # Hover ended (mouse moved)

    ren_win.Render()
    hw.On()
    iren.Initialize()
    iren.Start()


if __name__ == '__main__':
    main()
