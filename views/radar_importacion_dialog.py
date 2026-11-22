"""Entrada y vista previa; el servicio valida y PostgreSQL confirma la escritura."""

import csv
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from services.fuentes_tendencias import PAISES
from services.importacion_tendencias import TIKTOK_COLUMNAS
from views.tabla_paginada import TablaPaginada


class ImportacionRadarDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Importar datos reales')
        self.setMinimumWidth(660)
        layout = QVBoxLayout(self)
        nota = QLabel('TikTok: transcribe solo datos visibles que tengas permiso de usar. No hay scraping.\n'
                      'Google: descarga el CSV del gráfico original. Los archivos no se suben a terceros.')
        nota.setWordWrap(True)
        layout.addWidget(nota)
        form = QFormLayout()
        self.formato = QComboBox()
        self.formato.addItem('TikTok / Creative Center · observaciones en plantilla CSV', 'tiktok_manual')
        self.formato.addItem('Google Trends · Interés a lo largo del tiempo (CSV nativo)', 'google_timeline')
        self.formato.addItem('Google Trends · Consultas relacionadas TOP/RISING (CSV nativo)', 'google_related')
        self.formato.addItem('Google Trends · Tendencias actuales (CSV nativo)', 'google_now')
        form.addRow('Formato', self.formato)
        fila = QHBoxLayout()
        self.ruta = QLineEdit()
        elegir = QPushButton('Elegir CSV')
        elegir.clicked.connect(self._elegir)
        fila.addWidget(self.ruta, 1)
        fila.addWidget(elegir)
        form.addRow('Archivo', fila)
        self.pais = QComboBox()
        for codigo, nombre in PAISES.items():
            self.pais.addItem(nombre, codigo)
        form.addRow('País Google', self.pais)
        self.referencia = QLineEdit()
        self.referencia.setPlaceholderText('Consulta exacta de origen del CSV relacionado')
        form.addRow('Consulta de origen', self.referencia)
        self.periodo = QLineEdit()
        self.periodo.setPlaceholderText('Periodo exacto, p. ej. fechas de inicio / fin del gráfico')
        form.addRow('Periodo relacionadas', self.periodo)
        self.fecha = QLineEdit(date.today().isoformat())
        form.addRow('Fecha de observación', self.fecha)
        self.parcial = QCheckBox('Último punto temporal incompleto (excluir del cálculo)')
        self.parcial.setChecked(True)
        form.addRow(self.parcial)
        layout.addLayout(form)
        self.guia = QLabel()
        self.guia.setWordWrap(True)
        self.guia.setTextFormat(Qt.PlainText)
        layout.addWidget(self.guia)
        plantilla = QPushButton('Guardar plantilla TikTok vacía')
        plantilla.clicked.connect(self._plantilla)
        layout.addWidget(plantilla)
        self.formato.currentIndexChanged.connect(self._actualizar)
        self._actualizar()
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Ok).setText('Validar y previsualizar')
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)

    def _actualizar(self):
        formato = self.formato.currentData()
        google = formato != 'tiktok_manual'
        self.pais.setEnabled(google)
        for widget in (self.referencia, self.periodo):
            widget.setEnabled(formato == 'google_related')
        self.fecha.setEnabled(formato in ('google_related', 'google_now'))
        self.parcial.setEnabled(formato == 'google_timeline')
        self.guia.setText(
            'Plantilla: una fila por observación. tipo: producto/hashtag/consulta/tema/video. '
            'categoria: hogar/limpieza/juegos/peliculas/navidad/regalos/otros. pais: PE, US, MX, CL, CO, BR o ND. '
            'fecha: AAAA-MM-DD. metrica: reproducciones/publicaciones/popularidad/posicion/crecimiento/presencia. '
            'valor: cifra exacta sin separadores o vacío; conserva 1.2M o <1 en valor_original. '
            'periodo y contexto: mismos filtros, escala y ámbito para comparar fechas. '
            'url: enlace HTTPS de la evidencia TikTok. No asignes PE si no está confirmado.'
            if not google else
            'Google → Explorar → selecciona Perú y un solo término → descarga el gráfico correspondiente. '
            'El histórico verifica término/país del encabezado y conserva cada exportación en su propia escala. '
            'En Consultas relacionadas, país, consulta, periodo y fecha son declarados por ti; revisa que coincidan con el archivo.')

    def _elegir(self):
        ruta, _ = QFileDialog.getOpenFileName(self, 'CSV real', '', 'CSV (*.csv)')
        if ruta:
            self.ruta.setText(ruta)

    def _plantilla(self):
        ruta, _ = QFileDialog.getSaveFileName(self, 'Plantilla sin datos de ejemplo', 'observaciones_tiktok.csv', 'CSV (*.csv)')
        if ruta:
            try:
                with open(ruta, 'w', encoding='utf-8-sig', newline='') as archivo:
                    csv.writer(archivo).writerow(TIKTOK_COLUMNAS)
            except OSError:
                self.guia.setText('No se pudo guardar la plantilla. Revisa la ubicación y permisos.')

    def opciones(self):
        return dict(ruta=self.ruta.text().strip(), formato=self.formato.currentData(), pais=self.pais.currentData(),
                    referencia=self.referencia.text().strip(), periodo=self.periodo.text().strip(),
                    fecha=self.fecha.text().strip(), ultimo_parcial=self.parcial.isChecked())


def confirmar_importacion(parent, lote):
    dialogo = QDialog(parent)
    dialogo.setWindowTitle('Vista previa · todavía no guardada')
    dialogo.resize(1050, 600)
    layout = QVBoxLayout(dialogo)
    etiqueta = QLabel(f'{lote["archivo"]} · {len(lote["items"])} observaciones\nSHA256: {lote["sha256"]}')
    etiqueta.setTextFormat(Qt.PlainText)
    layout.addWidget(etiqueta)
    columnas = ('termino', 'tipo', 'pais', 'metrica', 'valor', 'etiqueta_original', 'observado_en', 'periodo', 'contexto', 'url')
    tabla = TablaPaginada(len(lote['items']), len(columnas))
    tabla.setHorizontalHeaderLabels(columnas)
    tabla.setEditTriggers(QTableWidget.NoEditTriggers)
    for fila, item in enumerate(lote['items']):
        for columna, clave in enumerate(columnas):
            valor = item.get(clave)
            tabla.setItem(fila, columna, QTableWidgetItem('No informado' if valor is None else str(valor)))
    tabla.resizeColumnsToContents()
    layout.addWidget(tabla)
    layout.addWidget(QLabel('Confirma solo si coinciden la fuente, el país, las fechas y las cifras. No se verifica su autenticidad automáticamente.'))
    botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
    botones.accepted.connect(dialogo.accept)
    botones.rejected.connect(dialogo.reject)
    layout.addWidget(botones)
    return dialogo.exec() == QDialog.Accepted
