import typing
from PyQt5.QtCore import pyqtSignal

from .algorithm_description import SegmentationProfile
from .partseg_utils import PartEncoder, part_hook, HistoryElement, SegmentationPipeline
from .io_functions import save_project
from project_utils.settings import BaseSettings
import numpy as np

MASK_COLORS = {"black": np.array((0, 0, 0)), "white": np.array((255, 255, 255)), "red": np.array((255, 0, 0)),
               "green": np.array((0, 255, 0)), "blue": np.array((0, 0, 255))}


class PartSettings(BaseSettings):
    mask_changed = pyqtSignal()
    json_encoder_class = PartEncoder
    decode_hook = part_hook

    def __init__(self, json_path):
        super().__init__(json_path)
        self._mask = None
        self.full_segmentation = None
        self.segmentation_history: typing.List[HistoryElement] = []
        self.undo_segmentation_history: typing.List[HistoryElement] = []

    @property
    def use_physical_unit(self):
        return self.get("use_physical_unit", False)

    def set_use_physical_unit(self, value):
        self.set("use_physical_unit", value)

    @property
    def mask(self):
        if self._image.mask is not None:
            return self._image.mask[0]
        return None

    @mask.setter
    def mask(self, value):
        try:
            self._image.set_mask(value)
            self.mask_changed.emit()
        except ValueError:
            raise ValueError("mask do not fit to image")

    def _image_changed(self):
        super()._image_changed()
        self._mask = None

    def load_profiles(self):
        pass

    def components_mask(self):
        return np.array([0] + [1] * self.segmentation.max(), dtype=np.uint8)

    def save_project(self, file_path):
        dkt = dict()
        dkt["segmentation"] = self.segmentation
        algorithm_name = self.get("last_executed_algorithm")
        dkt["algorithm_parameters"] = {"name": algorithm_name, "values": self.get(f"algorithms.{algorithm_name}")}
        dkt["mask"] = self.mask
        dkt["full_segmentation"] = self.full_segmentation
        dkt["history"] = self.segmentation_history
        dkt["image"] = self.image
        save_project(file_path, **dkt)

    @property
    def segmentation_pipelines(self) -> typing.Dict[str, SegmentationPipeline]:
        return self.get("segmentation_pipelines", dict())

    @property
    def segmentation_profiles(self) -> typing.Dict[str, SegmentationProfile]:
        return self.get("segmentation_profiles", dict())


def load_project(file_path, settings):
    pass

def save_labeled_image(file_path, settings):
    pass