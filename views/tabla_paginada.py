"""Paginación visual común: conserva datos, índices, filtros y acciones de la tabla."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QLabel, QPushButton, QTableWidget, QWidget


class TablaPaginada(QTableWidget):
    FILAS_POR_PAGINA = 7
    ALTO_PIE = 42

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pagina_actual = 0
        self.total_paginas = 1
        self._filtradas = set()
        self._filtro_cambiado = False
        self._actualizando = False
        self._limites_altura = None
        self._timer_paginacion = QTimer(self)
        self._timer_paginacion.setSingleShot(True)
        self._timer_paginacion.timeout.connect(self.actualizar_paginacion)
        self.pie_pagina = QWidget(self, objectName='tablePagination')
        self.pie_pagina.setStyleSheet('''
            QWidget#tablePagination { background: #ffffff; border-top: 1px solid #e1e3e6; }
            QWidget#tablePagination QLabel { color: #454b53; background: transparent; border: none; font-size: 10px; }
            QWidget#tablePagination QPushButton { color: #34383d; background: #ffffff;
                border: 1px solid #d7dade; border-radius: 5px; padding: 5px 9px; font-size: 10px; }
            QWidget#tablePagination QPushButton:hover { background: #fff0e5; }
            QWidget#tablePagination QPushButton:disabled { color: #989da4; background: #f2f3f5; }
        ''')
        layout = QHBoxLayout(self.pie_pagina)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        self.rango_pagina = QLabel()
        self.anterior = QPushButton('‹ Anterior')
        self.indicador_pagina = QLabel()
        self.siguiente = QPushButton('Siguiente ›')
        for boton in (self.anterior, self.siguiente):
            boton.setAutoDefault(False)
        self.anterior.clicked.connect(lambda: self.ir_a_pagina(self.pagina_actual - 1))
        self.siguiente.clicked.connect(lambda: self.ir_a_pagina(self.pagina_actual + 1))
        layout.addWidget(self.rango_pagina)
        layout.addStretch()
        layout.addWidget(self.anterior)
        layout.addWidget(self.indicador_pagina)
        layout.addWidget(self.siguiente)
        self.pie_pagina.hide()
        self.model().rowsInserted.connect(self._insertadas)
        self.model().rowsRemoved.connect(self._eliminadas)
        self.model().modelReset.connect(self._reiniciar)
        self.model().layoutChanged.connect(self._programar)
        self.model().dataChanged.connect(self._programar)
        self._programar()

    def _programar(self, *_):
        self._timer_paginacion.start(0)

    def _insertadas(self, _parent, primera, ultima):
        cantidad = ultima - primera + 1
        self._filtradas = {fila + cantidad if fila >= primera else fila for fila in self._filtradas}
        self._programar()

    def _eliminadas(self, _parent, primera, ultima):
        cantidad = ultima - primera + 1
        self._filtradas = {fila - cantidad if fila > ultima else fila
                           for fila in self._filtradas if not primera <= fila <= ultima}
        self._programar()

    def _reiniciar(self, *_):
        self._filtradas.clear()
        self.pagina_actual = 0
        self._programar()

    def setRowHidden(self, row, hide):
        # Un filtro externo no debe confundirse con las filas de otras páginas.
        if hide:
            self._filtradas.add(row)
        else:
            self._filtradas.discard(row)
        self.pagina_actual = 0
        self._filtro_cambiado = True
        super().setRowHidden(row, hide)
        self._programar()

    def _filas_disponibles(self):
        return [fila for fila in range(self.rowCount()) if fila not in self._filtradas]

    def actualizar_paginacion(self):
        if self._actualizando:
            return
        self._timer_paginacion.stop()
        self._actualizando = True
        try:
            filas = self._filas_disponibles()
            self.total_paginas = max(1, (len(filas) + self.FILAS_POR_PAGINA - 1) // self.FILAS_POR_PAGINA)
            seleccionada = self.currentRow()
            if not self._filtro_cambiado and self.selectionMode() != QAbstractItemView.NoSelection and seleccionada in filas:
                self.pagina_actual = filas.index(seleccionada) // self.FILAS_POR_PAGINA
            self._filtro_cambiado = False
            self.pagina_actual = max(0, min(self.pagina_actual, self.total_paginas - 1))
            self._mostrar_pagina(filas)
        finally:
            self._actualizando = False

    def _mostrar_pagina(self, filas):
        inicio = self.pagina_actual * self.FILAS_POR_PAGINA
        visibles = filas[inicio:inicio + self.FILAS_POR_PAGINA]
        conjunto = set(visibles)
        for fila in range(self.rowCount()):
            super().setRowHidden(fila, fila not in conjunto)
        if self.currentRow() >= 0 and self.currentRow() not in conjunto:
            if visibles and self.selectionMode() != QAbstractItemView.NoSelection:
                self.selectRow(visibles[0])
            else:
                self.clearSelection()
                self.setCurrentCell(-1, -1)
        self.rango_pagina.setText(f'{inicio + 1 if filas else 0}–{inicio + len(visibles)} de {len(filas)}')
        self.indicador_pagina.setText(f'Página {self.pagina_actual + 1} de {self.total_paginas}')
        self.anterior.setEnabled(self.pagina_actual > 0)
        self.siguiente.setEnabled(self.pagina_actual + 1 < self.total_paginas)
        mostrar_pie = len(filas) >= self.FILAS_POR_PAGINA
        self.pie_pagina.setVisible(mostrar_pie)
        if mostrar_pie:
            if self._limites_altura is None:
                self._limites_altura = (self.minimumHeight(), self.maximumHeight())
            altura_filas = sum(self.rowHeight(fila) for fila in visibles)
            altura_filas += (self.FILAS_POR_PAGINA - len(visibles)) * self.verticalHeader().defaultSectionSize()
            altura = (altura_filas + self.horizontalHeader().height() + self.ALTO_PIE
                      + self.horizontalScrollBar().sizeHint().height() + self.frameWidth() * 2)
            self.setFixedHeight(altura)
        elif self._limites_altura is not None:
            minimo, maximo = self._limites_altura
            self.setMinimumHeight(minimo)
            self.setMaximumHeight(maximo)
            self._limites_altura = None
        self.updateGeometries()

    def ir_a_pagina(self, pagina):
        self._timer_paginacion.stop()
        filas = self._filas_disponibles()
        self.total_paginas = max(1, (len(filas) + self.FILAS_POR_PAGINA - 1) // self.FILAS_POR_PAGINA)
        self.pagina_actual = max(0, min(pagina, self.total_paginas - 1))
        self._mostrar_pagina(filas)
        inicio = self.pagina_actual * self.FILAS_POR_PAGINA
        if filas and self.selectionMode() != QAbstractItemView.NoSelection:
            self.selectRow(filas[inicio])
        self.verticalScrollBar().setValue(0)

    def updateGeometries(self):
        super().updateGeometries()
        if not hasattr(self, 'pie_pagina'):
            return
        if not self.pie_pagina.isHidden():
            margenes = self.viewportMargins()
            self.setViewportMargins(margenes.left(), margenes.top(), margenes.right(), self.ALTO_PIE)
            borde = self.frameWidth()
            alto_barra = self.horizontalScrollBar().height() if self.horizontalScrollBar().isVisible() else 0
            ancho_barra = self.verticalScrollBar().width() if self.verticalScrollBar().isVisible() else 0
            self.pie_pagina.setGeometry(borde, self.height() - borde - alto_barra - self.ALTO_PIE,
                                       self.width() - borde * 2 - ancho_barra, self.ALTO_PIE)
            self.pie_pagina.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateGeometries()
