"""Runtime page widget: set up, check and remove the Newton runtime from the preferences."""
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QMessageBox
from . import runtime_setup
from .i18n import tr

MANUAL_GUIDE_URL = "https://github.com/d1rty-pixel/ingetrazo-newton/blob/main/docs/runtime-setup.md#method-c-manual"

_active = set()   # a running QThread must outlive a closed preferences dialog


class _Task(QThread):
    progress = Signal(str)
    done = Signal(bool, str)

    def __init__(self, job):
        super().__init__()
        self.job, self.cancelled = job, False

    def run(self):
        try:
            self.done.emit(True, self.job(self))
        except runtime_setup.SetupError as exc:
            self.done.emit(False, str(exc))
        except Exception as exc:
            self.done.emit(False, f"{type(exc).__name__}: {exc}")


def manual_link(sentence):
    """Fills the {link} of a translated sentence with the guide link; the URL is never translated."""
    link = f'<a href="{MANUAL_GUIDE_URL}">{tr("Manual installation guide")}</a>'
    return sentence.format(link=link)


def link_label(sentence):
    label = QLabel(manual_link(sentence));label.setWordWrap(True)
    label.setTextFormat(Qt.RichText);label.setOpenExternalLinks(True)
    return label


class RuntimeSetupBox(QWidget):
    def __init__(self, python_field):
        super().__init__()
        self.python_field, self.task = python_field, None
        box = QVBoxLayout(self);box.setContentsMargins(0,0,0,0)
        self.status = QLabel();self.status.setWordWrap(True)
        box.addWidget(self.status)
        # Check and the log belong to the Python environment setting, which exists in every build.
        self.verify = QPushButton(tr("Check runtime"));self.verify.clicked.connect(self.start_check)
        self.log = QPlainTextEdit();self.log.setReadOnly(True);self.log.setMaximumBlockCount(200);self.log.setMaximumHeight(110)
        self.log.hide();self.destroyed.connect(self.abandon)
        if not runtime_setup.RUNTIME_SETUP_ENABLED:
            self.status.hide()
            box.addWidget(link_label(tr("Automatic setup is disabled in this build. Follow the {link}.")))
            return
        row = QHBoxLayout();box.addLayout(row)
        self.setup = QPushButton(tr("Set up runtime"));self.setup.clicked.connect(self.start_setup)
        self.remove = QPushButton(tr("Remove runtime"));self.remove.clicked.connect(self.remove_runtime)
        self.cancel = QPushButton(tr("Cancel"));self.cancel.clicked.connect(self.cancel_task);self.cancel.hide()
        for button in (self.setup,self.remove,self.cancel):
            row.addWidget(button)
        row.addStretch()
        self.refresh()

    def refresh(self):
        path = runtime_setup.resolve()
        self.status.setText(tr("Interpreter: {path}").format(path=path) if path else tr("No runtime found."))
        self.remove.setEnabled(runtime_setup.is_managed())

    def busy(self,running):
        self.verify.setEnabled(not running)
        if not hasattr(self,"setup"):
            return
        for button in (self.setup,self.remove):
            button.setEnabled(not running)
        self.cancel.setVisible(running)
        if not running:
            self.refresh()

    def run(self,job,finished):
        self.log.clear();self.log.show();self.busy(True)
        task = self.task = _Task(job)
        task.progress.connect(self.log.appendPlainText)
        task.done.connect(finished)
        task.finished.connect(lambda:_active.discard(task))
        _active.add(task);task.start()

    def start_setup(self):
        folder = runtime_setup.runtime_dir()
        text = tr("Newton will download uv {uv} and Python {python}, install MuJoCo {mujoco} into {folder} and test it. Nothing else on your computer is changed. Continue?")
        answer = QMessageBox.question(self,tr("Set up runtime"),text.format(
            uv=runtime_setup.UV_VERSION,python=runtime_setup.PYTHON_VERSION,mujoco=runtime_setup.MUJOCO_VERSION,folder=folder))
        if answer != QMessageBox.Yes:
            return
        self.run(lambda task:runtime_setup.install(
            progress=lambda event:task.progress.emit(event["message"]),cancel=lambda:task.cancelled),self.setup_done)

    def setup_done(self,ok,message):
        self.busy(False)
        if ok:
            self.python_field.setText(message)
            self.log.appendPlainText(tr("Runtime ready."))
        else:
            self.log.appendPlainText(message)

    def start_check(self):
        python = self.python_field.text().strip() or runtime_setup.resolve()
        def job(task):
            ok,message = runtime_setup.check(python)
            if not ok:
                raise runtime_setup.SetupError(message)
            return message
        self.run(job,lambda ok,message:(self.busy(False),self.log.appendPlainText(message)))

    def remove_runtime(self):
        folder = runtime_setup.runtime_dir()
        text = tr("Delete Newton's own runtime folder {folder}?").format(folder=folder)
        current = self.python_field.text().strip()
        if current and not Path(current).is_relative_to(folder):
            text += "\n\n"+tr("The interpreter you use now, {path}, is not inside this folder and stays untouched.").format(path=current)
        if QMessageBox.question(self,tr("Remove runtime"),text) != QMessageBox.Yes:
            return
        try:
            runtime_setup.uninstall()
        except runtime_setup.SetupError as exc:
            self.log.show();self.log.appendPlainText(str(exc))
        else:
            if Path(self.python_field.text().strip()).is_relative_to(folder):
                self.python_field.setText("")
            self.log.show();self.log.appendPlainText(tr("Runtime removed."))
        self.refresh()

    def cancel_task(self):
        if self.task:
            self.task.cancelled = True

    def abandon(self,*_):
        for task in list(_active):
            task.cancelled = True
