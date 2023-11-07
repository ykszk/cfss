import argparse
import sys
from pathlib import Path

import numpy as np
import PyQt5
import vtk

# import vtkmodules.vtkRenderingOpenGL2
from landmark import load_landmarks, locate_landmarks
from logzero import logger
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget
from ssm import PCAStats
from utils import read_mesh, write_mesh

# from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkCommand, vtkIdTypeArray, vtkPoints
from vtkmodules.vtkCommonDataModel import (
    vtkPolyData,
    vtkSelection,
    vtkSelectionNode,
    vtkUnstructuredGrid,
)
from vtkmodules.vtkFiltersCore import vtkGlyph3D
from vtkmodules.vtkFiltersExtraction import vtkExtractSelection
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
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
        self.pids = [0, 0]
        ids = vtkIdTypeArray()
        ids.SetNumberOfComponents(1)
        ids.SetNumberOfValues(2)
        self.ids = ids
        self.index = None

        self.scalar = numpy_to_vtk(np.array([[0], [1]]).astype(np.float32))

    def set_index(self, index: int):
        self.index = index

    def left_button_press_event(self, obj, event):
        if self.index is None:
            self.OnLeftButtonDown()
            return
        colors = vtkNamedColors()

        # Get the location of the click (in window coordinates)
        pos = self.GetInteractor().GetEventPosition()

        # picker = vtkCellPicker()
        picker = vtkHardwarePicker()
        picker.SnapToMeshPointOn()
        picker.SetPixelTolerance(10)
        # picker.UseCellsOn()
        # picker.SetTolerance(0.01)

        # Pick from this location.
        picker.Pick(pos[0], pos[1], 0, self.GetDefaultRenderer())
        pid = picker.GetPointId()
        if pid != -1:
            logger.info(f'Point for {self.index}: {pid}')
            # print(f'Pick position is: ({world_position[0]:.6g}, {world_position[1]:.6g}, {world_position[2]:.6g})')

            self.pids[self.index] = pid
            self.ids.SetValue(0, self.pids[0])
            self.ids.SetValue(1, self.pids[1])
            self.index = None

            selection_node = vtkSelectionNode()
            selection_node.SetFieldType(vtkSelectionNode.POINT)
            selection_node.SetContentType(vtkSelectionNode.INDICES)
            selection_node.SetSelectionList(self.ids)

            selection = vtkSelection()
            selection.AddNode(selection_node)

            extract_selection = vtkExtractSelection()
            extract_selection.SetInputData(0, self.data)
            extract_selection.SetInputData(1, selection)
            extract_selection.Update()

            # In selection
            # sed_points = vtkPoints()
            # sed_points.InsertNextPoint()
            # selected = vtkPolyData()
            # selected.ShallowCopy(extract_selection.GetOutput())
            # selected.GetPoints().GetData().SetNumberOfComponents(1)
            # # selected.GetPoints().SetNumberOfPoints(2)
            # print(self.scalar)
            # print(selected.GetPoints().GetData())
            # print(selected.GetPoints().GetNumberOfPoints())
            # selected.GetPoints().SetData(self.scalar)

            glyph3D = vtkGlyph3D()
            glyph3D.SetSourceConnection(self.source.GetOutputPort())
            glyph3D.SetInputConnection(extract_selection.GetOutputPort())
            # glyph3D.SetColorModeToColorByScalar()

            self.selected_mapper.SetInputConnection(glyph3D.GetOutputPort())
            self.selected_mapper.ScalarVisibilityOn()
            self.selected_actor.SetMapper(self.selected_mapper)
            self.selected_actor.GetProperty().SetColor(colors.GetColor3d('Red'))

            self.GetInteractor().GetRenderWindow().GetRenderers().GetFirstRenderer().AddActor(self.selected_actor)

        # Forward events
        self.OnLeftButtonDown()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)

        logger.info('Create pca')
        indir = Path('../result/lm_aligned')
        filenames = sorted(indir.glob('*.vtk'))
        pca_stats = PCAStats.from_files(filenames)
        logger.info('Done')

        self.frame = QtWidgets.QWidget()

        self.vl = QtWidgets.QVBoxLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.vl.addWidget(self.vtkWidget)

        colors = vtkNamedColors()

        mesh = read_mesh('../result/ssm/ssm.vtk')

        mapper = vtkPolyDataMapper()
        mapper.SetInputData(mesh)

        actor = vtkActor()
        actor.GetProperty().SetColor(colors.GetColor3d('lightyellow'))
        actor.GetProperty().SetRepresentationToWireframe()
        actor.SetMapper(mapper)
        self.actor = actor

        renderer = vtkRenderer()
        ren_win = self.vtkWidget.GetRenderWindow()
        ren_win.AddRenderer(renderer)
        ren_win.SetWindowName('PointPicking')
        iren = self.vtkWidget.GetRenderWindow().GetInteractor()
        iren.SetRenderWindow(ren_win)

        renderer.AddActor(actor)
        renderer.SetBackground(colors.GetColor3d('AliceBlue'))
        self.ren = renderer

        style = MouseInteractorStyle(mesh)
        style.SetDefaultRenderer(renderer)
        iren.SetInteractorStyle(style)

        self.ren.ResetCamera()

        self.frame.setLayout(self.vl)
        self.setCentralWidget(self.frame)

        self.dock = QtWidgets.QDockWidget('Controls', self)
        dock_widget = QtWidgets.QWidget()
        dock_widget.setLayout(QtWidgets.QVBoxLayout())
        self.dock.setWidget(dock_widget)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dock)

        group = QtWidgets.QGroupBox('Distance', self)
        dock_widget.layout().addWidget(group)
        group.setLayout(QtWidgets.QVBoxLayout())

        def pick_callback(index):
            def callback():
                logger.info(f'Picking {index}')
                style.set_index(index)

            return callback

        button = QtWidgets.QPushButton('Point 1', self)
        button.clicked.connect(pick_callback(0))
        group.layout().addWidget(button)

        button = QtWidgets.QPushButton('Point 2', self)
        button.clicked.connect(pick_callback(1))
        group.layout().addWidget(button)

        button = QtWidgets.QPushButton('Calculate', self)
        group.layout().addWidget(button)

        calc_result = QtWidgets.QLabel('', self)

        def calc_callback():
            logger.info(f'Calc stats for {style.pids[0]} and {style.pids[1]}')
            dists = pca_stats.dists_between(style.pids[0], style.pids[1])

            calc_result.setText(f'mean: {dists.mean():.2f} mm\nstd: {dists.std():.2f} mm')

        button.clicked.connect(calc_callback)
        group.layout().addWidget(calc_result)

        dock_widget.layout().addStretch(1)

        self.show()
        iren.Initialize()
        iren.Start()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()

    sys.exit(app.exec_())
