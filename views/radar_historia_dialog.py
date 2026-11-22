"""Gráfico de una única serie comparable, sin rellenar huecos ni inventar puntos."""

from datetime import datetime

from PySide6.QtCharts import QChart, QChartView, QDateTimeAxis, QLineSeries, QScatterSeries, QValueAxis
from PySide6.QtCore import QDateTime, Qt, QTimeZone
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout

from services.importacion_tendencias import METRICAS
from services.analisis_senales import resumen_crecimiento
from views.tabla_paginada import TablaPaginada


class HistoriaRadarDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Historial real de la señal')
        self.resize(1000, 720)
        layout = QVBoxLayout(self)
        if not items:
            layout.addWidget(QLabel('No hay puntos guardados para esta serie.'))
        else:
            item = items[-1]
            titulo = QLabel(f'{item["termino"]} · {item["proveedor"]} · {item.get("pais") or "País no informado"}\n'
                            f'{METRICAS[item["metrica"]]} · {item["periodo"]}\nContexto: {item["contexto"]}')
            titulo.setTextFormat(Qt.PlainText)
            titulo.setWordWrap(True)
            layout.addWidget(titulo)
            resumen = QLabel(resumen_crecimiento(items))
            resumen.setWordWrap(True)
            layout.addWidget(resumen)
            chart = QChart()
            chart.setTitle('Observaciones en UTC · huecos y puntos parciales no se interpolan')
            chart.legend().hide()
            scatter = QScatterSeries()
            scatter.setMarkerSize(7)
            segmentos, segmento, valores, tiempos = [], None, [], []
            for punto in items:
                if punto.get('valor') is None or punto.get('parcial'):
                    segmento = None
                    continue
                tiempo = int(datetime.fromisoformat(punto['observado_en']).timestamp() * 1000)
                valor = punto['valor']
                if segmento is None:
                    segmento = QLineSeries()
                    segmentos.append(segmento)
                segmento.append(tiempo, valor)
                scatter.append(tiempo, valor)
                valores.append(valor)
                tiempos.append(tiempo)
            if valores:
                x = QDateTimeAxis()
                x.setFormat('dd/MM/yy HH:mm')
                x.setTitleText('Fecha de observación (UTC)')
                x.setTickCount(4)
                margen = 3600000 if min(tiempos) == max(tiempos) else 0
                x.setRange(QDateTime.fromMSecsSinceEpoch(min(tiempos) - margen, QTimeZone.utc()),
                           QDateTime.fromMSecsSinceEpoch(max(tiempos) + margen, QTimeZone.utc()))
                y = QValueAxis()
                y.setTitleText(METRICAS[item['metrica']])
                if item['metrica'] == 'interes_relativo':
                    y.setRange(0, 100)
                else:
                    margen_y = max((max(valores) - min(valores)) * .1, 1)
                    y.setRange(min(0, min(valores) - margen_y), max(valores) + margen_y)
                if item['metrica'] == 'posicion':
                    y.setReverse(True)
                chart.addAxis(x, Qt.AlignBottom)
                chart.addAxis(y, Qt.AlignLeft)
                for serie in [*segmentos, scatter]:
                    chart.addSeries(serie)
                    serie.attachAxis(x)
                    serie.attachAxis(y)
            else:
                chart.setTitle('Sin cifras exactas completas: consulta las observaciones originales en la tabla')
            grafico = QChartView(chart)
            grafico.setRenderHint(QPainter.Antialiasing)
            grafico.setMinimumHeight(300)
            layout.addWidget(grafico, 1)
            tabla = TablaPaginada(len(items), 6)
            tabla.setHorizontalHeaderLabels(('Fecha UTC', 'Valor', 'Original', 'Parcial', 'Archivo / procedencia', 'Fuente URL'))
            tabla.setEditTriggers(QTableWidget.NoEditTriggers)
            for fila, punto in enumerate(items):
                for columna, valor in enumerate((punto['observado_en'], punto.get('valor'), punto.get('etiqueta_original', ''),
                        'Sí' if punto.get('parcial') else 'No', punto.get('archivo', punto['origen']), punto['url'])):
                    tabla.setItem(fila, columna, QTableWidgetItem('Sin cifra' if valor is None else str(valor)))
            tabla.resizeColumnsToContents()
            layout.addWidget(tabla)
            nota = QLabel('Cada CSV de Google tiene su propia escala: nunca se concatenan exportaciones. '
                          'Una señal internacional o un hashtag no valida un producto ni demanda peruana. '
                          'La fecha de la última observación indica la antigüedad; no es un pronóstico.')
            nota.setWordWrap(True)
            layout.addWidget(nota)
        botones = QDialogButtonBox(QDialogButtonBox.Close)
        botones.rejected.connect(self.reject)
        layout.addWidget(botones)
