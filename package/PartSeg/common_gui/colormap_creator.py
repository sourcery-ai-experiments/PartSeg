import os
import random
import string
from functools import partial
from math import ceil

from PartSegData import icons_dir
from qtpy.QtCore import Qt, QRect, QPointF, Signal
from qtpy.QtGui import QImage, QPaintEvent, QPainter, QMouseEvent, QBrush, QColor, QHideEvent, QFontMetrics, QFont, \
    QShowEvent, QIcon, QResizeEvent
from qtpy.QtWidgets import QWidget, QColorDialog, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox, \
    QToolButton, QScrollArea, QGridLayout
from typing import List, Optional, Dict, Tuple, Iterable, Set
import numpy as np
import bisect

from PartSeg.common_gui.numpy_qimage import convert_colormap_to_image
from PartSeg.common_gui.stack_image_view import ImageView
from PartSeg.project_utils_qt.settings import ViewSettings
from PartSeg.utils.color_image.color_image_base import color_image, create_color_map
from PartSeg.utils.color_image import Color, ColorPosition, ColorMap, BaseColormap


def color_from_qcolor(color: QColor) -> Color:
    """Convert :py:class:`.QColor` to :py:class:`.Color`"""
    return Color(color.red(), color.green(), color.blue())


def qcolor_from_color(color: Color) -> QColor:
    """Convert :py:class:`.Color` to :py:class:`.QColor`"""
    return QColor(color.red, color.green, color.blue)


class ColormapEdit(QWidget):
    """
    Preview of colormap. Double click used for add/remove colors. Single click on marker allows moving them
    """

    double_clicked = Signal(float)  # On double click emit signal with current position factor.

    @staticmethod
    def array_to_image(array: np.ndarray):
        img = color_image(np.linspace((0, 0, 0), (255, 255, 255), 512).T.reshape((3, 512, 1)), [array], [(0, 255)])
        return QImage(img.data, img.shape[1], img.shape[0], img.dtype.itemsize * img.shape[1] * 3, QImage.Format_RGB888)

    def __init__(self):
        super().__init__()
        self.color_list: List[Color] = []
        self.position_list: List[float] = []
        self.move_ind = None
        self.image = convert_colormap_to_image(ColorMap((ColorPosition(0, Color(0, 0, 0)),
                                                         ColorPosition(1, Color(255, 255, 255)))))
        self.setMinimumHeight(60)

    def paintEvent(self, a0: QPaintEvent) -> None:
        painter = QPainter(self)
        margin = 10
        width = self.width() - 2 * margin
        rect = QRect(margin, margin, width, self.height()-2*margin)
        painter.drawImage(rect, self.image)
        painter.save()

        for pos_factor in self.position_list:
            pos = width * pos_factor
            point = QPointF(pos+margin, self.height()/2)
            painter.setBrush(QBrush(Qt.black))
            painter.drawEllipse(point, 5, 5)
            painter.setBrush(QBrush(Qt.white))
            painter.drawEllipse(point, 3, 3)

        painter.restore()

    def refresh(self):
        """Recreate presented image and force repaint event """
        self.image = convert_colormap_to_image(self.colormap)
        self.repaint()

    def _get_color_ind(self, ratio) -> Optional[int]:
        ind = bisect.bisect_left(self.position_list, ratio)
        if len(self.position_list) > ind:
            if abs(self.position_list[ind] - ratio) < 0.01:
                return ind
        if len(self.position_list) > 0 and ind > 0:
            if abs(self.position_list[ind - 1] - ratio) < 0.01:
                return ind - 1
        return None

    def _get_ratio(self, e: QMouseEvent, margin=10):
        frame_margin = 10
        width = self.width() - 2 * frame_margin
        if e.x() < margin or e.x() > self.width() - margin:
            return
        if e.y() < margin or e.y() > self.height() - margin:
            return
        return (e.x() - frame_margin) / width

    def mousePressEvent(self, e: QMouseEvent) -> None:
        ratio = self._get_ratio(e, 5)
        if ratio is None:
            return
        ind = self._get_color_ind(ratio)
        if ind is None:
            return
        self.move_ind = ind

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        self._move_color(e)
        self.move_ind = None

    def _move_color(self, e: QMouseEvent) -> None:
        ratio = self._get_ratio(e)
        if ratio is None or self.move_ind is None:
            return
        self.position_list.pop(self.move_ind)
        ind = bisect.bisect_left(self.position_list, ratio)
        col = self.color_list.pop(self.move_ind)
        self.color_list.insert(ind, col)
        self.position_list.insert(ind, ratio)
        self.move_ind = ind
        self.refresh()

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        self._move_color(e)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        If click near marker remove it. Otherwise emmit `double_click` signal with event position factor.
        """
        ratio = self._get_ratio(event)
        if ratio is None:
            return
        ind = self._get_color_ind(ratio)
        if ind is not None:
            self.position_list.pop(ind)
            self.color_list.pop(ind)
            self.refresh()
            return
        self.double_clicked.emit(ratio)

    def add_color(self, color: ColorPosition):
        """
        Add color to current colormap

        :param color: Color with position.

        """
        ind = bisect.bisect_left(self.position_list, color.color_position)
        self.color_list.insert(ind, color.color)
        self.position_list.insert(ind, color.color_position)
        self.refresh()

    def clear(self):
        """
        Remove color markers. Reset to initial state.
        """
        self.color_list = []
        self.position_list = []
        self.image = convert_colormap_to_image(ColorMap((ColorPosition(0, Color(0, 0, 0)),
                                                         ColorPosition(1, Color(255, 255, 255)))))
        self.repaint()

    def distribute_evenly(self):
        """
        Distribute color markers evenly.
        """
        for i, pos in enumerate(np.linspace(0, 1, len(self.position_list))):
            self.position_list[i] = pos
        self.refresh()

    @property
    def colormap(self) -> ColorMap:
        """colormap getter"""
        return ColorMap(tuple([ColorPosition(x, y) for x, y in zip(self.position_list, self.color_list)]))

    @colormap.setter
    def colormap(self, val: ColorMap):
        """colormap setter"""
        self.position_list = [x.color_position for x in val]
        self.color_list = [x.color for x in val]


class ColormapCreator(QWidget):
    """
    Widget for creating colormap.
    """
    colormap_selected = Signal(ColorMap)
    """
    emitted on save button click. Contains current colormap in format accepted by :py:func:`create_color_map` 
    """

    def __init__(self):
        super().__init__()
        self.color_picker = QColorDialog()
        self.color_picker.setWindowFlag(Qt.Widget)
        self.color_picker.setOptions(QColorDialog.DontUseNativeDialog | QColorDialog.NoButtons)
        self.show_colormap = ColormapEdit()
        self.clear_btn = QPushButton("Clear")
        self.save_btn = QPushButton("Save")
        self.distribute_btn = QPushButton("Distribute evenly")
        layout = QVBoxLayout()
        layout.addWidget(self.color_picker)
        layout.addWidget(self.show_colormap)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.distribute_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        self.show_colormap.double_clicked.connect(self.add_color)
        self.clear_btn.clicked.connect(self.show_colormap.clear)
        self.save_btn.clicked.connect(self.save)
        self.distribute_btn.clicked.connect(self.show_colormap.distribute_evenly)

    def add_color(self, pos):
        color = self.color_picker.currentColor()
        self.show_colormap.add_color(ColorPosition(pos, color_from_qcolor(color)))

    def save(self):
        if self.show_colormap.colormap:
            self.colormap_selected.emit(self.show_colormap.colormap)

    def current_colormap(self) -> ColorMap:
        """:return: current colormap"""
        return self.show_colormap.colormap

    def set_colormap(self, colormap: ColorMap):
        """set current colormap"""
        self.show_colormap.colormap = colormap
        self.show_colormap.refresh()


class PColormapCreator(ColormapCreator):
    """
    :py:class:`~.ColormapCreator` variant which save result in :py:class:`.ViewSettings`
    """
    def __init__(self, settings: ViewSettings):
        super().__init__()
        self.settings = settings
        for i, el in enumerate(settings.get_from_profile("custom_colors", [])):
            self.color_picker.setCustomColor(i, qcolor_from_color(el))
        self.prohibited_names = set(self.settings.colormap_dict.keys())  # Prohibited name is added to reduce
        # probability of colormap cache collision

    def _save_custom_colors(self):
        colors = [color_from_qcolor(self.color_picker.customColor(i)) for i in range(self.color_picker.customCount())]
        self.settings.set_in_profile("custom_colors", colors)

    def hideEvent(self, a0: QHideEvent) -> None:
        """Save custom colors on hide"""
        self._save_custom_colors()

    def save(self):
        if self.show_colormap.colormap:
            for i in range(1000):
                rand_name = "custom_" + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(10))
                if rand_name not in self.settings.colormap_dict and rand_name not in self.prohibited_names:
                    break
            else:
                raise RuntimeError("Cannot add colormap")
            self.prohibited_names.add(rand_name)
            self.settings.colormap_dict[rand_name] = self.show_colormap.colormap
            self.settings.chosen_colormap_change(rand_name, True)
            self.colormap_selected.emit(self.show_colormap.colormap)


class _IconSelector:
    def __init__(self):
        self._close_icon = None
        self._edit_icon = None

    @property
    def close_icon(self) -> QIcon:
        if self._close_icon is None:
            self._close_icon = QIcon(os.path.join(icons_dir, "task-reject.png"))
        return self._close_icon

    @property
    def edit_icon(self):
        if self._edit_icon is None:
            self._edit_icon = QIcon(os.path.join(icons_dir, "configure.png"))
        return self._edit_icon


_icon_selector = _IconSelector()


class ChannelPreview(QWidget):
    """
    class for preview single colormap. Witch checkbox for change selection.

    :param colormap: colormap to show
    :param accepted: if checkbox should be checked
    :param name: name which will be emitted in all signals as firs argument
    :param ind: number which will be emmited in all signals as second argument
    """
    selection_changed = Signal(str, bool)
    """checkbox selection changed (name)"""
    edit_request = Signal([str], [ColorMap])
    """send after pressing edit signal (name) (ColorMap object)"""
    remove_request = Signal(str)
    """Signal with name of colormap (name)"""

    def __init__(self, colormap: BaseColormap, accepted: bool, name: str, removable: bool = False, used: bool = False):
        super().__init__()
        self.image = convert_colormap_to_image(colormap)
        self.name = name
        self.removable = removable
        self.checked = QCheckBox()
        self.checked.setChecked(accepted)
        self.checked.setDisabled(used)
        self.setMinimumWidth(80)
        metrics = QFontMetrics(QFont())
        layout = QHBoxLayout()
        layout.addWidget(self.checked)
        layout.addStretch(1)
        self.remove_btn = QToolButton()
        self.remove_btn.setIcon(_icon_selector.close_icon)
        if removable:
            self.remove_btn.setToolTip("Remove colormap")
        else:
            self.remove_btn.setToolTip("This colormap is protected")
        self.remove_btn.setEnabled(not accepted and self.removable)

        self.edit_btn = QToolButton()
        self.edit_btn.setIcon(_icon_selector.edit_icon)
        layout.addWidget(self.remove_btn)
        layout.addWidget(self.edit_btn)
        self.setLayout(layout)
        self.checked.stateChanged.connect(self._selection_changed)
        self.edit_btn.clicked.connect(partial(self.edit_request.emit, name))
        if isinstance(colormap, ColorMap):
            self.edit_btn.clicked.connect(partial(self.edit_request[ColorMap].emit, colormap))
            self.edit_btn.setToolTip("Create colormap base on this")
        else:
            self.edit_btn.setDisabled(True)
            self.edit_btn.setToolTip("This colormap is not editable")
        self.remove_btn.clicked.connect(partial(self.remove_request.emit, name))
        self.setMinimumHeight(max(metrics.height(), self.edit_btn.minimumHeight(), self.checked.minimumHeight())+20)

    def _selection_changed(self, _=None):
        chk = self.checked.isChecked()
        self.selection_changed.emit(self.name, chk)
        self.remove_btn.setEnabled(not chk and self.removable)

    def set_blocked(self, block):
        """Set if block possibility of remove or uncheck """
        self.checked.setDisabled(block)
        if self.removable and not block:
            self.remove_btn.setToolTip("Remove colormap")
        else:
            self.remove_btn.setToolTip("This colormap is protected")
            self.remove_btn.setDisabled(True)

    @property
    def state_changed(self):
        """Inner checkbox stateChanged signal"""
        return self.checked.stateChanged

    @property
    def is_checked(self):
        """If colormap is selected"""
        return self.checked.isChecked()

    def set_chosen(self, state: bool):
        """Set selection of check box."""
        self.checked.setChecked(state)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        start = 2 * self.checked.x() + self.checked.width()
        end = self.remove_btn.x() - self.checked.x()
        rect = self.rect()
        rect.setX(start)
        rect.setWidth(end-start)
        painter.drawImage(rect, self.image)
        super().paintEvent(event)


class ColormapList(QWidget):
    """
    Show list of colormaps
    """
    edit_signal = Signal(ColorMap)
    """Colormap for edit"""

    remove_signal = Signal(str)
    """Name of colormap to remove"""

    visibility_colormap_change = Signal(str, bool)
    """Hide or show colormap"""

    def __init__(self, colormap_map: Dict[str, Tuple[ColorMap, bool]], selected: Optional[Iterable[str]] = None):
        super().__init__()
        if selected is None:
            self._selected = set()
        else:
            self._selected = set(selected)
        self._blocked = set()
        self.current_columns = 1
        self.colormap_map = colormap_map
        self._widget_dict: Dict[str, ChannelPreview] = {}
        self.scroll_area = QScrollArea()
        self.central_widget = QWidget()
        layout2 = QVBoxLayout()
        self.grid_layout = QGridLayout()
        layout2.addLayout(self.grid_layout)
        layout2.addStretch(1)
        layout2.setContentsMargins(0, 0, 0, 0)

        self.central_widget.setLayout(layout2)
        self.central_widget.setMinimumWidth(300)
        self.scroll_area.setWidget(self.central_widget)
        self.scroll_area.setWidgetResizable(True)

        layout = QVBoxLayout()
        layout.addWidget(self.scroll_area)
        self.setLayout(layout)

    def showEvent(self, event: QShowEvent):
        self.refresh()

    def get_selected(self) -> Set[str]:
        """Already selected colormaps"""
        return set(self._selected)

    def change_selection(self, name, selected):
        if selected:
            self._selected.add(name)
        else:
            self._selected.remove(name)
        self.visibility_colormap_change.emit(name, selected)

    def blocked(self) -> Set[str]:
        """Channels that cannot be turn of and remove"""
        return self._blocked

    def _get_columns(self):
        return max(1, self.width() // 400)

    def resizeEvent(self, event: QResizeEvent):
        if self._get_columns() != self.current_columns:
            self.refresh()
            self.central_widget.repaint()

    def refresh(self):
        layout: QGridLayout = self.grid_layout
        cache_dict: Dict[str, ChannelPreview] = {}
        self._widget_dict = {}
        for _ in range(layout.count()):
            el: ChannelPreview = layout.takeAt(0).widget()
            if el.name in self.colormap_map:
                cache_dict[el.name] = el
            else:
                el.deleteLater()
                el.edit_request[ColorMap].disconnect()
                el.remove_request.disconnect()
                el.selection_changed.disconnect()
        selected = self.get_selected()
        blocked = self.blocked()
        columns = self._get_columns()
        for i, (name, (colormap, removable)) in enumerate(self.colormap_map.items()):
            if name in cache_dict:
                widget = cache_dict[name]
                widget.set_blocked(name in blocked)
                widget.set_chosen(name in selected)
            else:
                widget = ChannelPreview(colormap, name in selected, name, removable=removable, used=name in blocked)
                widget.edit_request[ColorMap].connect(self.edit_signal)
                widget.remove_request.connect(self._remove_request)
                widget.selection_changed.connect(self.change_selection)
            layout.addWidget(widget, i // columns, i % columns)
            self._widget_dict[name] = widget
        widget: QWidget = layout.itemAt(0).widget()
        height = widget.minimumHeight()
        self.current_columns = columns
        self.central_widget.setMinimumHeight((height + 10) * ceil(len(self.colormap_map) / columns))

    def check_state(self, name: str) -> bool:
        """
        Check state of widget representing given colormap

        :param name: name of colormap which representing widget should be checked
        """
        return self._widget_dict[name].is_checked

    def set_state(self, name: str, state: bool) -> None:
        """
        Set if given colormap is selected

        :param name: name of colormap
        :param state: state to be set
        """
        self._widget_dict[name].set_chosen(state)

    def get_colormap_widget(self, name) -> ChannelPreview:
        """Access to widget showing colormap. Created for testing purpose."""
        return self._widget_dict[name]

    def _remove_request(self, name):
        _, removable = self.colormap_map[name]
        if not removable:
            raise ValueError(f"ColorMap {name} is protected from remove")
        if name not in self.colormap_map:
            raise ValueError(f"color with name {name} not found in any dict")
        del self.colormap_map[name]


class PColormapList(ColormapList):
    """
        Show list of colormaps. Integrated with :py:class:`.ViewSettings`

        :param settings: used for store state
        :param control_names: list of names of :py:class:`.ImageView` for protect used channels from uncheck or remove
    """
    def __init__(self, settings: ViewSettings, control_names: List[str]):
        super().__init__(settings.colormap_dict)
        settings.colormap_dict.colormap_removed.connect(self.refresh)
        settings.colormap_dict.colormap_added.connect(self.refresh)
        settings.colormap_changes.connect(self.refresh)
        self.settings = settings
        self.color_names = control_names

    def get_selected(self) -> Set[str]:
        return set(self.settings.chosen_colormap)

    def change_selection(self, name, selected):
        self.visibility_colormap_change.emit(name, selected)
        self.settings.chosen_colormap_change(name, selected)

    def blocked(self) -> Set[str]:
        # TODO check only currently presented channels
        blocked = set()
        for el in self.color_names:
            num = self.settings.get_from_profile(f"{el}.channels_count", 0)
            for i in range(num):
                blocked.add(self.settings.get_channel_info(el, i))
        return blocked

    def _change_colormap_visibility(self, name, visible):
        colormaps = set(self.settings.chosen_colormap)
        if visible:
            colormaps.add(name)
        else:
            try:
                colormaps.remove(name)
            except KeyError:
                pass
        self.settings.chosen_colormap = list(sorted(colormaps))