from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QPainter, QColor, QPolygon, QFont, QPen
from PyQt5.QtWidgets import QWidget


class Compass(QWidget):
    '''Класс графического компаса'''
    def __init__(self):
        super().__init__()
        self.current_direction = 0
        self.initUI()

    def initUI(self):
        self.setGeometry(0, 0, 350, 350)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.hide()

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()

    def drawWidget(self, qp):
        font = QFont('Serif', 10, QFont.Light)
        qp.setFont(font)
        qp.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # Set background color and draw circle
        qp.setBrush(QColor(15, 15, 15))
        qp.setPen(QPen(QColor(150, 150, 150), 2))
        qp.drawEllipse(50, 50, 250, 250)

        # Draw direction labels and lines
        qp.setPen(QPen(QColor(43, 43, 43), 5))
        qp.drawLine(175, 50, 175, 30)
        qp.drawText(170, 20, 'С')

        qp.drawLine(175, 300, 175, 320)
        qp.drawText(170, 340, 'Ю')

        qp.drawLine(50, 175, 30, 175)
        qp.drawText(5, 180, 'З')

        qp.drawLine(300, 175, 320, 175)
        qp.drawText(330, 180, 'В')

        qp.setRenderHint(QPainter.Antialiasing)

        qp.translate(175, 175)
        qp.rotate(-self.current_direction + 180)

        qp.setPen(QColor(255, 255, 255))
        arrow_polygon = QPolygon(
            [QPoint(-10, 0), QPoint(0, -20), QPoint(10, 0), QPoint(0, 70)])
        qp.setBrush(QColor(215, 0, 64))
        qp.drawPolygon(arrow_polygon)

    def updateDirection(self, angle):
        self.current_direction = angle
        self.update()
