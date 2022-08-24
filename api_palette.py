# Copyright (c) 2016-2017
# Milan Bohacek <milan.bohacek+apipalette@gmail.com>
# All rights reserved.
#
# ==============================================================================
#
# This file is part of API Palette.
#
# API Palette is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# ==============================================================================

import idaapi
import idautils
import idc
from idaapi import PluginForm
from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5
import re
import inspect

last_api = ""
last_api_search = ""

# timing = 0

# --------------------------------------------------------------------------


def list_api():
    api_list = []
    for module in [idaapi, idautils, idc]:
        for i in inspect.getmembers(module, inspect.isfunction):
            # api_name api_content module_name
            api_list.append((i[0], i[1], module.__name__))
    return sorted(api_list, key=lambda x: x[0])


# --------------------------------------------------------------------------


class MyEdit(QtWidgets.QLineEdit):
    def keyPressEvent(self, event):
        if event.key() in [QtCore.Qt.Key_Down, QtCore.Qt.Key_Up, QtCore.Qt.Key_PageDown, QtCore.Qt.Key_PageUp]:
            QtWidgets.QApplication.sendEvent(self.lst, event)

        QtWidgets.QLineEdit.keyPressEvent(self, event)


# --------------------------------------------------------------------------


class MyApiList(QtWidgets.QListView):
    def keyPressEvent(self, event):
        super(MyApiList, self).keyPressEvent(event)

    def moveCursor(self, cursorAction, modifiers):
        idx = self.currentIndex()
        row = idx.row()
        cnt = idx.model().rowCount()

        if cursorAction in [QtWidgets.QAbstractItemView.MoveUp, QtWidgets.QAbstractItemView.MovePrevious]:
            if row == 0:
                cursorAction = QtWidgets.QAbstractItemView.MoveEnd

        if cursorAction in [QtWidgets.QAbstractItemView.MoveDown, QtWidgets.QAbstractItemView.MoveNext]:
            if row + 1 == cnt:
                cursorAction = QtWidgets.QAbstractItemView.MoveHome

        return super(MyApiList, self).moveCursor(cursorAction, modifiers)


# --------------------------------------------------------------------------


class api_delegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, parent):
        self.cached_size = None
        super(api_delegate, self).__init__(parent)
        self.template_str = "<table cellspacing=0 width=750 cellpadding=0><tr><td width = 20%>{}</td><td width = 60% >{}</td><td width = 10% >{}</td></tr></table>"
        # self.template_str = "<table cellspacing=0 width=750 cellpadding=0><tr><td width = 30% >{}</td><td width = 30% >{}</td><td width=30%>{}</td><td align=right width=100%>{}</td></tr></table>"

    def paint(self, painter, option, index):
        model = index.model()
        row = index.row()
        action = model.data(model.index(row, 0, QtCore.QModelIndex()))
        api = model.data(model.index(row, 1, QtCore.QModelIndex()))
        module = model.data(model.index(row, 2, QtCore.QModelIndex()))

        doc = QtGui.QTextDocument()

        global ApiForm

        if len(ApiForm.regex_pattern) > 1:
            try:
                action = ApiForm.regex.sub(r'<b>\1</b>', action)
            except:
                pass
            try:
                api = ApiForm.regex.sub(r'<b>\1</b>', api)
            except:
                pass
        if api:
            api = api.lstrip("\t \n\r").split("\n")[0]

        document = self.template_str.format(action, api, module)
        doc.setHtml(document)

        painter.save()
        option.widget.style().drawControl(QtWidgets.QStyle.CE_ItemViewItem, option, painter)

        painter.translate(option.rect.left(), option.rect.top())
        clip = QtCore.QRectF(0, 0, option.rect.width(), option.rect.height())
        doc.drawContents(painter, clip)
        painter.restore()

    def sizeHint(self, option, index):
        if self.cached_size is None:
            self.initStyleOption(option, index)
            doc = QtGui.QTextDocument()
            document = self.template_str.format("action", "api", "description")
            doc.setHtml(document)
            doc.setTextWidth(option.rect.width())
            self.cached_size = QtCore.QSize(doc.idealWidth(), doc.size().height())
        return self.cached_size


# --------------------------------------------------------------------------


class ApiFilter(QtCore.QSortFilterProxyModel):
    def filterAcceptsRow__(self, sourceRow, sourceParent):
        # t1 = time.clock()
        r = self.filterAcceptsRow_(sourceRow, sourceParent)
        # t2 = time.clock()
        # global timing
        # timing += t2-t1
        # return r

    def filterAcceptsRow(self, sourceRow, sourceParent):
        regex = self.filterRegExp()
        if len(regex.pattern()) == 0:
            return True

        m = self.sourceModel()

        for i in range(2):  # search api name and doc
            if regex.indexIn(m.data(m.index(sourceRow, i, sourceParent))) != -1:
                return True
        return False


# --------------------------------------------------------------------------


class ApiPaletteForm_t(QtWidgets.QDialog):
    def mousePressEvent(self, event):

        event.ignore()
        event.accept()
        if not self.rect().contains(event.pos()):
            close()

    def select(self, row):
        idx = self.proxyModel.index(row, 0, QtCore.QModelIndex())
        self.lst.setCurrentIndex(idx)

    def on_text_changed(self):
        filter = self.filter.text()
        self.regex = re.compile("(%s)" % (re.escape(filter)), flags=re.IGNORECASE)
        self.regex_pattern = filter
        self.proxyModel.setFilterRegExp(
            QtCore.QRegExp(
                filter, QtCore.Qt.CaseInsensitive, QtCore.QRegExp.FixedString
            )
        )

        # self.lst.currentIndex()
        self.select(0)
        self.lst.viewport().update()

    def on_enter(self):
        self.report_action(self.lst.currentIndex())

    def report_action(self, index):
        if not index.isValid():
            return
        self.setResult(1)
        m = index.model()
        row = index.row()
        self.action_name = "%s.%s" % (m.data(m.index(row, 2)), m.data(m.index(row, 0)))
        global last_api_search
        last_api_search = self.filter.text()
        self.done(1)

    def focusOutEvent(self, event):
        pass

    # def event(self, event):
    #    return super(ApiPaletteForm_t, self).event(event)
    def __init__(self, parent=None, flags=None):
        """
        Called when the plugin form is created
        """
        # Get parent widget
        # self.parent = idaapi.PluginForm.FormToPyQtWidget(form)
        # super(ApiPaletteForm_t, self).__init__( parent, QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowTitleHint  )
        # super(ApiPaletteForm_t, self).__init__( parent, QtCore.Qt.Popup )
        # super(ApiPaletteForm_t, self).__init__( parent, QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint )
        super(ApiPaletteForm_t, self).__init__(parent, QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)

        self.setFocusPolicy(QtCore.Qt.ClickFocus)

        self.setWindowTitle("API Palette")
        self.resize(800, 500)

        # Create tree control
        self.lst = MyApiList()
        self.actions = list_api()
        self.action_name = None

        self.model = QtGui.QStandardItemModel(len(self.actions), 3)

        self.proxyModel = ApiFilter()
        self.proxyModel.setDynamicSortFilter(True)

        self.model.setHeaderData(0, QtCore.Qt.Horizontal, "api")
        self.model.setHeaderData(1, QtCore.Qt.Horizontal, "doc")
        self.model.setHeaderData(2, QtCore.Qt.Horizontal, "module")

        for row, i in enumerate(self.actions):
            self.model.setData(self.model.index(row, 0, QtCore.QModelIndex()), i[0])  # api name
            # first line of the doc
            doc = i[1].__doc__.lstrip().split('\n', 1)[0] if i[1].__doc__ else ''
            self.model.setData(self.model.index(row, 1, QtCore.QModelIndex()), doc)
            self.model.setData(self.model.index(row, 2, QtCore.QModelIndex()), i[2])  # module name

        self.proxyModel.setSourceModel(self.model)
        self.lst.setModel(self.proxyModel)

        global last_api_search

        self.filter = MyEdit(last_api_search)
        self.regex = re.compile("(%s)" % re.escape(last_api_search), flags=re.IGNORECASE)
        self.regex_pattern = last_api_search

        self.proxyModel.setFilterRegExp(
            QtCore.QRegExp(self.regex_pattern, QtCore.Qt.CaseInsensitive, QtCore.QRegExp.FixedString))

        self.filter.setMaximumHeight(30)
        self.filter.textChanged.connect(self.on_text_changed)
        self.filter.returnPressed.connect(self.on_enter)

        self.lst.clicked.connect(self.on_clicked)
        # self.lst.activated.connect(self.on_activated)

        self.lst.setSelectionMode(1)  # QtSingleSelection

        self.lst.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.lst.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.lst.setItemDelegate(api_delegate(self.lst))

        # self.lst.setSectionResizeMode( QtWidgets.QHeaderView.Fixed )

        self.filter.lst = self.lst
        self.lst.filter = self.filter
        self.filter.setStyleSheet('border: 0px solid black; border-bottom:0px;')
        self.lst.setStyleSheet('QListView{border: 0px solid black; background-color: #F0F0F0;}; ')

        # self.completer = QtWidgets.QCompleter(self.model)
        # self.completer.setCompletionMode(QtWidgets.QCompleter.InlineCompletion)
        # self.filter.setCompleter(self.completer)

        # Create layout
        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(self.filter)
        layout.addWidget(self.lst)

        # Populate PluginForm
        self.setLayout(layout)
        self.filter.setFocus()
        self.filter.selectAll()

        found = False
        if len(last_api) > 0:
            for row in range(self.proxyModel.rowCount()):
                idx = self.proxyModel.index(row, 0)
                if self.proxyModel.data(idx) == last_api:
                    self.lst.setCurrentIndex(idx)
                    found = True
                    break
        if not found:
            self.lst.setCurrentIndex(self.proxyModel.index(0, 0))

    def on_clicked(self, item):
        self.report_action(item)

    def on_activated(self, item):
        self.report_action(item)


# --------------------------------------------------------------------------
def AskForAPI():
    global ApiForm
    # todo change [x for x in QtWidgets.QApplication.topLevelWidgets() if repr(x).find('QMainWindow') != -1][0] into something non-crazy
    parent = [
        x
        for x in QtWidgets.QApplication.topLevelWidgets()
        if repr(x).find('QMainWindow') != -1
    ][0]
    ApiForm = ApiPaletteForm_t(parent)
    ApiForm.setModal(True)
    idaapi.disable_script_timeout()

    # ApiForm.setStyleSheet("background:transparent;");
    ApiForm.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
    # ApiForm.setAttribute(QtCore.Qt.WA_TranslucentBackground, True);

    result = None

    if ApiForm.exec_() == 1:
        global last_api
        last_api = ApiForm.action_name
        result = last_api

    del ApiForm
    return result


# --------------------------------------------------------------------------


# https://stackoverflow.com/questions/35762856/how-can-i-move-the-keyboard-cursor-focus-to-a-qlineedit/43383330#43383330
# QPoint pos(line_edit->width()-5, 5);
# QMouseEvent e(QEvent::MouseButtonPress, pos, Qt::LeftButton, Qt::LeftButton, 0);
# qApp->sendEvent(line_edit, &e);
# QMouseEvent f(QEvent::MouseButtonRelease, pos, Qt::LeftButton, Qt::LeftButton, 0);
# qApp->sendEvent(line_edit, &f);
def set_focus_on_qplaintextedit(control):
    r = control.cursorRect()
    pos = QtCore.QPoint(r.left(), r.top())
    # pos  = control.mapToGlobal(pos)
    ev = QtGui.QMouseEvent(
        PyQt5.QtGui.QMouseEvent.MouseButtonPress,
        pos,
        QtCore.Qt.LeftButton,
        QtCore.Qt.LeftButton,
        QtCore.Qt.NoModifier,
    )
    ev2 = QtGui.QMouseEvent(
        PyQt5.QtGui.QMouseEvent.MouseButtonRelease,
        pos,
        QtCore.Qt.LeftButton,
        QtCore.Qt.LeftButton,
        QtCore.Qt.NoModifier,
    )
    control.mousePressEvent(ev)
    control.mouseReleaseEvent(ev2)
    control.activateWindow()


class api_palette_ah(idaapi.action_handler_t):
    def __init__(self):
        idaapi.action_handler_t.__init__(self)

    def activate(self, ctx):
        global control
        control = QtWidgets.QApplication.focusWidget()
        action = AskForAPI()

        if action:
            r = repr(control)
            if "QPlainTextEdit" in r:
                control.insertPlainText(action + "(")
                set_focus_on_qplaintextedit(control)

            elif "QLineEdit" in r:
                control.insert(action + "(")
                control.setFocus()
            else:
                CLI_append(action)
                # control.insert(action + "(")
        return 1

    def update(self, ctx):
        return idaapi.AST_ENABLE_ALWAYS


api_palette_action_desc = idaapi.action_desc_t(
    "mb:api_palette",
    "API Palette",
    api_palette_ah(),
    "Shift+W",
    "Opens Sublime-like api palette.",
    -1,
)


def api_register_actions():
    idaapi.register_action(api_palette_action_desc)


def api_unregister_actions():
    idaapi.unregister_action(api_palette_action_desc.name)


def CLI_append(text):
    # hack, hackity, hack hack hack
    parent = [
        x
        for x in QtWidgets.QApplication.topLevelWidgets()
        if repr(x).find('QMainWindow') != -1
    ][0]
    output = parent.findChild(QtWidgets.QWidget, "Output window")
    ed = output.findChild(QtWidgets.QLineEdit)
    # ed.setText(ed.text()+text)
    ed.insert(text + "(")
    # ed.setFocus(7)
    ed.setFocus()


class APIPalettePlugin(idaapi.plugin_t):
    flags = idaapi.PLUGIN_FIX | idaapi.PLUGIN_HIDE
    comment = "Sublime-like api palette for IDA"
    help = "Sublime-like api palette"
    wanted_name = "api palette"
    wanted_hotkey = ""

    def init(self):
        addon = idaapi.addon_info_t()
        addon.id = "milan.bohacek.api_palette"
        addon.name = "API Palette"
        addon.producer = "Milan Bohacek"
        addon.url = "milan.bohacek+apipalette@gmail.com"
        addon.version = "7.00"
        idaapi.register_addon(addon)
        api_register_actions()

        return idaapi.PLUGIN_KEEP

    def term(self):
        api_unregister_actions()
        pass

    def run(self, arg):
        pass


def PLUGIN_ENTRY():
    return APIPalettePlugin()
