"""High-fidelity, content-only inventory and sales views for Flamar Analytics.

Each page includes a ``shellHeader`` widget (date, notification, and account)
to match the design references. An integrating shell can hide it with
``view.shell_header.hide()`` without affecting the page title or content.
"""

import csv
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


INK = '#09142f'
MUTED = '#60708f'
PURPLE = '#5133f5'
GREEN = '#08a66c'
RED = '#ef334e'
ORANGE = '#ff9815'
BLUE = '#268df0'
BORDER = '#dfe5ee'


class IconBadge(QWidget):
    """Small painted icon tile used where the reference uses line icons."""

    def __init__(self, kind='bars', color=PURPLE, background='#f0edff', size=58, parent=None):
        super().__init__(parent)
        self.kind, self.color, self.background = kind, QColor(color), QColor(background)
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self.background)
        p.drawRoundedRect(self.rect(), 12, 12)
        p.setPen(QPen(self.color, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        w, h = self.width(), self.height()
        if self.kind == 'bars':
            p.setPen(Qt.NoPen); p.setBrush(self.color)
            for x, y, bh in ((.30, .60, .20), (.46, .46, .34), (.62, .30, .50)):
                p.drawRoundedRect(QRectF(w*x, h*y, w*.08, h*bh), 2, 2)
        elif self.kind in ('box', 'stock'):
            pts = [QPointF(w*.28,h*.37), QPointF(w*.50,h*.25), QPointF(w*.72,h*.37),
                   QPointF(w*.72,h*.65), QPointF(w*.50,h*.77), QPointF(w*.28,h*.65)]
            p.drawPolygon(pts); p.drawLine(pts[0], QPointF(w*.50,h*.50)); p.drawLine(pts[2], QPointF(w*.50,h*.50)); p.drawLine(QPointF(w*.50,h*.50), pts[4])
            if self.kind == 'stock':
                p.drawLine(QPointF(w*.40,h*.31), QPointF(w*.61,h*.43))
        elif self.kind == 'truck':
            p.drawRoundedRect(QRectF(w*.22,h*.37,w*.37,h*.25), 2, 2); p.drawRect(QRectF(w*.59,h*.45,w*.17,h*.17))
            p.drawEllipse(QPointF(w*.36,h*.68), 4, 4); p.drawEllipse(QPointF(w*.66,h*.68), 4, 4)
        elif self.kind == 'tag':
            p.drawRoundedRect(QRectF(w*.27,h*.30,w*.42,h*.35), 4, 4); p.drawEllipse(QPointF(w*.36,h*.38), 2, 2)
        elif self.kind == 'money':
            p.setPen(Qt.NoPen); p.setBrush(self.color); p.drawEllipse(QPointF(w*.50,h*.50), w*.22, h*.27)
            p.setPen(QPen(Qt.white, 2)); p.setFont(QFont('Segoe UI', 16, QFont.Bold)); p.drawText(self.rect(), Qt.AlignCenter, '$')
        elif self.kind == 'calendar':
            p.drawRoundedRect(QRectF(w*.27,h*.29,w*.46,h*.43), 3, 3); p.drawLine(QPointF(w*.27,h*.42),QPointF(w*.73,h*.42))
            p.drawLine(QPointF(w*.38,h*.24),QPointF(w*.38,h*.35)); p.drawLine(QPointF(w*.62,h*.24),QPointF(w*.62,h*.35))
        elif self.kind == 'trophy':
            p.drawRoundedRect(QRectF(w*.38,h*.26,w*.24,h*.29), 3, 3); p.drawArc(QRectF(w*.22,h*.29,w*.22,h*.22), 80*16, 210*16); p.drawArc(QRectF(w*.56,h*.29,w*.22,h*.22), -110*16, 210*16)
            p.drawLine(QPointF(w*.50,h*.55),QPointF(w*.50,h*.69)); p.drawLine(QPointF(w*.39,h*.70),QPointF(w*.61,h*.70))
        elif self.kind == 'megaphone':
            p.drawPolygon([QPointF(w*.25,h*.43),QPointF(w*.58,h*.31),QPointF(w*.58,h*.63),QPointF(w*.25,h*.53)]); p.drawLine(QPointF(w*.33,h*.54),QPointF(w*.39,h*.70)); p.drawLine(QPointF(w*.69,h*.36),QPointF(w*.77,h*.29)); p.drawLine(QPointF(w*.70,h*.57),QPointF(w*.79,h*.64))
        elif self.kind == 'upload':
            p.setPen(QPen(self.color, 4, Qt.SolidLine, Qt.RoundCap)); p.drawLine(QPointF(w*.50,h*.66),QPointF(w*.50,h*.34)); p.drawLine(QPointF(w*.50,h*.34),QPointF(w*.38,h*.46)); p.drawLine(QPointF(w*.50,h*.34),QPointF(w*.62,h*.46)); p.drawArc(QRectF(w*.23,h*.45,w*.54,h*.28), 0, 180*16)


class LineIcon(QWidget):
    """Compact shell icon that does not depend on symbol font coverage."""

    def __init__(self, kind, size=20, parent=None):
        super().__init__(parent); self.kind=kind; self.setFixedSize(size,size)

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setPen(QPen(QColor('#50617f'),1.6,Qt.SolidLine,Qt.RoundCap,Qt.RoundJoin)); p.setBrush(Qt.NoBrush); w=self.width(); h=self.height()
        if self.kind=='calendar':
            p.drawRoundedRect(QRectF(w*.18,h*.25,w*.64,h*.58),2,2); p.drawLine(QPointF(w*.18,h*.42),QPointF(w*.82,h*.42)); p.drawLine(QPointF(w*.34,h*.16),QPointF(w*.34,h*.32)); p.drawLine(QPointF(w*.66,h*.16),QPointF(w*.66,h*.32))
        elif self.kind=='bell':
            p.drawArc(QRectF(w*.25,h*.18,w*.50,h*.58),20*16,140*16); p.drawLine(QPointF(w*.25,h*.53),QPointF(w*.18,h*.72)); p.drawLine(QPointF(w*.18,h*.72),QPointF(w*.82,h*.72)); p.drawLine(QPointF(w*.82,h*.72),QPointF(w*.75,h*.53)); p.drawArc(QRectF(w*.42,h*.70,w*.16,h*.15),180*16,180*16)
            p.setPen(Qt.NoPen); p.setBrush(QColor(PURPLE)); p.drawEllipse(QPointF(w*.77,h*.22),3.2,3.2)
        elif self.kind=='chevron':
            p.drawLine(QPointF(w*.30,h*.42),QPointF(w*.50,h*.60)); p.drawLine(QPointF(w*.50,h*.60),QPointF(w*.70,h*.42))


class SalesChart(QWidget):
    def __init__(self, line=False, parent=None):
        super().__init__(parent)
        self.line = line
        self.values = [13, 15, 18, 20, 23, 25, 28, 31, 34, 29, 25, 19]
        self.setMinimumHeight(205)

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        area = self.rect().adjusted(45, 26, -18, -28)
        p.setFont(QFont('Segoe UI', 8)); p.setPen(QColor(MUTED))
        for i in range(5):
            y = area.bottom() - area.height()*i/4
            p.drawText(QRectF(0,y-8,38,16), Qt.AlignRight|Qt.AlignVCenter, '0' if i == 0 else f'{i*10}K')
            p.setPen(QPen(QColor('#e7ecf4'),1)); p.drawLine(area.left(),int(y),area.right(),int(y)); p.setPen(QColor(MUTED))
        labels = ('Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic')
        slot = area.width()/12; grad = QLinearGradient(0,area.top(),0,area.bottom()); grad.setColorAt(0,QColor('#6749fa')); grad.setColorAt(1,QColor('#765cf6'))
        points=[]
        for i,(value,label) in enumerate(zip(self.values,labels)):
            x=area.left()+slot*i+slot/2; bh=value/40*area.height()
            p.setPen(Qt.NoPen); p.setBrush(grad); p.drawRoundedRect(QRectF(x-slot*.31,area.bottom()-bh,slot*.62,bh),4,4)
            p.setPen(QColor(MUTED)); p.drawText(QRectF(area.left()+slot*i,area.bottom()+6,slot,18),Qt.AlignCenter,label)
            line_values = (8, 9, 11, 13, 16, 18, 20, 24, 27, 25, 23, 21)
            points.append(QPointF(x, area.bottom()-line_values[i]/40*area.height()))
        tip_x=area.left()+slot*8+slot/2; tip_y=max(2,area.bottom()-self.values[8]/40*area.height()-49); tip=QRectF(tip_x-32,tip_y,64,42)
        p.setPen(QPen(QColor('#d8e0ec'),1)); p.setBrush(QColor('#ffffff')); p.drawRoundedRect(tip,6,6); p.setPen(QColor(MUTED)); p.setFont(QFont('Segoe UI',7)); p.drawText(tip.adjusted(0,3,0,-20),Qt.AlignCenter,'Sep 2025' if self.line else 'Ago 2025'); p.setPen(QColor(INK)); p.setFont(QFont('Segoe UI',9,QFont.Bold)); p.drawText(tip.adjusted(0,18,0,-2),Qt.AlignCenter,'$ 32,400')
        if self.line:
            p.setPen(QPen(QColor('#4c28f4'),2)); p.setBrush(Qt.NoBrush); p.drawPolyline(points)
            for pt in points:
                p.setBrush(Qt.white); p.setPen(QPen(QColor('#4c28f4'),2)); p.drawEllipse(pt,4,4)


class Donut(QWidget):
    values = (35,22,15,12,10,6)
    colors = ('#5133f5','#3598ed','#ef5c99','#ff8b22','#ffbd31','#98a6bf')
    labels = ('Ropa','Tecnología','Colección K-pop','Decoración','Papelería','Accesorios')

    def __init__(self, total='25,430', parent=None):
        super().__init__(parent); self.total=total; self.setMinimumHeight(205)

    def paintEvent(self,event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        size=min(150,self.height()-24,self.width()*.48); ring=QRectF(10,(self.height()-size)/2,size,size)
        start=90*16; pen=QPen(); pen.setWidth(max(25,int(size*.19))); pen.setCapStyle(Qt.FlatCap)
        for value,color in zip(self.values,self.colors):
            span=-int(value/100*360*16); pen.setColor(QColor(color)); p.setPen(pen); p.drawArc(ring.adjusted(pen.width()/2,pen.width()/2,-pen.width()/2,-pen.width()/2),start,span); start+=span
        p.setPen(QColor(MUTED)); p.setFont(QFont('Segoe UI',9)); p.drawText(ring.adjusted(20,38,-20,-55),Qt.AlignCenter,'Total')
        p.setPen(QColor(INK)); p.setFont(QFont('Segoe UI',14,QFont.Bold)); p.drawText(ring.adjusted(10,57,-10,-35),Qt.AlignCenter,self.total)
        p.setPen(QColor(MUTED)); p.setFont(QFont('Segoe UI',8)); p.drawText(ring.adjusted(15,78,-15,-15),Qt.AlignCenter,'unidades')
        x=ring.right()+28; top=(self.height()-len(self.values)*25)/2
        for i,(label,value,color) in enumerate(zip(self.labels,self.values,self.colors)):
            y=top+i*25; p.setPen(Qt.NoPen); p.setBrush(QColor(color)); p.drawEllipse(QPointF(x,y+8),5,5)
            p.setPen(QColor(INK)); p.setFont(QFont('Segoe UI',8)); p.drawText(QRectF(x+14,y,self.width()-x-55,17),Qt.AlignVCenter,label); p.drawText(QRectF(self.width()-42,y,35,17),Qt.AlignRight|Qt.AlignVCenter,f'{value}%')


class DropZone(QFrame):
    file_dropped = Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent,objectName='dropZone'); self.setAcceptDrops(True)
    def dragEnterEvent(self,event:QDragEnterEvent):
        urls=event.mimeData().urls()
        if urls and Path(urls[0].toLocalFile()).suffix.lower() in {'.csv','.xlsx','.xls'}: event.acceptProposedAction()
    def dropEvent(self,event:QDropEvent):
        self.file_dropped.emit(event.mimeData().urls()[0].toLocalFile()); event.acceptProposedAction()


class BaseContentView(QWidget):
    def __init__(self,title,subtitle,greeting=None,parent=None):
        super().__init__(parent,objectName='corePage'); self.setStyleSheet(STYLES)
        root=QVBoxLayout(self); root.setContentsMargins(0,0,0,0)
        scroll=QScrollArea(objectName='coreScroll'); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.content=QWidget(objectName='coreContent'); self.content.setMinimumWidth(0)
        self.body=QVBoxLayout(self.content); self.body.setContentsMargins(22,16,22,18); self.body.setSpacing(12)
        self.body.addLayout(self._header(title,subtitle,greeting)); scroll.setWidget(self.content); root.addWidget(scroll)

    def _header(self,title,subtitle,greeting):
        row=QHBoxLayout(); copy=QVBoxLayout(); copy.setSpacing(2)
        copy.addWidget(QLabel(title,objectName='pageTitle'))
        if greeting: copy.addWidget(QLabel(greeting,objectName='greeting'))
        copy.addWidget(QLabel(subtitle,objectName='subtitle')); row.addLayout(copy); row.addStretch()
        self.shell_header=QWidget(objectName='shellHeader'); shell=QHBoxLayout(self.shell_header); shell.setContentsMargins(0,2,0,0); shell.setSpacing(13)
        date=QFrame(objectName='dateFrame'); date.setFixedWidth(242); dl=QHBoxLayout(date); dl.setContentsMargins(13,8,10,8); dl.addWidget(LineIcon('calendar',18)); dl.addWidget(QLabel('01/08/2025 - 31/08/2025',objectName='dateText'),1); dl.addWidget(LineIcon('chevron',14)); shell.addWidget(date)
        shell.addWidget(LineIcon('bell',24))
        avatar=QLabel('AA',objectName='topAvatar'); avatar.setAlignment(Qt.AlignCenter); avatar.setFixedSize(40,40); shell.addWidget(avatar)
        account=QVBoxLayout(); account.setSpacing(0); account.addWidget(QLabel('Administrador',objectName='accountName')); account.addWidget(QLabel('Administrador',objectName='accountRole')); shell.addLayout(account)
        shell.addWidget(QLabel('⌄',objectName='muted')); row.addWidget(self.shell_header,alignment=Qt.AlignTop); return row

    @staticmethod
    def card(): return QFrame(objectName='card')

    @staticmethod
    def metric(kind,value,label,change,color,bg,detail='vs. mes anterior',height=108):
        card=QFrame(objectName='card'); card.setFixedHeight(height); lay=QHBoxLayout(card); lay.setContentsMargins(14,12,14,12); lay.setSpacing(14)
        lay.addWidget(IconBadge(kind,color,bg,56)); text=QVBoxLayout(); text.setSpacing(1); text.addStretch(); text.addWidget(QLabel(value,objectName='metricValue')); text.addWidget(QLabel(label,objectName='metricLabel')); text.addStretch(); lay.addLayout(text,1)
        side=QVBoxLayout(); side.setSpacing(2); side.addStretch(); chip=QLabel(change,objectName='badChip' if 'Stock crítico' in label and '↑' in change else 'goodChip'); chip.setAlignment(Qt.AlignCenter); side.addWidget(chip); side.addWidget(QLabel(detail,objectName='smallMuted'),alignment=Qt.AlignRight); side.addStretch(); lay.addLayout(side); return card

    def metrics(self,items,height=108):
        grid=QGridLayout(); grid.setSpacing(10)
        for i,item in enumerate(items): grid.addWidget(self.metric(*item,height=height),0,i); grid.setColumnStretch(i,1)
        return grid

    @staticmethod
    def section(title,widget,action='',subtitle=''):
        card=QFrame(objectName='card'); lay=QVBoxLayout(card); lay.setContentsMargins(14,11,14,12); lay.setSpacing(7)
        top=QHBoxLayout(); titles=QVBoxLayout(); titles.setSpacing(0); titles.addWidget(QLabel(title,objectName='sectionTitle'))
        if subtitle: titles.addWidget(QLabel(subtitle,objectName='muted'))
        top.addLayout(titles); top.addStretch()
        if action: top.addWidget(QPushButton(action,objectName='linkButton'))
        lay.addLayout(top); lay.addWidget(widget,1); return card

    @staticmethod
    def table(headers,rows,height=210,numbered=False):
        if numbered: headers=('#',)+tuple(headers); rows=tuple((i+1,)+tuple(r) for i,r in enumerate(rows))
        table=QTableWidget(len(rows),len(headers),objectName='coreTable'); table.setHorizontalHeaderLabels(headers); table.verticalHeader().hide(); table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch); table.horizontalHeader().setMinimumSectionSize(52)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers); table.setSelectionMode(QAbstractItemView.NoSelection); table.setFocusPolicy(Qt.NoFocus); table.setShowGrid(False); table.setFixedHeight(height); table.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Fixed); table.verticalHeader().setDefaultSectionSize(31)
        for r,row in enumerate(rows):
            for c,val in enumerate(row):
                item=QTableWidgetItem(str(val)); item.setTextAlignment(Qt.AlignVCenter|(Qt.AlignLeft if c in (0,1) else Qt.AlignCenter)); table.setItem(r,c,item)
                if str(val) in ('Crítico','↓ 12%','↓ 8%'):
                    item.setForeground(QColor(RED)); item.setBackground(QColor('#ffeaed'))
                elif str(val) in ('Bajo','Alto','Medio'):
                    item.setForeground(QColor('#d46b00')); item.setBackground(QColor('#fff1df'))
                elif str(val)=='Óptimo' or str(val).startswith('↑'):
                    item.setForeground(QColor(GREEN)); item.setBackground(QColor('#e5f8ef'))
        return table


class DashboardView(BaseContentView):
    def __init__(self,parent=None):
        super().__init__('Dashboard','Aquí tienes un resumen del desempeño de tu negocio.',parent=parent)
        self.body.addLayout(self.metrics((
            ('bars','$ 25,430','Ventas del mes','↑ 12%',PURPLE,'#f0edff'),('money','$ 320,850','Ingresos estimados','↑ 8%',GREEN,'#e8f8f1'),
            ('stock','24','Productos con stock\ncrítico','↑ 33%',RED,'#ffedf0'),('megaphone','6','Campañas sugeridas','↑ 50%',ORANGE,'#fff5e5')),115)); self.body.addSpacing(6)
        top=QGridLayout(); top.setSpacing(10); sales=self.section('Ventas por mes   ⓘ',SalesChart(), 'Ventas'); donut=self.section('Categorías con mayor demanda',Donut()); seasons=self._seasons()
        for card in (sales,donut,seasons): card.setFixedHeight(324)
        top.addWidget(sales,0,0,1,2); top.addWidget(donut,0,2); top.addWidget(seasons,0,3); top.setColumnStretch(0,9); top.setColumnStretch(1,9); top.setColumnStretch(2,10); top.setColumnStretch(3,12); self.body.addLayout(top)
        lower=QGridLayout(); lower.setSpacing(10); stock=self._stock_alerts(); trends=self._trend_card(); promos=self._promos()
        for card in (stock,trends,promos): card.setFixedHeight(307)
        lower.addWidget(stock,0,0,1,2); lower.addWidget(trends,0,2); lower.addWidget(promos,0,3); lower.setColumnStretch(0,2); lower.setColumnStretch(1,2); lower.setColumnStretch(2,3); lower.setColumnStretch(3,3); self.body.addLayout(lower)

    def _seasons(self):
        box=QWidget(); lay=QVBoxLayout(box); lay.setContentsMargins(0,0,0,0); lay.setSpacing(7)
        for icon,title,date,status,copy in (('🎃','Halloween','01 - 31 de octubre','Faltan 32 días','Preparar inventario\ny promociones'),('🎄','Navidad','01 - 31 de diciembre','Faltan 93 días','Planificar surtido\ny campañas'),('🎓','Regreso a clases','01 - 30 de agosto','En curso','Aprovechar la demanda\nactual')):
            row=QFrame(objectName='miniRow'); rl=QHBoxLayout(row); rl.setContentsMargins(9,7,9,7); rl.addWidget(QLabel(icon,objectName='thumb')); txt=QVBoxLayout(); txt.addWidget(QLabel(title,objectName='rowTitle')); txt.addWidget(QLabel(date,objectName='muted')); rl.addLayout(txt,1); rt=QVBoxLayout(); rt.addWidget(QLabel(status,objectName='purpleChip' if status!='En curso' else 'goodChip')); rt.addWidget(QLabel(copy,objectName='muted')); rl.addLayout(rt); lay.addWidget(row)
        return self.section('Próximas temporadas   ⓘ',box,'Ver todas')

    def _stock_alerts(self):
        rows=(('🎧  Audífonos Bluetooth','8','Crítico','Reabastecer'),('🎒  Mochila escolar','12','Alto','Reabastecer'),('👕  Playera K-pop','15','Alto','Reabastecer'),('🎃  Decoración Halloween','20','Medio','Monitorear'),('📘  Cuaderno universitario','18','Medio','Monitorear'))
        return self.section('Alertas de abastecimiento   ⓘ',self.table(('Producto','Stock actual','Nivel de riesgo','Acción sugerida'),rows,245),'Ver todas')

    def _trend_card(self):
        box=QWidget(); lay=QVBoxLayout(box); lay.setContentsMargins(0,0,0,0); lay.setSpacing(6)
        for icon,title,copy,growth in (('👕','Guerreras K-pop','Aumento significativo en búsquedas\ny ventas en las últimas 4 semanas.','↑ 120%'),('🎃','Decoración Halloween','Crecimiento de demanda para la\ntemporada de octubre.','↑ 85%'),('🎄','Navidad','Incremento en interés de productos\nnavideños desde principios de mes.','↑ 60%')):
            row=QFrame(objectName='miniRow'); rl=QHBoxLayout(row); rl.addWidget(QLabel(icon,objectName='thumb')); tx=QVBoxLayout(); tx.addWidget(QLabel(title,objectName='rowTitle')); tx.addWidget(QLabel(copy,objectName='muted')); rl.addLayout(tx,1); rl.addWidget(QLabel(growth,objectName='goodChip'),alignment=Qt.AlignTop); lay.addWidget(row)
        return self.section('Tendencias detectadas   ⓘ',box,'Ver todas')

    def _promos(self):
        box=QWidget(); lay=QVBoxLayout(box); lay.setContentsMargins(0,0,0,0); lay.setSpacing(6)
        for icon,title,copy,priority in (('👕','Combo K-pop','Playera + póster + sticker\nPotencial de incremento en ventas: +35%','Alta prioridad'),('🎃','Descuento Halloween','20% en decoración seleccionada\nPotencial de incremento en ventas: +28%','Media prioridad'),('🎒','Paquete Regreso a clases','Mochila + cuaderno + estuche\nPotencial de incremento en ventas: +40%','Alta prioridad')):
            row=QFrame(objectName='miniRow'); rl=QHBoxLayout(row); rl.addWidget(QLabel(icon,objectName='thumb')); tx=QVBoxLayout(); tx.addWidget(QLabel(title,objectName='rowTitle')); tx.addWidget(QLabel(copy,objectName='muted')); rl.addLayout(tx,1); rl.addWidget(QLabel(priority,objectName='purpleChip'),alignment=Qt.AlignTop); lay.addWidget(row)
        return self.section('Promociones sugeridas   ⓘ',box,'Ver todas')


IMPORT_ROWS=(
    ('01/08/2025','Audífonos Bluetooth','Tecnología','12','35.00','45','TechSupply','Regreso a clases','Verano'),('01/08/2025','Mochila escolar','Accesorios','8','28.50','32','Mundo Escolar','Regreso a clases','Verano'),
    ('02/08/2025','Playera K-pop','Ropa','25','18.90','60','KStyle','K-pop','Verano'),('02/08/2025','Decoración Halloween','Decoración','40','12.00','120','DecoMundo','Halloween','Otoño'),('03/08/2025','Cuaderno universitario','Papelería','30','6.50','80','OfiPlus','Regreso a clases','Verano'),
    ('03/08/2025','Figura coleccionable','Colección K-pop','15','24.90','40','KStyle','K-pop','Verano'),('04/08/2025','Lámpara LED','Tecnología','10','22.00','25','TechSupply','Sin campaña','Todo el año'),('04/08/2025','Taza temática','Accesorios','18','9.90','70','DecoMundo','Día del Estudiante','Verano'),
    ('05/08/2025','Set de stickers','Papelería','50','4.50','200','OfiPlus','Regreso a clases','Verano'),('05/08/2025','Árbol navideño mini','Decoración','5','15.00','35','DecoMundo','Navidad','Invierno'))
IMPORT_HEADERS=('Fecha','Producto','Categoría','Cantidad','Precio (USD)','Stock actual','Proveedor','Campaña','Temporada')


class ImportDataView(BaseContentView):
    def __init__(self,parent=None):
        super().__init__('Importar datos','Carga y procesa archivos para integrarlos con tus análisis.',parent=parent); self.selected_path=None
        self.body.addLayout(self._types()); self.body.addWidget(self._stepper())
        top=QGridLayout(); top.setSpacing(10); top.addWidget(self._drop(),0,0); top.addWidget(self._details(),0,1); top.setColumnStretch(0,11); top.setColumnStretch(1,10); self.body.addLayout(top)
        self.body.addWidget(self._preview())

    def _types(self):
        grid=QGridLayout(); grid.setSpacing(10)
        for i,(kind,title,sub,color,bg) in enumerate((('bars','Ventas','Historial de ventas por producto',PURPLE,'#f0edff'),('stock','Inventario','Niveles de stock y movimientos',RED,'#ffedf0'),('money','Precios de proveedores','Precios y condiciones de compra',GREEN,'#e8f8f1'),('calendar','Catálogo estacional','Campañas, temporadas y eventos',BLUE,'#eaf3ff'))):
            card=QFrame(objectName='typeActive' if i==0 else 'card'); card.setFixedHeight(80); lay=QHBoxLayout(card); lay.addWidget(IconBadge(kind,color,bg,45)); tx=QVBoxLayout(); tx.addWidget(QLabel(title,objectName='typeTitle')); tx.addWidget(QLabel(sub,objectName='muted')); lay.addLayout(tx,1); grid.addWidget(card,0,i); grid.setColumnStretch(i,1)
        return grid

    def _stepper(self):
        card=self.card(); card.setFixedHeight(72); lay=QHBoxLayout(card); lay.setContentsMargins(14,10,14,10)
        for i,(title,sub) in enumerate((('Seleccionar archivo','Carga tu archivo en formato CSV o Excel'),('Validar datos','Revisa y corrige posibles errores'),('Procesar','Integra los datos al sistema')),1):
            num=QLabel(str(i),objectName='stepActive' if i==1 else 'step'); num.setAlignment(Qt.AlignCenter); num.setFixedSize(36,36); lay.addWidget(num); tx=QVBoxLayout(); tx.addWidget(QLabel(title,objectName='stepTitleActive' if i==1 else 'rowTitle')); tx.addWidget(QLabel(sub,objectName='muted')); lay.addLayout(tx)
            if i<3: line=QFrame(objectName='line'); line.setFixedHeight(1); lay.addWidget(line,1)
        return card

    def _drop(self):
        panel=DropZone(); panel.setFixedHeight(272); panel.file_dropped.connect(self._load_file); lay=QVBoxLayout(panel); lay.setSpacing(3); lay.addStretch(); lay.addWidget(IconBadge('upload',PURPLE,'#f8f7ff',60),alignment=Qt.AlignCenter); lay.addWidget(QLabel('Arrastra y suelta tu archivo aquí',objectName='uploadTitle'),alignment=Qt.AlignCenter); lay.addWidget(QLabel('o haz clic para seleccionar',objectName='muted'),alignment=Qt.AlignCenter)
        choose=QPushButton('Seleccionar archivo',objectName='secondaryButton'); choose.setFixedWidth(250); choose.clicked.connect(self._choose_file); lay.addWidget(choose,alignment=Qt.AlignCenter); lay.addWidget(QLabel('Formatos soportados: CSV, XLSX, XLS\nTamaño máximo: 50 MB',objectName='muted'),alignment=Qt.AlignCenter); lay.addStretch(); return panel

    def _details(self):
        card=self.card(); card.setFixedHeight(272); lay=QVBoxLayout(card); lay.setContentsMargins(14,11,14,11); head=QHBoxLayout(); head.addWidget(QLabel('Detalles del archivo',objectName='sectionTitle')); head.addStretch(); head.addWidget(QLabel('Archivo listo para validar',objectName='goodChip')); lay.addLayout(head)
        self.file_name=QLabel('ventas_agosto_2025.xlsx',objectName='detailValue'); self.file_type=QLabel('Excel (.xlsx)',objectName='detailValue'); self.file_size=QLabel('2.4 MB',objectName='detailValue'); self.record_count=QLabel('1,248',objectName='detailValue'); self.modified=QLabel('18/08/2025 10:24 a. m.',objectName='detailValue')
        for icon,name,value in (('▣','Nombre del archivo',self.file_name),('▤','Tipo de archivo',self.file_type),('●','Tamaño del archivo',self.file_size),('☷','Registros detectados',self.record_count),('□','Fecha de modificación',self.modified)):
            row=QFrame(objectName='detailRow'); rl=QHBoxLayout(row); rl.setContentsMargins(7,3,7,3); badge=QLabel(icon,objectName='detailIcon'); badge.setAlignment(Qt.AlignCenter); badge.setFixedSize(27,27); rl.addWidget(badge); rl.addWidget(QLabel(name,objectName='muted')); rl.addStretch(); rl.addWidget(value); lay.addWidget(row)
        return card

    def _preview(self):
        card=self.card(); lay=QVBoxLayout(card); lay.setContentsMargins(14,11,14,10); head=QHBoxLayout(); head.addWidget(QLabel('Vista previa de los datos   ⓘ',objectName='sectionTitle')); head.addWidget(QLabel('Se muestran los primeros 10 registros del archivo.',objectName='muted')); head.addStretch(); self.columns=QLabel('Columnas detectadas: 9',objectName='muted'); head.addWidget(self.columns); head.addWidget(QPushButton('↗   Vista completa',objectName='secondaryButton')); lay.addLayout(head)
        self.preview=self.table(IMPORT_HEADERS,IMPORT_ROWS,277,True); self.preview.verticalHeader().setDefaultSectionSize(24); lay.addWidget(self.preview); foot=QHBoxLayout(); foot.addWidget(QLabel('ⓘ   Si los datos no se muestran correctamente, revisa el formato del archivo o descarga la plantilla.',objectName='muted')); foot.addStretch(); cancel=QPushButton('Cancelar',objectName='secondaryButton'); cancel.clicked.connect(self._reset); foot.addWidget(cancel); validate=QPushButton('Validar datos',objectName='primaryButton'); validate.clicked.connect(lambda: validate.setText('Datos validados')); foot.addWidget(validate); lay.addLayout(foot); return card

    def _choose_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Seleccionar archivo de datos','','Archivos de datos (*.csv *.xlsx *.xls)')
        if path: self._load_file(path)

    def _load_file(self,path):
        file=Path(path)
        if not file.is_file() or file.stat().st_size>50*1024*1024: return
        headers,rows,total=IMPORT_HEADERS,[],0
        if file.suffix.lower()=='.csv':
            try:
                with file.open('r',encoding='utf-8-sig',newline='') as src:
                    reader=csv.reader(src); headers=tuple(next(reader,IMPORT_HEADERS))
                    for row in reader:
                        total+=1
                        if len(rows)<10: rows.append(tuple(row))
            except (OSError,UnicodeError,csv.Error): return
        elif file.suffix.lower()=='.xlsx':
            try:
                from openpyxl import load_workbook
                sheet=load_workbook(file,read_only=True,data_only=True).active; iterator=sheet.iter_rows(values_only=True); headers=tuple(str(v or '') for v in next(iterator,IMPORT_HEADERS))
                for row in iterator:
                    total+=1
                    if len(rows)<10: rows.append(tuple('' if v is None else str(v) for v in row))
            except (ImportError,OSError,ValueError,StopIteration): rows=list(IMPORT_ROWS); total=1248; headers=IMPORT_HEADERS
        else: rows=list(IMPORT_ROWS); total=1248
        self.selected_path=file; self.file_name.setText(file.name); self.file_type.setText(f'{file.suffix[1:].upper()} ({file.suffix.lower()})'); self.file_size.setText(f'{file.stat().st_size/1024/1024:.1f} MB'); self.record_count.setText(f'{total:,}'); self.modified.setText(datetime.fromtimestamp(file.stat().st_mtime).strftime('%d/%m/%Y %H:%M')); self._fill(headers,rows)

    def _fill(self,headers,rows):
        width=max(len(headers),max((len(r) for r in rows),default=0)); self.preview.setColumnCount(width+1); self.preview.setHorizontalHeaderLabels(('#',)+tuple(headers)+tuple(f'Campo {i+1}' for i in range(len(headers),width))); self.preview.setRowCount(len(rows))
        for r,row in enumerate(rows):
            self.preview.setItem(r,0,QTableWidgetItem(str(r+1)))
            for c in range(width): self.preview.setItem(r,c+1,QTableWidgetItem(str(row[c]) if c<len(row) else ''))
        self.columns.setText(f'Columnas detectadas: {width}')

    def _reset(self):
        self.selected_path=None; self.file_name.setText('ventas_agosto_2025.xlsx'); self.file_type.setText('Excel (.xlsx)'); self.file_size.setText('2.4 MB'); self.record_count.setText('1,248'); self.modified.setText('18/08/2025 10:24 a. m.'); self._fill(IMPORT_HEADERS,IMPORT_ROWS)


PRODUCTS=(('P001','🎧  Audífonos Bluetooth','Tecnología','8','20','TechSupply','7 días','$320.00','Crítico','⋮'),('P002','🎒  Mochila escolar','Papelería','12','25','EscolarMX','5 días','$280.00','Bajo','⋮'),('P003','👕  Playera K-pop','Ropa','45','20','KPopStore','10 días','$150.00','Óptimo','⋮'),('P004','🎃  Decoración Halloween','Decoración','6','30','DecoFest','12 días','$95.00','Crítico','⋮'),('P005','📘  Cuaderno universitario','Papelería','120','40','Papelería Pro','5 días','$22.00','Óptimo','⋮'),('P006','🎄  Decoración Navidad','Decoración','18','40','DecoFest','14 días','$110.00','Bajo','⋮'),('P007','🕶  Lentes de sol','Accesorios','32','20','ModaPlus','9 días','$85.00','Óptimo','⋮'),('P008','🧴  Botella reutilizable','Accesorios','75','30','EcoLife','6 días','$65.00','Óptimo','⋮'))


class ProductsView(BaseContentView):
    def __init__(self,parent=None):
        super().__init__('Productos e inventario','Gestiona tu catálogo de productos, niveles de inventario y abastecimiento.',parent=parent)
        self.body.addSpacing(9); self.body.addLayout(self.metrics((('box','248','Productos activos','↑ 12%',PURPLE,'#f0edff'),('stock','20','Stock crítico','↑ 33%',RED,'#ffedf0'),('truck','16','En pedido','↓ 20%',BLUE,'#eaf3ff'),('tag','18','Categorías','↑ 6%',ORANGE,'#fff5e5')),92)); self.body.addWidget(self._filters()); self.body.addWidget(self._listing())
        bottom=QGridLayout(); bottom.setSpacing(10); bottom.addWidget(self._seasonal(),0,0,1,3); bottom.addWidget(self._quick_alerts(),0,3,1,2); self.body.addLayout(bottom)

    def _filters(self):
        card=self.card(); card.setFixedHeight(91); lay=QHBoxLayout(card); lay.setContentsMargins(14,10,14,10); self.search=QLineEdit(); self.search.setPlaceholderText('Buscar por código, nombre o categoría...'); lay.addWidget(self._labeled('Buscar producto',self.search),2)
        for title,values in (('Categoría',('Todas','Tecnología','Ropa','Papelería')),('Estado',('Todos','Crítico','Bajo','Óptimo')),('Proveedor',('Todos','TechSupply','DecoFest')),('Temporada',('Todas','Halloween','Navidad'))):
            cb=QComboBox(); cb.addItems(values); lay.addWidget(self._labeled(title,cb),1)
        apply=QPushButton('Aplicar filtros',objectName='primaryButton'); apply.clicked.connect(self._filter); lay.addWidget(apply,alignment=Qt.AlignBottom); clear=QPushButton('Limpiar',objectName='secondaryButton'); clear.clicked.connect(lambda:self.search.clear()); lay.addWidget(clear,alignment=Qt.AlignBottom); return card

    @staticmethod
    def _labeled(title,widget):
        box=QWidget(); lay=QVBoxLayout(box); lay.setContentsMargins(0,0,0,0); lay.setSpacing(3); lay.addWidget(QLabel(title,objectName='fieldLabel')); lay.addWidget(widget); return box

    def _listing(self):
        table=self.table(('Código','Producto','Categoría','Stock actual','Stock mínimo','Proveedor','Tiempo de entrega','Precio compra','Estado','Acciones'),PRODUCTS,343); table.verticalHeader().setDefaultSectionSize(38)
        card=self.section('Listado de productos   ⓘ',table,'Agregar producto','248 productos en total'); foot=QHBoxLayout(); foot.addWidget(QLabel('Mostrando 1-8 de 248 productos   ⓘ',objectName='muted')); foot.addStretch()
        for text in ('‹','1','2','3','4','5','...','31','›'): foot.addWidget(QPushButton(text,objectName='pageActive' if text=='1' else 'pageButton'))
        foot.addStretch(); foot.addWidget(QLabel('Filas por página',objectName='muted')); combo=QComboBox(); combo.addItems(('8','16','24')); foot.addWidget(combo); card.layout().addLayout(foot); return card

    def _filter(self):
        term=self.search.text().casefold()
        table=self.findChild(QTableWidget)
        for r in range(table.rowCount()): table.setRowHidden(r,term not in ' '.join(table.item(r,c).text().casefold() for c in range(table.columnCount())))

    def _seasonal(self):
        rows=(('🎃  Decoración Halloween','Alta demanda en octubre','01 - 31 de octubre','6','30','Crítico'),('🎄  Decoración Navidad','Alta demanda en diciembre','01 - 31 de diciembre','18','40','Bajo'),('🎒  Mochilas escolares','Demanda en regreso a clases','01 - 30 de agosto','12','25','Bajo'))
        return self.section('Productos estacionales   ⓘ',self.table(('Producto','','Temporada','Stock actual','Stock mínimo','Estado'),rows,150),'Próximas temporadas','Productos relevantes por temporada')

    def _quick_alerts(self):
        rows=(('🎃  Decoración Halloween','Stock por debajo del mínimo','6 unidades  ›'),('🎒  Mochila escolar','Stock por debajo del mínimo','12 unidades  ›'),('📘  Cuaderno universitario','Se acerca a stock mínimo','18 unidades  ›'))
        return self.section('Alertas rápidas   ⓘ',self.table(('Producto','Alerta','Stock'),rows,150),'Ver todas')


class SalesView(BaseContentView):
    def __init__(self,parent=None):
        super().__init__('Análisis de ventas','Analiza el comportamiento histórico de tus ventas para identificar tendencias, productos clave y oportunidades de crecimiento.',parent=parent)
        self.body.addSpacing(22); self.body.addLayout(self.metrics((('bars','$ 25,430','Ventas totales','↑ 12%',PURPLE,'#f0edff'),('box','3,850','Unidades vendidas','↑ 8%',GREEN,'#e8f8f1'),('tag','$ 6.60','Ticket promedio','↑ 4%',RED,'#ffedf0'),('trophy','Ropa','Categoría líder','↑ 6%',ORANGE,'#fff5e5','35% de las ventas')),114)); self.body.addSpacing(7)
        charts=QGridLayout(); charts.setSpacing(10); evolution=self.section('Evolución de ventas   ⓘ',SalesChart(True),'●  Ventas (USD)     ○  Unidades vendidas        Ventas'); participation=self.section('Participación por categoría   ⓘ',Donut('$25,430'),'Ventas'); evolution.setFixedHeight(315); participation.setFixedHeight(315); charts.addWidget(evolution,0,0,1,3); charts.addWidget(participation,0,3,1,2); self.body.addLayout(charts)
        tables=QGridLayout(); tables.setSpacing(10); tables.addWidget(self._top_products(),0,0,1,3); tables.addWidget(self._season_sales(),0,3,1,2); self.body.addLayout(tables); self.body.addWidget(self._insight())

    def _top_products(self):
        rows=(('🎧  Audífonos Bluetooth','Tecnología','520','$ 4,160','↑ 18%'),('🎒  Mochila escolar','Regreso a clases','480','$ 3,840','↑ 12%'),('👕  Playera K-pop','Ropa','430','$ 3,225','↑ 25%'),('🎃  Decoración Halloween','Decoración','390','$ 2,730','↑ 40%'),('📘  Cuaderno universitario','Papelería','380','$ 2,280','↑ 15%'))
        return self.section('Productos más vendidos   ⓘ',self.table(('Producto','Categoría','Unidades vendidas','Ventas (USD)','Variación'),rows,207,True),'Ver todos')

    def _season_sales(self):
        rows=(('🎃  Halloween','$ 6,240','950','↑ 33%'),('🎄  Navidad','$ 5,120','780','↑ 20%'),('🎓  Regreso a clases','$ 4,860','720','↑ 28%'),('🎁  Campaña escolar','$ 3,950','610','↑ 15%'),('❤  San Valentín','$ 2,310','340','↓ 12%'),('☀  Verano','$ 2,150','320','↓ 8%'))
        table=self.table(('Temporada','Ventas (USD)','Unidades','Variación'),rows,207); table.verticalHeader().setDefaultSectionSize(27); return self.section('Ventas por temporada   ⓘ',table,'Ver todas')

    def _insight(self):
        card=QFrame(objectName='insight'); card.setFixedHeight(82); lay=QHBoxLayout(card); lay.addWidget(IconBadge('megaphone','#ffffff',PURPLE,48)); tx=QVBoxLayout(); tx.addWidget(QLabel('Insight de ventas',objectName='insightTitle')); copy=QLabel('Las ventas crecieron un 12% respecto al mes anterior, impulsadas principalmente por la temporada de Halloween (+33%) y la categoría de Ropa, que representa el 35% del total\nde ventas. Se recomienda aumentar inventario de productos de decoración y ropa para la próxima temporada.',objectName='muted'); copy.setWordWrap(True); tx.addWidget(copy); lay.addLayout(tx,1); lay.addWidget(QPushButton('Ver recomendaciones',objectName='secondaryButton')); return card


STYLES='''
QWidget#corePage,QWidget#coreContent,QScrollArea#coreScroll{background:#f7f9fd;color:#09142f;font-family:"Segoe UI Variable","Segoe UI";border:none}
QScrollBar:vertical{background:#eef2f7;width:8px}QScrollBar::handle:vertical{background:#cbd4e1;border-radius:4px;min-height:40px}QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0}
QLabel#pageTitle{font-size:30px;font-weight:800;color:#08132d}QLabel#greeting{font-size:20px;font-weight:750;color:#0d172d}QLabel#subtitle,QLabel#muted,QLabel#smallMuted{color:#60708f;font-size:11px}QLabel#smallMuted{font-size:9px}
QWidget#shellHeader{background:transparent}QFrame#dateFrame{background:white;border:1px solid #d5deea;border-radius:8px}QLabel#dateText{color:#20324f;font-size:11px}QLabel#topAvatar{background:#e4e0ff;color:#5133f5;border-radius:20px;font-weight:800}QLabel#accountName{color:#111827;font-size:12px;font-weight:750}QLabel#accountRole{font-size:10px;color:#60708f}
QFrame#card{background:white;border:1px solid #dfe5ee;border-radius:9px}QLabel#metricValue{font-size:23px;font-weight:800;color:#08122c}QLabel#metricLabel{font-size:11px;color:#34435e}QLabel#sectionTitle{font-size:15px;font-weight:750;color:#10182b}QLabel#rowTitle,QLabel#typeTitle{font-size:11px;font-weight:700;color:#111a2d}
QLabel#goodChip{background:#e4f8ee;color:#079557;border-radius:6px;padding:4px 7px;font-size:10px;font-weight:700}QLabel#badChip{background:#ffeaed;color:#e62e45;border-radius:6px;padding:4px 7px;font-size:10px;font-weight:700}QLabel#purpleChip{background:#f0edff;color:#4e31ed;border-radius:6px;padding:4px 7px;font-size:9px;font-weight:650}
QPushButton#primaryButton{background:#5133f5;color:white;border:none;border-radius:7px;padding:10px 18px;font-size:11px;font-weight:700}QPushButton#primaryButton:hover{background:#4125dd}QPushButton#secondaryButton{background:white;color:#4e31ed;border:1px solid #bdb4ff;border-radius:7px;padding:9px 17px;font-size:11px;font-weight:650}QPushButton#linkButton{background:transparent;color:#4e31ed;border:none;font-size:11px;font-weight:650;padding:4px}
QFrame#miniRow{background:white;border:1px solid #e5eaf1;border-radius:8px}QLabel#thumb{background:#f3f1ff;border-radius:8px;font-size:20px;padding:7px}
QTableWidget#coreTable{background:white;color:#273754;border:1px solid #e0e6ef;border-radius:7px;font-size:10px;selection-background-color:#f2efff}QTableWidget#coreTable::item{border-bottom:1px solid #e5eaf1;padding:3px}QTableWidget#coreTable QHeaderView::section{background:#f7f9fc;color:#12203a;border:none;border-bottom:1px solid #dfe5ee;padding:6px 3px;font-size:10px;font-weight:700}
QFrame#typeActive{background:white;border:1px solid #654cff;border-radius:8px}QFrame#dropZone{background:#fbfbff;border:1px dashed #6045ff;border-radius:10px}QLabel#uploadTitle{color:#111827;font-size:15px;font-weight:750}QLabel#stepActive{background:#5133f5;color:white;border-radius:18px;font-weight:700}QLabel#step{background:white;color:#172541;border:1px solid #bdc8d8;border-radius:18px;font-weight:700}QLabel#stepTitleActive{color:#5133f5;font-size:11px;font-weight:700}QFrame#line{background:#bdc8d8;border:none}QFrame#detailRow{border:none;border-bottom:1px solid #e3e8ef}QLabel#detailIcon{background:#f0edff;color:#5133f5;border-radius:7px;font-weight:700}QLabel#detailValue{font-size:10px;color:#111a2d;font-weight:650}
QLineEdit,QComboBox{background:white;color:#263752;border:1px solid #d4deea;border-radius:6px;padding:8px;font-size:10px;min-height:16px}QComboBox::drop-down{border:none;width:18px}QLabel#fieldLabel{font-size:9px;font-weight:700;color:#111a2d}QPushButton#pageButton,QPushButton#pageActive{min-width:25px;max-width:25px;min-height:25px;background:white;color:#354460;border:1px solid #d8e0ea;border-radius:5px;font-size:9px}QPushButton#pageActive{background:#5133f5;color:white;border:none}
QFrame#insight{background:#f6f3ff;border:1px solid #ded7ff;border-radius:9px}QLabel#insightTitle{color:#5031ed;font-size:12px;font-weight:750}
'''


__all__=['DashboardView','ImportDataView','ProductsView','SalesView']
