# noinspection PyUnresolvedReferences
import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkIdTypeArray
from vtkmodules.vtkCommonDataModel import (
    vtkSelection,
    vtkSelectionNode,
    vtkUnstructuredGrid,
)
from vtkmodules.vtkFiltersCore import vtkGlyph3D, vtkTriangleFilter
from vtkmodules.vtkFiltersExtraction import vtkExtractSelection
from vtkmodules.vtkFiltersSources import vtkPlaneSource, vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkCellPicker,
    vtkDataSetMapper,
    vtkHardwarePicker,
    vtkPointPicker,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkSelectVisiblePoints,
)


# Catch mouse events
class MouseInteractorStyle(vtkInteractorStyleTrackballCamera):
    def __init__(self, data):
        self.AddObserver('LeftButtonPressEvent', self.left_button_press_event)
        self.data = data
        self.selected_mapper = vtkDataSetMapper()
        self.selected_actor = vtkActor()
        sphere_source = vtkSphereSource()
        self.source = sphere_source
        self.source.SetPhiResolution(11)
        self.source.SetThetaResolution(11)
        self.source.SetRadius(2)

        # glyph3D = vtkGlyph3D()
        # glyph3D.SetSourceConnection(sphere_source.GetOutputPort())
        # glyph3D.SetInputData(data)
        # glyph3D.Update()

    def left_button_press_event(self, obj, event):
        colors = vtkNamedColors()

        # Get the location of the click (in window coordinates)
        pos = self.GetInteractor().GetEventPosition()
        # orient = obj.GetWorldOrientation()
        # print(orient)

        # picker = vtkCellPicker()
        picker = vtkHardwarePicker()
        picker.SnapToMeshPointOn()
        # picker.UseCellsOn()
        # picker.SetTolerance(0.01)

        # Pick from this location.
        picker.Pick(pos[0], pos[1], 0, self.GetDefaultRenderer())

        world_position = picker.GetPickPosition()
        print(f'Point id is: {picker.GetPointId()}')

        if picker.GetPointId() != -1:
            print(f'Pick position is: ({world_position[0]:.6g}, {world_position[1]:.6g}, {world_position[2]:.6g})')

            ids = vtkIdTypeArray()
            ids.SetNumberOfComponents(1)
            ids.InsertNextValue(picker.GetPointId())

            selection_node = vtkSelectionNode()
            selection_node.SetFieldType(vtkSelectionNode.POINT)
            selection_node.SetContentType(vtkSelectionNode.INDICES)
            selection_node.SetSelectionList(ids)

            selection = vtkSelection()
            selection.AddNode(selection_node)

            extract_selection = vtkExtractSelection()
            extract_selection.SetInputData(0, self.data)
            extract_selection.SetInputData(1, selection)
            extract_selection.Update()

            # In selection
            selected = vtkUnstructuredGrid()
            selected.ShallowCopy(extract_selection.GetOutput())

            glyph3D = vtkGlyph3D()
            glyph3D.SetSourceConnection(self.source.GetOutputPort())
            glyph3D.SetInputData(selected)

            # print(f'Number of points in the selection: {selected.GetNumberOfPoints()}')
            # print(f'Number of cells in the selection : {selected.GetNumberOfCells()}')

            self.selected_mapper.SetInputConnection(glyph3D.GetOutputPort())
            self.selected_actor.SetMapper(self.selected_mapper)
            # self.selected_actor.GetProperty().SetRepresentationToPoints()
            self.selected_actor.GetProperty().SetColor(colors.GetColor3d('Yellow'))

            # self.selected_actor.GetProperty().SetLineWidth(3)
            # self.selected_actor.GetProperty().SetPointSize(10)

            self.GetInteractor().GetRenderWindow().GetRenderers().GetFirstRenderer().AddActor(self.selected_actor)

        # Forward events
        self.OnLeftButtonDown()


from utils import read_mesh


def main(argv):
    colors = vtkNamedColors()

    # plane_source = vtkPlaneSource()
    # plane_source.Update()

    mesh = read_mesh('../result/lm_aligned/CHUH0001.vtk')

    # triangle_filter = vtkTriangleFilter()
    # triangle_filter.SetInputConnection(plane_source.GetOutputPort())
    # triangle_filter.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(mesh)

    actor = vtkActor()
    actor.GetProperty().SetColor(colors.GetColor3d('SeaGreen'))
    # actor.GetProperty().SetRepresentationToWireframe()
    actor.SetMapper(mapper)

    renderer = vtkRenderer()
    ren_win = vtkRenderWindow()
    ren_win.AddRenderer(renderer)
    ren_win.SetWindowName('PointPicking')
    iren = vtkRenderWindowInteractor()
    iren.SetRenderWindow(ren_win)

    renderer.AddActor(actor)
    # renderer.ResetCamera()
    renderer.SetBackground(colors.GetColor3d('PaleTurquoise'))

    # Add the custom style.
    style = MouseInteractorStyle(mesh)
    style.SetDefaultRenderer(renderer)
    iren.SetInteractorStyle(style)

    ren_win.Render()
    iren.Initialize()
    iren.Start()


if __name__ == '__main__':
    import sys

    main(sys.argv)
