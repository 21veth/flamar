"""Pestana de importacion de ingresos de inventario."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QGridLayout, QLabel, QMessageBox

from views.import_shared import FileDropZone, FileInfoCard, ImportTab


MAX_FILE_BYTES = 10 * 1024 * 1024
FILE_FILTER = 'Archivos Excel (*.xlsx)'


@dataclass
class ArchivoIngresoSeleccionado:
    path: Path
    name: str
    extension: str
    size_bytes: int
    modified: datetime | None
    total: int = 0


class IngresoDropZone(FileDropZone):
    def __init__(self, parent=None):
        super().__init__(parent)
        for label in self.findChildren(QLabel):
            if label.text().startswith('Formatos soportados'):
                label.setText('Formato permitido: XLSX · Tamaño máximo sugerido: 10 MB')

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if urls and Path(urls[0].toLocalFile()).suffix.lower() == '.xlsx':
            event.acceptProposedAction()


class InventoryFileInfoCard(FileInfoCard):
    def set_data(self, data):
        super().set_data(data)
        self.record_count.setText('Pendiente de validación' if data is not None else '-')


class InventoryImportTab(ImportTab):
    TITLE = 'Registro de ingreso de productos'
    SUBTITLE = 'Importa la mercadería recibida por ZEYVER.'
    STEP_TITLES = ('Seleccionar archivo', 'Validar datos', 'Guardar')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.archivo = None
        self.validate_button.setText('Validar archivo')
        self.reset()

    def preview_headers(self):
        return ('Archivo',)

    def sample_rows(self):
        return ()

    def _build_top(self):
        grid = QGridLayout()
        grid.setSpacing(12)
        self.drop = IngresoDropZone()
        self.drop.file_dropped.connect(self.load_file)
        self.drop.clicked.connect(self.choose_file)
        self.details = InventoryFileInfoCard()
        self.details.replace_requested.connect(self.choose_file)
        self.details.delete_requested.connect(self.clear_file)
        grid.addWidget(self.drop, 0, 0)
        grid.addWidget(self.details, 0, 1)
        grid.setColumnStretch(0, 11)
        grid.setColumnStretch(1, 10)
        self.root.addLayout(grid)

    def reset(self):
        self.archivo = None
        self.data = None
        self.errors = []
        self.details.set_data(None)
        self.stepper.set_step(1)
        self.validate_button.setEnabled(False)
        self.process_button.setEnabled(False)
        self.process_button.setVisible(False)
        self.full_button.setEnabled(False)
        self.full_button.setVisible(False)
        self.preview.setVisible(False)
        self.preview_caption.clear()
        self.footer_message.setText('Selecciona un Excel de ingreso para comenzar.')

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            'Seleccionar Excel de ingreso',
            '',
            FILE_FILTER,
        )
        if path:
            self.load_file(path)

    def load_file(self, path):
        candidate = Path(path)
        if candidate.suffix.lower() != '.xlsx':
            QMessageBox.warning(
                self,
                'Formato no permitido',
                'Solo se aceptan archivos .xlsx.',
            )
            return

        try:
            stat = candidate.stat()
        except OSError as exc:
            QMessageBox.warning(self, 'No se pudo leer el archivo', str(exc))
            return

        if stat.st_size > MAX_FILE_BYTES:
            QMessageBox.warning(
                self,
                'Archivo demasiado grande',
                'El archivo supera el límite sugerido de 10 MB.',
            )
            return

        self.archivo = ArchivoIngresoSeleccionado(
            path=candidate,
            name=candidate.name,
            extension=candidate.suffix.lower(),
            size_bytes=stat.st_size,
            modified=datetime.fromtimestamp(stat.st_mtime),
        )
        self.details.set_data(self.archivo)
        self.validate_button.setEnabled(True)
        self.preview.setVisible(False)
        self.preview_caption.clear()
        self.footer_message.setText(
            f'Archivo listo: {candidate.name}. Pulsa "Validar archivo" para continuar.'
        )

    def clear_file(self):
        self.reset()

    def validate_file(self):
        if self.archivo is None:
            return
        QMessageBox.information(
            self,
            'Etapa 2 pendiente',
            'El archivo está listo. La validación de productos se implementará en la Etapa 2.',
        )

    def process_file(self):
        return None
