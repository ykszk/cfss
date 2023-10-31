import argparse
import sys

import PyQt5
import vtk

# import vtkmodules.vtkRenderingOpenGL2
from landmark import load_landmarks, locate_landmarks
from logzero import logger
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget
from utils import read_mesh, write_mesh

# from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonCore import vtkPoints, vtkStringArray
from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkFiltersSources import vtkSphereSource
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkActor2D,
    vtkGlyph3DMapper,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)
from vtkmodules.vtkRenderingLabel import vtkLabeledDataMapper


# https://examples.vtk.org/site/Python/GeometricObjects/IsoparametricCellsDemo/
# https://examples.vtk.org/site/Cxx/Visualization/LabelContours/


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        QtWidgets.QMainWindow.__init__(self, parent)

        self.frame = QtWidgets.QWidget()

        self.vl = QtWidgets.QVBoxLayout()
        self.vtkWidget = QVTKRenderWindowInteractor(self.frame)
        self.vl.addWidget(self.vtkWidget)

        self.ren = vtkRenderer()
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.vtkWidget.GetRenderWindow().GetInteractor()

        parser = argparse.ArgumentParser(description='Show lanrmark points on mesh.')
        parser.add_argument('mesh', help='Mesh vtp filename')
        parser.add_argument('landmark', help='Lanrmark .mrk.json filename')
        parser.add_argument(
            '--target',
            help='Optional mesh to show lanrmark points on. <mesh> is used by default. points in <mesh> and <target> should be registered.',
        )

        args = parser.parse_args()

        logger.info('Load %s', args.mesh)
        mesh = read_mesh(args.mesh)
        logger.info('Load %s', args.landmark)
        landmarks = load_landmarks(args.landmark)
        landmark_ids = locate_landmarks(mesh, landmarks)
        vtk_points = vtkPoints()
        vtk_points.Resize(len(landmark_ids))
        if args.target:
            mesh = read_mesh(args.target)
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
        self.actor = actor
        # actor.GetProperty().SetRepresentationToWireframe()

        # Create a rendering window and renderer
        self.ren = vtkRenderer()
        # renWin = vtkRenderWindow()
        renWin = self.vtkWidget.GetRenderWindow()
        renWin.AddRenderer(self.ren)
        renWin.SetWindowName('Craniofacial landmarks')

        # Create a renderwindowinteractor
        # iren = vtkRenderWindowInteractor()
        # renWin.GetInteractor()
        iren = renWin.GetInteractor()
        iren.SetRenderWindow(renWin)

        style = vtkInteractorStyleTrackballCamera()
        iren.SetInteractorStyle(style)

        # Assign actor to the renderer
        self.ren.AddActor(actor)

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
        self.ren.AddViewProp(pointActor)

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
        self.ren.AddViewProp(labelActor)

        # Enable user interface interactor
        # iren.Initialize()
        # renWin.Render()

        self.ren.SetBackground(colors.GetColor3d('AliceBlue'))
        # ren.GetActiveCamera().SetPosition(-0.5, -100, -20.0)
        # ren.GetActiveCamera().SetViewUp(0.0, 0.0, 1.0)
        # renWin.Render()
        # iren.Start()

        self.dock = QtWidgets.QDockWidget('Controls', self)
        dock_widget = QtWidgets.QWidget()
        dock_widget.setLayout(QtWidgets.QVBoxLayout())
        slider = QtWidgets.QSlider(Qt.Orientation.Horizontal)
        slider.setMaximum(100)
        slider.setMinimum(0)
        slider.setValue(50)
        slider.valueChanged.connect(lambda: self.set_opacity(slider.value() / 100))
        self.opacity_slider = slider
        dock_widget.layout().addWidget(self.opacity_slider)
        self.dock.setWidget(dock_widget)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.dock)

        # self.ren.AddActor(actor)

        self.ren.ResetCamera()

        self.frame.setLayout(self.vl)
        self.setCentralWidget(self.frame)

        self.show()
        self.iren.Initialize()

    def set_opacity(self, opacity: float):
        self.actor.GetProperty().SetOpacity(opacity)
        self.actor.GetProperty().Modified()
        self.vtkWidget.GetRenderWindow().Render()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    window = MainWindow()

    sys.exit(app.exec_())
