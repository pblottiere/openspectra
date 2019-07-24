#  Developed by Joseph M. Conti and Joseph W. Boardman on 3/17/19 2:30 PM.
#  Last modified 3/17/19 2:30 PM
#  Copyright (c) 2019. All rights reserved.
from typing import Dict

from PyQt5.QtCore import Qt, pyqtSignal, QObject, QPoint, pyqtSlot, QRegExp
from PyQt5.QtGui import QColor, QBrush, QCloseEvent, QFont, QResizeEvent, QRegExpValidator
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, \
    QTableWidget, QTableWidgetItem, QApplication, QStyle, QMenu, QAction, QHBoxLayout, QLabel, QComboBox, QFormLayout, \
    QLineEdit, QPushButton

from openspectra.openspecrtra_tools import RegionOfInterest
from openspectra.openspectra_file import OpenSpectraHeader
from openspectra.utils import Logger, LogHelper


class RegionEvent(QObject):

    def __init__(self, region:RegionOfInterest):
        super().__init__(None)
        self.__region = region

    def region(self) -> RegionOfInterest:
        return self.__region


class RegionStatsEvent(RegionEvent):

    def __init__(self, region:RegionOfInterest):
        super().__init__(region)


class RegionToggleEvent(RegionEvent):

    def __init__(self, region:RegionOfInterest):
        super().__init__(region)


class RegionCloseEvent(RegionEvent):

    def __init__(self, region:RegionOfInterest, row:int):
        super().__init__(region)
        self.__row = row

    def row(self) -> int:
        return self.__row


class RegionNameChangeEvent(RegionEvent):

    def __init__(self, region:RegionOfInterest):
        super().__init__(region)


class RegionSaveEvent(RegionEvent):

    def __init__(self, region:RegionOfInterest, include_bands:bool=False):
        super().__init__(region)
        self.__include_bands = include_bands

    def include_bands(self) -> bool:
        return self.__include_bands


class RegionOfInterestControl(QWidget):

    __LOG:Logger = LogHelper.logger("RegionOfInterestControl")

    stats_clicked = pyqtSignal(RegionStatsEvent)
    region_toggled = pyqtSignal(RegionToggleEvent)
    region_name_changed = pyqtSignal(RegionNameChangeEvent)
    region_saved = pyqtSignal(RegionSaveEvent)
    region_closed = pyqtSignal(RegionCloseEvent)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__regions = list()
        self.__selected_row = None

        layout = QVBoxLayout()

        self.__margins = 5
        layout.setContentsMargins(self.__margins, self.__margins, self.__margins, self.__margins)

        self.__rows = 0
        self.__table = QTableWidget(self.__rows, 4, self)
        self.__table.setShowGrid(False)
        self.__table.verticalHeader().hide()
        self.__table.cellClicked.connect(self.__handle_cell_clicked)
        self.__table.cellChanged.connect(self.__handle_cell_changed)

        self.__table.setColumnWidth(0, 40)

        self.__table.setHorizontalHeaderLabels(["Color", "Name", "Size (h x w)", "Description"])
        layout.addWidget(self.__table)
        self.setLayout(layout)

        self.__init_menu()

    def __init_menu(self):
        self.__menu:QMenu = QMenu(self)
        toggle_action = QAction("Toggle", self)
        toggle_action.triggered.connect(self.__handle_region_toggle)
        self.__menu.addAction(toggle_action)

        stats_action = QAction("Band stats", self)
        stats_action.triggered.connect(self.__handle_band_stats)
        self.__menu.addAction(stats_action)

        self.__menu.addSeparator()

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.__handle_region_save)
        self.__menu.addAction(save_action)

        close_action = QAction("Close", self)
        close_action.triggered.connect(self.__handle_region_close)
        self.__menu.addAction(close_action)

        self.setContextMenuPolicy(Qt.CustomContextMenu)

    def add_item(self, region:RegionOfInterest, color:QColor):
        self.__table.cellClicked.disconnect(self.__handle_cell_clicked)
        self.__table.cellChanged.disconnect(self.__handle_cell_changed)
        self.__table.setRowCount(self.__rows + 1)

        name_item = QTableWidgetItem(region.display_name())

        color_item = QTableWidgetItem("...")
        font = QFont()
        font.setBold(True)
        color_item.setFont(font)
        color_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        color_item.setBackground(QBrush(color))
        color_item.setFlags(Qt.ItemIsEnabled)

        size_item = QTableWidgetItem(
            str(region.image_height()) + " x " + str(region.image_width()))
        size_item.setTextAlignment(Qt.AlignVCenter)
        size_item.setFlags(Qt.ItemIsEnabled)

        description_item = QTableWidgetItem(region.description())
        description_item.setFlags(Qt.ItemIsEnabled)

        self.__table.setItem(self.__rows, 0, color_item)
        self.__table.setItem(self.__rows, 1, name_item)
        self.__table.setItem(self.__rows, 2, size_item)
        self.__table.setItem(self.__rows, 3, description_item)

        if self.__rows == 0:
            self.__table.horizontalHeader().setStretchLastSection(True)

        self.__adjust_width()

        self.__regions.append(region)
        self.__rows += 1
        self.__table.cellClicked.connect(self.__handle_cell_clicked)
        self.__table.cellChanged.connect(self.__handle_cell_changed)

    def remove_all(self):
        self.__table.clearContents()
        self.__regions.clear()
        self.__rows = 0

    def remove(self, event:RegionCloseEvent):
        row = event.row()
        region = self.__regions[row]
        if region is not None:
            self.__table.removeRow(row)
            del self.__regions[row]
            self.__rows -= 1
            self.__selected_row = None

    def __adjust_width(self):
        self.__table.resizeColumnsToContents()
        length = self.__table.horizontalHeader().length()
        RegionOfInterestControl.__LOG.debug("Header length: {0}", length)
        self.setMinimumWidth(length + self.__margins * 2 +
                             QApplication.style().pixelMetric(QStyle.PM_DefaultFrameWidth) * 2)

    @pyqtSlot(int, int)
    def __handle_cell_clicked(self, row:int, column:int):
        position = self.mapToGlobal(QPoint(self.__table.columnViewportPosition(column), self.__table.rowViewportPosition(row)))
        RegionOfInterestControl.__LOG.debug("Cell clicked row: {0}, column: {1}, y pos: {2}",
            row, column, position)
        if column == 0 and -1 < row < len(self.__regions):
            self.__selected_row = row
            RegionOfInterestControl.__LOG.debug("Found region: {0}", self.__regions[row].display_name())
            self.__menu.popup(position)

    @pyqtSlot(int, int)
    def __handle_cell_changed(self, row:int, column:int):
        RegionOfInterestControl.__LOG.debug("Cell changed row: {0}, column: {1}", row, column)
        if column == 1:
            item = self.__table.item(row, column)
            RegionOfInterestControl.__LOG.debug("Cell changed, new value: {0}", item.text())
            region:RegionOfInterest = self.__regions[row]
            region.set_display_name(item.text())
            self.region_name_changed.emit(RegionNameChangeEvent(region))
            self.__adjust_width()

    @pyqtSlot()
    def __handle_region_toggle(self):
        region = self.__regions[self.__selected_row]
        RegionOfInterestControl.__LOG.debug("Toogle region: {0}", region.display_name())
        self.region_toggled.emit(RegionToggleEvent(region))
        self.__selected_row = None

    @pyqtSlot()
    def __handle_region_save(self):
        region = self.__regions[self.__selected_row]
        RegionOfInterestControl.__LOG.debug("Save region: {0}", region.display_name())
        self.region_saved.emit(RegionSaveEvent(region))
        self.__selected_row = None

    @pyqtSlot()
    def __handle_region_close(self):
        region = self.__regions[self.__selected_row]
        RegionOfInterestControl.__LOG.debug("Close region: {0}", region.display_name())
        self.region_closed.emit(RegionCloseEvent(region, self.__selected_row))

    @pyqtSlot()
    def __handle_band_stats(self):
        region = self.__regions[self.__selected_row]
        RegionOfInterestControl.__LOG.debug("Band stats region: {0}", region.display_name())
        self.stats_clicked.emit(RegionStatsEvent(region))
        self.__selected_row = None


class RegionOfInterestDisplayWindow(QMainWindow):

    __LOG:Logger = LogHelper.logger("RegionOfInterestDisplayWindow")

    stats_clicked = pyqtSignal(RegionStatsEvent)
    region_toggled = pyqtSignal(RegionToggleEvent)
    region_name_changed = pyqtSignal(RegionNameChangeEvent)
    region_saved = pyqtSignal(RegionSaveEvent)
    region_closed =  pyqtSignal(RegionCloseEvent)
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Region of Interest")
        self.__region_control = RegionOfInterestControl()
        self.setCentralWidget(self.__region_control)
        self.__region_control.stats_clicked.connect(self.stats_clicked)
        self.__region_control.region_toggled.connect(self.region_toggled)
        self.__region_control.region_name_changed.connect(self.region_name_changed)
        self.__region_control.region_saved.connect(self.region_saved)
        self.__region_control.region_closed.connect(self.region_closed)

    def add_item(self, region:RegionOfInterest, color:QColor):
        self.__region_control.add_item(region, color)

    def remove_all(self):
        self.__region_control.remove_all()

    def remove(self, event:RegionCloseEvent):
        self.__region_control.remove(event)

    def closeEvent(self, event:QCloseEvent):
        self.closed.emit()
        # accepting hides the window
        event.accept()


class RangeSelector(QWidget):

    __LOG:Logger = LogHelper.logger("RangeSelector")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.__init_ui__()

    def __init_ui__(self):
        layout = QHBoxLayout()

        from_layout = QVBoxLayout()
        from_layout.addWidget(QLabel("From:"))

        self.__from_select = QComboBox(self)
        # TODO get ignored for certain styles, like Mac, when not editable
        # TODO possibly allow editable but make it jump to item instead of adding to list?
        self.__from_select.setMaxVisibleItems(20)
        self.__from_select.currentIndexChanged.connect(self.__handle_from_changed)

        from_layout.addWidget(self.__from_select)
        layout.addLayout(from_layout)

        to_layout = QVBoxLayout()
        to_layout.addWidget(QLabel("To:"))

        self.__to_select = QComboBox(self)
        # TODO get ignored for certain styles, like Mac, when not editable
        # TODO possibly allow editable but make it jump to item instead of adding to list?
        self.__to_select.setMaxVisibleItems(20)
        self.__to_select.currentIndexChanged.connect(self.__handle_to_changed)

        to_layout.addWidget(self.__to_select)
        layout.addLayout(to_layout)

        self.setLayout(layout)

    @pyqtSlot(int)
    def __handle_from_changed(self, index:int):
        RangeSelector.__LOG.debug("from index changed to: {0}".format(index))
        if self.__to_select.currentIndex() < index:
            self.__to_select.setCurrentIndex(index)

    @pyqtSlot(int)
    def __handle_to_changed(self, index:int):
        RangeSelector.__LOG.debug("to index changed to: {0}".format(index))
        if self.__from_select.currentIndex() > index:
            self.__from_select.setCurrentIndex(index)

    def clear(self):
        self.__from_select.clear()
        self.__to_select.clear()

    def from_value(self) -> int:
        return int(self.__from_select.currentText())

    def to_value(self) -> int:
        return int(self.__to_select.currentText())

    def set_range(self, start:int, end:int):
        if end <= start:
            raise ValueError("end value must be greater than start")

        self.__from_select.currentIndexChanged.disconnect(self.__handle_from_changed)
        self.__to_select.currentIndexChanged.disconnect(self.__handle_to_changed)

        index = 0
        for item in range(start, end):
            self.__from_select.insertItem(index, str(item))
            self.__to_select.insertItem(index, str(item + 1))
            index += 1

        self.__from_select.setCurrentIndex(0)
        self.__to_select.setCurrentIndex(end - 2)

        self.__from_select.currentIndexChanged.connect(self.__handle_from_changed)
        self.__to_select.currentIndexChanged.connect(self.__handle_to_changed)


class FileSubCubeParams:

    def __init__(self, name:str, lines:int, samples:int, bands:int, file_format:str):
        self.__name = name
        self.__lines = lines
        self.__samples = samples
        self.__bands = bands
        self.__file_format = file_format

    def name(self) -> str:
        return self.__name

    def lines(self) -> int:
        return self.__lines

    def samples(self) -> int:
        return self.__samples

    def bands(self) -> int:
        return self.__bands

    def file_format(self) -> str:
        return self.__file_format


class SubCubeControl(QWidget):

    __LOG:Logger = LogHelper.logger("SubCubeControl")

    cancel = pyqtSignal()

    def __init__(self, files:Dict[str, FileSubCubeParams], parent=None):
        super().__init__(parent)
        self.__files = files

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.__file_list = QComboBox(self)
        self.__file_list.insertItem(0, "Select origin file...")
        self.__file_list.insertItems(1, self.__files.keys())
        self.__file_list.currentIndexChanged.connect(self.__handle_file_select)
        form_layout.addRow("Original File:", self.__file_list)

        self.__file_type = QComboBox(self)
        self.__format_map = {OpenSpectraHeader.BIL_INTERLEAVE : "BIL - Band Interleaved by Line",
                             OpenSpectraHeader.BSQ_INTERLEAVE : "BQS - Band Sequential",
                             OpenSpectraHeader.BIP_INTERLEAVE : "BIP - Band Interleaved by Pixel"}
        self.__file_type.insertItem(0, "")
        self.__file_type.insertItems(1, self.__format_map.values())
        form_layout.addRow("Output File Type:", self.__file_type)

        self.__sample_range = RangeSelector(self)
        form_layout.addRow("Sample Range:", self.__sample_range)

        self.__line_range = RangeSelector(self)
        form_layout.addRow("Line Range:", self.__line_range)

        self.__band_select = QLineEdit(self)
        self.__band_select.setMinimumWidth(250)
        self.__band_validator = QRegExpValidator(QRegExp("[0-9]+((-|,)([0-9]+))*"))
        self.__band_select.setValidator(self.__band_validator)
        self.__band_select.setToolTip\
                ("Use '-' for a range, ',' to sepearate ranges and single bands.\nExample: 1-10,12,14,19-21")
        self.__max_band = 0

        form_layout.addRow("Bands:", self.__band_select)
        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        cancel_button = QPushButton("Cancel", self)
        cancel_button.clicked.connect(self.cancel)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton("Save", self)
        save_button.clicked.connect(self.__handle_save)
        button_layout.addWidget(save_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    @pyqtSlot(int)
    def __handle_file_select(self, index:int):
        if index == 0:
            self.__line_range.clear()
            self.__sample_range.clear()
            self.__max_band = 0
            self.__band_select.clear()
            self.__file_type.setCurrentIndex(0)
        else:
            selected_file_name = self.__file_list.currentText()
            params:FileSubCubeParams = self.__files[selected_file_name]
            self.__line_range.set_range(1, params.lines())
            self.__sample_range.set_range(1, params.samples())
            self.__max_band = params.bands()
            self.__band_select.setText("1-" + str(self.__max_band))
            self.__file_type.setCurrentText(self.__format_map[params.file_format()])

    @pyqtSlot()
    def __handle_save(self):
        file_type = self.__file_type.currentText()
        lines = self.__line_range.from_value(), self.__line_range.to_value()
        samples = self.__sample_range.from_value(), self.__sample_range.to_value()
        bands = self.__band_select.text()

        SubCubeControl.__LOG.debug(
            "save button clicked, type: {0}, lines: {1}, samples: {2}, bands: {3}, bands valid: {4}".
                format(file_type, lines, samples, bands, self.__band_validator.validate(bands, 0)))

        # TODO emit create event


class SubCubeWindow(QMainWindow):

    __LOG:Logger = LogHelper.logger("SubCubeWindow")

    def __init__(self, files:Dict[str, FileSubCubeParams], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Sub-Cube")

        subcube_control = SubCubeControl(files, self)
        subcube_control.cancel.connect(self.__handle_cancel)
        self.setCentralWidget(subcube_control)

        self.setMinimumWidth(500)
        self.setMinimumHeight(325)
        # TODO is this what we really want???
        self.setMaximumWidth(500)
        self.setMaximumHeight(325)

        # TODO position center of screen??

    @pyqtSlot()
    def __handle_cancel(self):
        SubCubeWindow.__LOG.debug("cancel button clicked")
        self.close()

    def resizeEvent(self, event:QResizeEvent):
        SubCubeWindow.__LOG.debug("new size: {0}".format(event.size()))
