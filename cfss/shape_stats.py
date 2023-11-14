import argparse
import os
import sys
from functools import wraps
from pathlib import Path
from typing import Callable

import numpy as np
import PyQt5
import vtk
from logzero import logger
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget
from ssm import PCAStats

# vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkIdTypeArray
from vtkmodules.vtkCommonDataModel import vtkSelection, vtkSelectionNode
from vtkmodules.vtkFiltersCore import vtkGlyph3D, vtkPolyDataNormals
from vtkmodules.vtkFiltersExtraction import vtkExtractSelection
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkDataSetMapper,
    vtkHardwarePicker,
    vtkPolyDataMapper,
    vtkRenderer,
)


logger.setLevel(os.environ.get('LOGLEVEL', 'INFO'))

# https://github.com/pyvista/pyvista/discussions/4781


def left_button_on_exit(method):
    '''
    Call `self.OnLeftButtonDown()` on exit
    '''

    @wraps(method)
    def _impl(self, *method_args, **method_kwargs):
        method(self, *method_args, **method_kwargs)
        self.OnLeftButtonDown()

    return _impl


# Catch mouse events
class MouseInteractorStyle(vtkInteractorStyleTrackballCamera):
    def __init__(self, data):
        self.AddObserver('LeftButtonPressEvent', self.left_button_press_event)
        self.data = data
        self.selected_mapper = vtkDataSetMapper()
        self.selected_actor = vtkActor()
        self.selected_actor.GetProperty().SetColor(vtkNamedColors().GetColor3d('Red'))
        self.selected_actor.SetMapper(self.selected_mapper)
        picker = vtkHardwarePicker()
        picker.SnapToMeshPointOn()
        picker.SetPixelTolerance(5)
        self.picker = picker
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
        self.pick_index = None
        self.on_change = []

    def set_index(self, index: int):
        self.pick_index = index

    def add_on_change(self, callback: Callable):
        self.on_change.append(callback)

    @left_button_on_exit
    def left_button_press_event(self, obj, event):
        if self.pick_index is None:
            return

        picker = self.picker

        # Get the location of the click (in window coordinates)
        pos = self.GetInteractor().GetEventPosition()

        # Pick from this location.
        picker.Pick(pos[0], pos[1], 0, self.GetDefaultRenderer())
        pid = picker.GetPointId()
        if pid != -1:
            logger.info(f'Picked point for {self.pick_index}: {pid}')

            self.pids[self.pick_index] = pid
            self.ids.SetValue(0, self.pids[0])
            self.ids.SetValue(1, self.pids[1])
            self.pick_index = None

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

            glyph3D = vtkGlyph3D()
            glyph3D.SetSourceConnection(self.source.GetOutputPort())
            glyph3D.SetInputConnection(extract_selection.GetOutputPort())
            # glyph3D.SetColorModeToColorByScalar()

            self.selected_mapper.SetInputConnection(glyph3D.GetOutputPort())
            # self.selected_mapper.ScalarVisibilityOn()

            self.GetInteractor().GetRenderWindow().GetRenderers().GetFirstRenderer().AddActor(self.selected_actor)
            for cb in self.on_change:
                cb()


def make_parser():
    parser = argparse.ArgumentParser(description='Shape stats.')
    parser.add_argument('-i', '--input', help='Input directory. default: %(default)s', default='../result/lm_aligned')
    parser.add_argument(
        '--morph_max', help='Morph slider\'s maximum value. default: %(default)s', default=100, type=int
    )
    parser.add_argument('--max_coef', help='Maximum coeficient. default: %(default)s', default=3, type=int)
    parser.add_argument('--pcs', help='Number of principal components. default: %(default)s', default=3, type=int)
    parser.add_argument('--cameras', help='Camera preset settings (`landmark.CameraPresets`) in json format')

    return parser


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)
        self.setWindowTitle('CFDB Browser')
        self.resize(1024, 1024)

        args = make_parser().parse_args()

        logger.info('Create PCA')
        indir = Path(args.input)
        filenames = sorted(indir.glob('*.vtk'))
        pca_stats, mesh = PCAStats.from_files(filenames)
        logger.info('Done')

        self.frame = QtWidgets.QWidget()

        self.vl = QtWidgets.QVBoxLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.vl.addWidget(self.vtkWidget)

        colors = vtkNamedColors()

        mesh_points = vtk_to_numpy(mesh.GetPoints().GetData())

        mapper = vtkPolyDataMapper()
        mapper.SetInputData(mesh)

        actor = vtkActor()
        actor.GetProperty().SetColor(colors.GetColor3d('lightyellow'))
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

        group = QtWidgets.QGroupBox('Rendering', self)
        dock_widget.layout().addWidget(group)
        group.setLayout(QtWidgets.QVBoxLayout())
        combobox = QtWidgets.QComboBox(self)
        combobox.addItems(['Surface', 'Surface With Edges', 'Wireframe', 'Points'])

        def set_representation(index: int):
            actor.GetProperty().EdgeVisibilityOff()
            if index == 0:
                actor.GetProperty().SetRepresentationToSurface()
            elif index == 1:
                actor.GetProperty().SetRepresentationToSurface()
                actor.GetProperty().EdgeVisibilityOn()
            elif index == 2:
                actor.GetProperty().SetRepresentationToWireframe()
            elif index == 3:
                actor.GetProperty().SetRepresentationToPoints()
            else:
                raise RuntimeError(f'Invalid index for rendering: {index}')
            actor.Modified()
            ren_win.Render()

        combobox.currentIndexChanged.connect(set_representation)
        group.layout().addWidget(combobox)

        if args.cameras:
            import landmark

            with open(args.cameras) as f:
                presets = landmark.CameraPresets.model_validate_json(f.read()).presets
            logger.info(f'Initialize camera with {presets[0].name}')
            param = presets[0].camera
            cam = self.ren.GetActiveCamera()
            cam.SetPosition(*param.position)
            cam.SetViewUp(*param.view_up)
            cam.SetFocalPoint(*param.focal_point)

            group = QtWidgets.QGroupBox('Camera', self)
            dock_widget.layout().addWidget(group)
            group.setLayout(QtWidgets.QHBoxLayout())

            def camera_callback(param: landmark.Camera):
                def callback():
                    cam = self.ren.GetActiveCamera()
                    cam.SetPosition(*param.position)
                    cam.SetViewUp(*param.view_up)
                    cam.SetFocalPoint(*param.focal_point)
                    cam.Modified()
                    ren_win.Render()

                return callback

            for preset in presets:
                button = QtWidgets.QPushButton(preset.name[0], self)
                button.setToolTip(preset.name)
                button.setStyleSheet('padding: 2px')
                button.clicked.connect(camera_callback(preset.camera))
                group.layout().addWidget(button)

        group = QtWidgets.QGroupBox('Distance', self)
        group.setToolTip('Euclidean distance between two points')
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

        calc_result = QtWidgets.QLabel('', self)

        def calc_callback():
            logger.debug(f'Calc stats for {style.pids[0]} and {style.pids[1]}')
            dists = pca_stats.dists_between(style.pids[0], style.pids[1])
            p1 = np.array(mesh.GetPoint(style.pids[0]))
            p2 = np.array(mesh.GetPoint(style.pids[1]))
            cur_dist = np.linalg.norm(p1 - p2)
            d_mean = dists.mean()
            d_std = dists.std()
            text1 = f'Current:\n {cur_dist:.2f} mm'
            if d_std > 0:
                score = (cur_dist - d_mean) / d_std
                text1 += f'\n z-score: {score:.2f}'

            text2 = f'Statistics\n mean: {d_mean:.2f} mm\n std: {d_std:.2f} mm'
            text = '\n'.join([text1, text2])
            calc_result.setText(text)

        style.add_on_change(calc_callback)
        group.layout().addWidget(calc_result)

        group = QtWidgets.QGroupBox('Shape', self)
        shape_group = group
        dock_widget.layout().addWidget(group)
        group.setLayout(QtWidgets.QVBoxLayout())

        group = QtWidgets.QGroupBox('Morph to', self)
        morph_group = group
        dock_widget.layout().addWidget(group)
        group.setLayout(QtWidgets.QVBoxLayout())

        data_list = ['average'] + [f'case {i+1}' for i in range(len(pca_stats.components))]
        morph_slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        morph_slider.setMaximum(max(100, args.morph_max))
        morph_slider.setMinimum(min(0, 0 - (args.morph_max - 100)))
        morph_slider.setValue(0)
        morph_boxes = []
        for i in range(2):
            combobox = QtWidgets.QComboBox(self)
            combobox.addItems(data_list)

            def callback(_):
                # change value from 1 to 0 to make sure to CHANGE the value to 0
                morph_slider.setValue(1)  # TODO: fix this workaround
                morph_slider.setValue(0)

            combobox.currentIndexChanged.connect(callback)
            morph_boxes.append(combobox)
            if i == 0:
                shape_group.layout().addWidget(combobox)
            else:
                morph_group.layout().addWidget(combobox)

        normal_filter = vtkPolyDataNormals()
        normal_filter.SetInputData(mesh)
        normal_filter.SplittingOff()

        def morph_slider_callback():
            morph_slider.setToolTip(f'{slider.value()}')
            value = morph_slider.value() / 100
            logger.debug('Morph slider changed: %s', value)
            idx1, idx2 = morph_boxes[0].currentIndex(), morph_boxes[1].currentIndex()
            # mean shape is `idx1 == 0 `
            zeros = np.zeros_like(pca_stats.all_coefs[0])
            coef1 = zeros if idx1 == 0 else pca_stats.all_coefs[idx1 - 1]
            coef2 = zeros if idx2 == 0 else pca_stats.all_coefs[idx2 - 1]
            coef = (1 - value) * coef1 + value * coef2
            set_coef(coef)

        morph_slider.valueChanged.connect(morph_slider_callback)
        group.layout().addWidget(morph_slider)

        group = QtWidgets.QGroupBox('PCA', self)
        dock_widget.layout().addWidget(group)
        group.setLayout(QtWidgets.QVBoxLayout())

        pc_sliders = []

        PC_DENOM = 10

        def pc_callback(index: int):
            def callback():
                coef = pca_stats.pca.transform(mesh_points.ravel()[np.newaxis])[0]
                value = pc_sliders[index].value() / PC_DENOM
                coef[index] = value * np.sqrt(pca_stats.pca.explained_variance_[index])
                set_coef(coef)

            return callback

        pca_label = QtWidgets.QLabel('magnitude = 0')
        pca_label.setToolTip('Magnitude of coefficients')
        group.layout().addWidget(pca_label)
        n_pcs = min(args.pcs, len(filenames) - 1)
        logger.info('Number of PCs: %d', n_pcs)
        for i in range(n_pcs):
            group.layout().addWidget(QtWidgets.QLabel(f'PC {i+1}'))
            slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
            slider.setMaximum(PC_DENOM * args.max_coef)
            slider.setMinimum(PC_DENOM * -args.max_coef)
            slider.setValue(0)
            pc_sliders.append(slider)
            slider.valueChanged.connect(pc_callback(i))
            group.layout().addWidget(slider)

        def set_coef(coef):
            normed_coef = coef / np.sqrt(pca_stats.pca.explained_variance_)
            pca_label.setText(f'magnitude = {np.linalg.norm(normed_coef):.02f}')
            for i, slider in enumerate(pc_sliders):
                slider.blockSignals(True)
                c = normed_coef[i]
                slider.setValue(int(PC_DENOM * c))
                slider.blockSignals(False)
            mesh_points[:] = pca_stats.pca.inverse_transform(coef[np.newaxis])[0].reshape(
                -1, 3
            )  # pca_stats.mean + coef * pca_stats.components
            mesh.GetPoints().SetData(numpy_to_vtk(mesh_points))
            normal_filter.Update()
            normals = normal_filter.GetOutput()
            mesh.GetCellData().SetNormals(normals.GetCellData().GetNormals())  # TODO: is this actually working?
            mesh.Modified()
            ren_win.Render()
            calc_callback()

        dock_widget.layout().addStretch(1)

        self.show()
        iren.Initialize()
        iren.Start()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()

    sys.exit(app.exec_())
