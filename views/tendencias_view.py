"""Radar real: consulta autorizada, importación trazable e historial PostgreSQL."""

from datetime import datetime

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup, QComboBox, QDialog, QDialogButtonBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QSizePolicy, QVBoxLayout,
)

from config.radar import CATEGORIAS_RADAR
from controllers.tendencias_controller import TendenciasController
from services.fuentes_tendencias import PAISES, url_segura
from views.intelligence_redesign_views import _BaseIntelligenceView
from views.radar_importacion_dialog import ImportacionRadarDialog, confirmar_importacion
from views.radar_historia_dialog import HistoriaRadarDialog
from services.importacion_tendencias import METRICAS


def texto(contenido, nombre=None):
    label = QLabel(str(contenido))
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    label.setMinimumWidth(0)
    if nombre:
        label.setObjectName(nombre)
    return label


def abrir_url(url):
    if isinstance(url, str) and url_segura(url):
        QDesktopServices.openUrl(QUrl(url))


class TrendsView(_BaseIntelligenceView):
    TITLE = 'Radar de tendencias'
    SUBTITLE = 'Señales reales, procedencia e historial. Sin demanda inventada.'
    PAGE_ICON = '◎'

    def __init__(self, sesion, parent=None, controller=None):
        self._resultado = None
        self._iniciado = False
        self._ocupado = False
        self._categoria = None
        self._visibles = []
        self._conexion = False
        self._historial = True
        self._accion = None
        self._pendiente = None
        super().__init__(sesion, parent)
        self.controller = controller if controller is not None else TendenciasController(parent=self)
        self.controller.actualizado.connect(self._recibir)
        self.controller.fallo.connect(self._error)
        self.controller.ocupado.connect(self._cambiar_ocupado)
        self.setStyleSheet(self._styles() + '''
            QFrame#radarHero { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #151945,stop:1 #5036c8); border-radius:18px; }
            QLabel#heroEyebrow { color:#c2b9ff; font-size:10px; font-weight:700; }
            QLabel#heroTitle { color:white; font-size:29px; font-weight:800; }
            QLabel#heroCopy { color:#e0dcff; font-size:12px; }
            QPushButton#radarSearch { background:white; color:#4f31d5; border:0; border-radius:10px; padding:16px 24px; font-size:14px; font-weight:750; }
            QPushButton#radarSearch:hover { background:#f0eaff; }
            QPushButton#radarSearch:disabled { background:#d8d3eb; color:#7f76a4; }
            QPushButton#categoryChip { background:white; color:#65708e; border:1px solid #e0e4ef; border-radius:16px; padding:9px 14px; font-size:11px; }
            QPushButton#categoryChip:checked { background:#5b32f5; border-color:#5b32f5; color:white; }
            QPushButton#categoryChip:hover { border-color:#9e88f7; }
            QFrame#trendCard { background:white; border:1px solid #e0e4f1; border-radius:13px; }
            QLabel#cardIcon { background:#f1edff; color:#6a48e5; border-radius:10px; font-size:30px; }
            QLabel#cardTitle { color:#182348; font-size:16px; font-weight:750; }
            QLabel#cardMetric { color:#5835dc; font-size:17px; font-weight:750; }
            QLabel#cardSource { color:#65718f; font-size:10px; font-weight:600; }
            QLabel#cardNote { color:#7a85a1; font-size:10px; }
            QLabel#emptyTitle { color:#26345c; font-size:21px; font-weight:750; }
            QLabel#emptyIcon { color:#b4a6ee; font-size:54px; }
            QLabel#radarStatus { color:#6473a1; font-size:11px; }
            QPushButton#sourceLink { color:#5835dc; background:#f5f2ff; border:0; border-radius:7px; padding:9px; font-size:11px; font-weight:650; }
            QPushButton#helpLink { color:#6c7692; background:transparent; border:0; font-size:10px; text-align:left; padding:4px; }
            QProgressBar { background:#e9e3ff; border:0; border-radius:3px; max-height:4px; }
            QProgressBar::chunk { background:#7452f6; }
        ''')

    def _top_bar(self):
        bar = QFrame(objectName='topBar')
        fila = QHBoxLayout(bar)
        fila.setContentsMargins(20, 13, 20, 13)
        fila.addWidget(texto('ElMayorista  /  Inteligencia comercial', 'sectionSubtitle'))
        fila.addStretch()
        fila.addWidget(texto(self.sesion.usuario, 'accountName'))
        return bar

    def _build_content(self, layout):
        layout.setSpacing(18)
        hero = QFrame(objectName='radarHero')
        fila = QHBoxLayout(hero)
        fila.setContentsMargins(28, 26, 28, 26)
        copy = QVBoxLayout()
        copy.setSpacing(9)
        copy.addWidget(texto('PERÚ · OPORTUNIDADES PARA TU TIENDA', 'heroEyebrow'))
        copy.addWidget(texto('¿Qué se está buscando?', 'heroTitle'))
        copy.addWidget(texto('Consulta señales reales o importa observaciones de TikTok y Google.\nCada fuente, país y métrica conserva su propio historial.', 'heroCopy'))
        fila.addLayout(copy, 1)
        self.buscar_tendencias = QPushButton('Buscar tendencias', objectName='radarSearch')
        self.buscar_tendencias.setCursor(Qt.PointingHandCursor)
        self.buscar_tendencias.clicked.connect(lambda: self._ejecutar('buscar_radar'))
        fila.addWidget(self.buscar_tendencias, alignment=Qt.AlignVCenter)
        layout.addWidget(hero)

        herramientas = QHBoxLayout()
        self.importar_csv = QPushButton('Importar CSV real', objectName='sourceLink')
        self.importar_csv.clicked.connect(self._importar)
        herramientas.addWidget(self.importar_csv)
        for nombre, url in (
                ('Abrir TikTok Creative Center ↗', 'https://ads.tiktok.com/business/creativecenter/'),
                ('Google Trends · Perú ↗', 'https://trends.google.com/trends/explore?geo=PE&hl=es')):
            boton = QPushButton(nombre, objectName='sourceLink')
            boton.clicked.connect(lambda _=False, u=url: abrir_url(u))
            herramientas.addWidget(boton)
        herramientas.addStretch()
        layout.addLayout(herramientas)
        self.aviso = texto('', 'radarStatus')
        layout.addWidget(self.aviso)

        self.progreso = QProgressBar()
        self.progreso.setRange(0, 0)
        self.progreso.setTextVisible(False)
        self.progreso.hide()
        layout.addWidget(self.progreso)

        categorias = QGridLayout()
        categorias.setSpacing(8)
        self.grupo_categorias = QButtonGroup(self)
        self.grupo_categorias.setExclusive(True)
        self.botones_categoria = {}
        for indice, (clave, nombre) in enumerate([(None, 'Todas')] + [(c, v['nombre']) for c, v in CATEGORIAS_RADAR.items()]):
            boton = QPushButton(nombre, objectName='categoryChip')
            boton.setCheckable(True)
            boton.setChecked(clave is None)
            boton.setCursor(Qt.PointingHandCursor)
            boton.clicked.connect(lambda _marcado=False, c=clave: self._cambiar_categoria(c))
            self.grupo_categorias.addButton(boton)
            self.botones_categoria[clave] = boton
            categorias.addWidget(boton, indice // 4, indice % 4)
        layout.addLayout(categorias)
        filtros = QHBoxLayout()
        self.mercado = QComboBox()
        self.mercado.addItem('Todos · Perú primero', None)
        for codigo, nombre in PAISES.items():
            self.mercado.addItem(nombre, codigo)
        self.mercado.addItem('País no informado', 'ND')
        self.mercado.currentIndexChanged.connect(self._mostrar)
        filtros.addWidget(self.mercado)
        self.fuente = QComboBox()
        self.fuente.addItem('Todas las fuentes', None)
        self.fuente.addItem('Google', 'google')
        self.fuente.addItem('TikTok', 'tiktok')
        self.fuente.setMinimumWidth(155)
        self.fuente.currentIndexChanged.connect(self._mostrar)
        filtros.addWidget(self.fuente)
        filtros.addStretch()
        layout.addLayout(filtros)

        cabecera = QHBoxLayout()
        self.resumen = texto('Tu próxima oportunidad empieza aquí', 'sectionTitle')
        self.estado = texto('Pulsa el botón para buscar.', 'radarStatus')
        cabecera.addWidget(self.resumen, 1)
        cabecera.addWidget(self.estado)
        layout.addLayout(cabecera)
        self.tarjetas = QGridLayout()
        self.tarjetas.setSpacing(14)
        for columna in range(3):
            self.tarjetas.setColumnStretch(columna, 1)
        layout.addLayout(self.tarjetas)

        self.vacio = QFrame()
        vacio = QVBoxLayout(self.vacio)
        vacio.setContentsMargins(40, 28, 40, 40)
        icono = texto('◎', 'emptyIcon')
        icono.setAlignment(Qt.AlignCenter)
        self.vacio_titulo = texto('Descubre tu próxima oportunidad', 'emptyTitle')
        self.vacio_titulo.setAlignment(Qt.AlignCenter)
        self.vacio_texto = texto('Busca una vez y explora los resultados por categoría.', 'radarStatus')
        self.vacio_texto.setAlignment(Qt.AlignCenter)
        for widget in (icono, self.vacio_titulo, self.vacio_texto):
            vacio.addWidget(widget)
        layout.addWidget(self.vacio)

        pie = QHBoxLayout()
        self.conexiones = texto('Google: RSS Perú + CSV · TikTok: importación manual disponible', 'sectionSubtitle')
        pie.addWidget(self.conexiones, 1)
        ayuda = QPushButton('Sobre las fuentes y la conexión', objectName='helpLink')
        ayuda.clicked.connect(self._ayuda)
        pie.addWidget(ayuda)
        layout.addLayout(pie)
        layout.addStretch()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._iniciado:
            self._iniciado = True
            self._ejecutar('cargar_radar')  # Solo historial, nunca consume APIs al abrir.

    def _ejecutar(self, accion, **opciones):
        if not self._ocupado:
            self._accion = accion
            self.controller.ejecutar(accion, id_usuario=self.sesion.id_usuario, **opciones)

    def _importar(self):
        dialogo = ImportacionRadarDialog(self)
        if dialogo.exec() == QDialog.Accepted:
            self._ejecutar('previsualizar_radar', **dialogo.opciones())

    def _cambiar_ocupado(self, ocupado):
        self._ocupado = ocupado
        self.buscar_tendencias.setEnabled(not ocupado)
        self.importar_csv.setEnabled(not ocupado)
        buscando = ocupado and self._accion == 'buscar_radar'
        self.buscar_tendencias.setText('Buscando…' if buscando else 'Buscar tendencias')
        self.progreso.setVisible(ocupado)
        if buscando:
            self.estado.setText('Consultando las fuentes…')
        if not ocupado and self._pendiente:
            accion, opciones = self._pendiente
            self._pendiente = None
            QTimer.singleShot(0, lambda: self._ejecutar(accion, **opciones))

    def _recibir(self, respuesta):
        if 'preview' in respuesta:
            lote = respuesta['preview']
            if confirmar_importacion(self, lote):
                opciones = dict(respuesta['opciones_importacion'], huella_confirmada=lote['huella'])
                if self._ocupado:
                    self._pendiente = ('importar_radar', opciones)
                else:
                    self._ejecutar('importar_radar', **opciones)
            return
        if 'historia' in respuesta:
            HistoriaRadarDialog(respuesta['historia'], self).exec()
            return
        resultado = respuesta.get('radar')
        if resultado is not None:
            self._resultado = resultado
        self._conexion = respuesta.get('tiktok_configurado', False)
        self._historial = respuesta.get('historial', True)
        self.conexiones.setText('Google: RSS Perú + CSV · TikTok: API configurada (autorización sujeta a respuesta)'
                               if self._conexion else 'Google: RSS Perú + CSV · TikTok: importación manual; API sin configurar')
        avisos = [respuesta.get('mensaje', '')]
        if resultado:
            avisos.extend(resultado.get('advertencias', []))
            if 'recibidas_rss' in resultado:
                avisos.append(f'RSS Perú: {resultado["recibidas_rss"]} consultas recibidas. No es un catálogo de productos.')
        self.aviso.setText('\n'.join(a for a in avisos if a))
        if self._resultado:
            fecha = datetime.fromisoformat(self._resultado['consultado_en']).astimezone()
            nota = ' · resultados recientes reutilizados' if self._resultado.get('cache') else ''
            if self._resultado.get('advertencias'):
                nota += ' · algunas fuentes no respondieron'
            self.estado.setText(f'Panel cargado: {fecha:%d/%m %H:%M}{nota}. Fechas de señal en cada tarjeta.')
        self._mostrar()

    def _error(self, mensaje):
        self.estado.setText(mensaje)
        self.aviso.setText(mensaje)
        if not self._resultado:
            self.vacio_titulo.setText('No pudimos completar la búsqueda')
            self.vacio_texto.setText('Puedes volver a intentarlo. No se han generado resultados de ejemplo.')

    def _cambiar_categoria(self, categoria):
        self._categoria = categoria
        self._mostrar()

    def _mostrar(self, *_):
        while self.tarjetas.count():
            item = self.tarjetas.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        items = self._resultado.get('items', []) if self._resultado else []
        self._visibles = [i for i in items if (self._categoria is None or i['categoria'] == self._categoria)
                          and (self.fuente.currentData() is None or i['fuente'] == self.fuente.currentData())
                          and (self.mercado.currentData() is None or (i.get('pais') or 'ND') == self.mercado.currentData())]
        self._visibles.sort(key=lambda i: 0 if i.get('pais') == 'PE' else 1)
        for indice, item in enumerate(self._visibles):
            self.tarjetas.addWidget(self._tarjeta(item), indice // 3, indice % 3)
        self.vacio.setVisible(not self._visibles)
        if self._resultado:
            self.resumen.setText(f'{len(self._visibles)} resultados para explorar')
            self.vacio_titulo.setText('Todavía no hay resultados para esta selección')
            self.vacio_texto.setText('Importa observaciones reales de TikTok o CSV de Google Trends. '
                                    'El RSS peruano puede no incluir productos. La conexión de datos API de TikTok requiere autorización; '
                                    'no se rellenará este panel con ejemplos.')

    def _tarjeta(self, item):
        card = QFrame(objectName='trendCard')
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        contenido = QVBoxLayout(card)
        contenido.setContentsMargins(18, 18, 18, 18)
        contenido.setSpacing(10)
        categoria = CATEGORIAS_RADAR[item['categoria']]
        cabecera = QHBoxLayout()
        icono = texto(categoria['icono'], 'cardIcon')
        icono.setFixedSize(48, 48)
        icono.setAlignment(Qt.AlignCenter)
        icono.setToolTip('Icono de categoría, no fotografía del producto.')
        cabecera.addWidget(icono)
        cabecera.addWidget(texto(categoria['nombre'], 'cardSource'), 1)
        cabecera.addWidget(texto(f'{item["fuente"].title()} · {item.get("pais") or "país no informado"}', 'cardSource'))
        contenido.addLayout(cabecera)
        titulo = texto(item['termino'], 'cardTitle')
        titulo.setToolTip(item['termino'])
        titulo.setFixedHeight(66)
        contenido.addWidget(titulo)
        contenido.addWidget(texto(item['indicador'], 'cardSource'))
        valor = item.get('valor')
        if item['metrica'] == 'crecimiento':
            metrica = f'{valor:+,.0f}% reportado por la fuente' if valor is not None else (item.get('etiqueta_original') or 'Crecimiento sin cifra')
        elif item['metrica'] == 'interes_relativo':
            metrica = f'Interés relativo: {valor:g}/100' if valor is not None else 'Interés: ' + (item.get('etiqueta_original') or 'sin cifra')
        elif item['metrica'] == 'reproducciones':
            metrica = f'{valor:,} reproducciones' if valor is not None else 'Reproducciones (texto): ' + (item.get('etiqueta_original') or 'sin cifra')
        elif item['metrica'] == 'trafico_rss':
            metrica = 'Tráfico aprox.: ' + (item.get('etiqueta_original') or 'no informado')
        else:
            metrica = METRICAS.get(item['metrica'], item['metrica']) + ': ' + (f'{valor:g}' if valor is not None else (item.get('etiqueta_original') or 'sin cifra'))
        contenido.addWidget(texto(metrica, 'cardMetric'))
        if item['fuente'] == 'tiktok':
            nota = 'Señal de TikTok, no ventas ni demanda confirmada en Perú. Tipo: ' + item['tipo'] + '.'
        elif item['tipo'] == 'tema':
            nota = 'Tema de interés, no un producto validado ni demanda de merchandising.'
        else:
            nota = f'Consulta recibida de la fuente, relacionada con «{item["referencia"]}». No confirma ventas.'
        contenido.addWidget(texto(nota, 'cardNote'))
        contenido.addWidget(texto(item.get('proveedor', ''), 'cardSource'))
        if item.get('observado_en'):
            contenido.addWidget(texto('Observado: ' + item['observado_en'][:10], 'cardNote'))
        if item.get('parcial'):
            contenido.addWidget(texto('Último punto parcial · excluido del cálculo', 'cardNote'))
        contenido.addWidget(texto(item.get('periodo', ''), 'cardNote'))
        if item['fuente'] == 'tiktok' and item.get('publicado'):
            contenido.addWidget(texto('Publicado: ' + item['publicado'][:10], 'cardNote'))
        contenido.addStretch()
        abrir = QPushButton('Ver fuente ↗', objectName='sourceLink')
        abrir.setCursor(Qt.PointingHandCursor)
        abrir.clicked.connect(lambda _checked=False, url=item['url']: abrir_url(url))
        contenido.addWidget(abrir)
        if item.get('clave_serie'):
            historia = QPushButton('Ver histórico y crecimiento', objectName='sourceLink')
            historia.clicked.connect(lambda _=False, c=item['clave_serie']: self._ejecutar('historia_radar', clave_serie=c))
            contenido.addWidget(historia)
        return card

    def _ayuda(self):
        dialogo = QDialog(self)
        dialogo.setWindowTitle('Fuentes del radar')
        dialogo.setMinimumWidth(560)
        layout = QVBoxLayout(dialogo)
        informacion = (
            'Gratis y sin scraping: RSS oficial de Google Perú, CSV exportados por ti y observaciones manuales de TikTok. '
            'No hay proveedor comercial activo ni productos de ejemplo.\n\n'
            'Importar CSV real: primero valida y previsualiza; después confirma para guardar en PostgreSQL. '
            'La plantilla TikTok es del radar, no un exportador nativo universal. Si Creative Center ofrece descarga para tu cuenta, '
            'adapta únicamente datos cuyo uso esté permitido; si no, registra observaciones visibles. No atribuyas Perú por el idioma del contenido.\n\n'
            'Discovery API requiere una app aprobada y acceso autorizado. Hashtags: token de anunciante y advertiser_id; '
            'se solicita PE/7DAY sin cambiar de país si falla. Búsquedas: token Business con discovery.search.words y open_id; '
            'no informa país ni volumen, por lo que no se etiqueta como demanda peruana. Configurar no garantiza autorización.\n\n'
            'Historial: instala database/radar_datos_reales.sql. Cada archivo conserva SHA256, fuente, fecha y contexto. '
            'Los gráficos no mezclan métricas, países ni escalas de exportaciones Google. Los huecos, <1 y parciales no se estiman. '
            'No se crean productos en el catálogo ni compras. Guía completa: docs/radar_tendencias.md.'
        )
        if not self._historial:
            informacion += '\n\nEsta búsqueda no pudo guardarse en PostgreSQL. Los resultados actuales siguen disponibles en pantalla.'
        if self._resultado and self._resultado.get('advertencias'):
            informacion += '\n\nAvisos de la última consulta:\n' + '\n'.join(self._resultado['advertencias'])
        etiqueta = texto(informacion)
        etiqueta.setMaximumWidth(660)
        layout.addWidget(etiqueta)
        externo = QPushButton('Abrir Creator Search Insights de TikTok ↗', objectName='sourceLink')
        externo.clicked.connect(lambda: abrir_url('https://www.tiktok.com/csi'))
        layout.addWidget(externo)
        botones = QDialogButtonBox(QDialogButtonBox.Close)
        botones.rejected.connect(dialogo.reject)
        layout.addWidget(botones)
        dialogo.exec()
