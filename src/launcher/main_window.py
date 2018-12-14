import os
import importlib
from PyQt5.QtCore import QSize, Qt, QTimerEvent
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QToolButton, QGridLayout, QWidget, QProgressBar
from partseg_utils.global_settings import static_file_folder

import time
class MainWindow(QMainWindow):
    def __init__(self, title):
        super().__init__()
        self.setWindowTitle(title)
        self.lib_path = ""
        self.final_title = ""
        analysis_icon = QIcon(os.path.join(static_file_folder, 'icons', "icon.png"))
        stack_icon = QIcon(os.path.join(static_file_folder, 'icons', "icon_stack.png"))
        self.analysis_button = QToolButton(self)
        self.analysis_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.analysis_button.setIcon(analysis_icon)
        self.analysis_button.setText("Segmentation\nAnalysis")
        self.analysis_button.setIconSize(QSize(100, 100))
        self.mask_button = QToolButton(self)
        self.mask_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.mask_button.setIcon(stack_icon)
        self.mask_button.setText("Mask\nSegmentation")
        self.mask_button.setIconSize(QSize(100, 100))
        self.analysis_button.clicked.connect(self.launch_analysis)
        self.mask_button.clicked.connect(self.launch_mask)
        self.progress = QProgressBar()
        self.progress.setHidden(True)
        layout = QGridLayout()
        layout.addWidget(self.progress, 0, 0, 1, 2)
        layout.addWidget(self.analysis_button, 1, 0)
        layout.addWidget(self.mask_button, 1, 1)
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        self.setWindowIcon(analysis_icon)

    def launch_analysis(self):
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.analysis_button.setDisabled(True)
        self.mask_button.setDisabled(True)
        self.lib_path = "segmentation_analysis.main_window"
        self.final_title = "PartSeg Segmentation Analysis"
        self.startTimer(0)

    def timerEvent(self, a0: 'QTimerEvent'):
        self.killTimer(a0.timerId())
        if self.lib_path != "":
            main_window_module = importlib.import_module(self.lib_path)
            self.launch(main_window_module.MainWindow, self.final_title)


    def launch_mask(self):
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.analysis_button.setDisabled(True)
        self.mask_button.setDisabled(True)
        self.lib_path = "segmentation_mask.stack_gui_main"
        self.final_title = "PartSeg Mask Segmentation"
        self.startTimer(0)

    def window_shown(self):
        self.close()

    def launch(self, cls, title):
        wind = cls(title, self.window_shown)
        wind.show()
        self.wind = wind
