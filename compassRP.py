import os
import sys
from itertools import count
from datetime import datetime
from collections import namedtuple as nt
import pyqtgraph as pg
from typing import NamedTuple, Iterable
from PyQt5.QtGui import QTextCursor, QFont
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow,
    QVBoxLayout, QWidget,
    QPushButton, QTextEdit,
    QSplitter, QLineEdit,
    QFormLayout, QMessageBox,
    QHBoxLayout, QComboBox,
    QLabel)
from receiver import Reciever, LowPassFilter
from compass import Compass


class MainWindow(QMainWindow):
    '''Класс главного окна'''
    DataFile = nt('DataFile', ['angle', 'x', 'y'])

    def __init__(self):
        super().__init__()
        self.reciever: Reciever = Reciever()
        self.dataForGraphX: list[float] = list(range(10))
        self.dataForGraphY: list[float] = [0] * 10
        self.dataForX: Iterable = count(10)
        self.maxDataSize: int = 50
        self.dataForFile: NamedTuple = self.DataFile([], [], [])
        self.portList: list = self.reciever.get_ports()
        self.setWindowTitle('КомпасРП вер. 1.2')
        self.initInterface()

    def initInterface(self):
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.graphBlock())
        splitter.addWidget(self.digitsBlock())
        self.compass = Compass()
        self.compass.hide()
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.portMenuBlock())
        mainLayout.addWidget(splitter)
        mainLayout.addWidget(self.buttonBlock())
        mainLayout.addWidget(self.settingsBlock())
        mainWidget = QWidget()
        mainWidget.setLayout(mainLayout)
        self.setCentralWidget(mainWidget)
        self.showMaximized()

        # Создаем таймер для обновления данных в интерфейсе
        self.timer = QTimer()
        self.timer.timeout.connect(self.updateInterface)

    def portMenuBlock(self):
        '''Блок выбора usb к которому подключен com'''
        widget = QWidget()
        layout = QHBoxLayout()
        self.portMenu = QComboBox()
        self.updatePortMenu()
        updateButton = QPushButton('Refresh')
        updateButton.clicked.connect(self.updatePortMenu)
        layout.addWidget(self.portMenu, 25)
        layout.addWidget(updateButton, 1)
        widget.setLayout(layout)
        return widget

    def updatePortMenu(self):
        self.portMenu.clear()
        self.portMenu.addItems(
            [i.description for i in self.portList]
        )

    def graphBlock(self):
        '''Блок графика'''
        # Создаем виджет графика
        plotWidget = pg.PlotWidget()
        plotWidget.setBackground('black')
        # Создаем кривую для виджета графика
        self.curve = pg.PlotDataItem(
            self.dataForGraphX,
            self.dataForGraphY,
            pen=pg.mkPen('red', width=2)
        )
        plotWidget.addItem(self.curve)
        plotWidget.setRange(
            yRange=list(range(-180, 180, 10))
        )
        plotWidget.setMouseEnabled(False)
        plotWidget.showGrid(x=True, y=True)
        return plotWidget

    def buttonBlock(self):
        '''Блок кнопок'''
        widget = QWidget()
        layout = QHBoxLayout()

        self.startButton = QPushButton('Start')
        self.startButton.clicked.connect(self.startProcess)
        self.startButton.setFont(QFont('Arial', 14, QFont.Bold))
        self.stopButton = QPushButton('Stop')
        self.stopButton.clicked.connect(self.stopProcess)
        self.stopButton.setFont(QFont('Arial', 14, QFont.Bold))
        self.stopButton.hide()
        # Создаем кнопку показа графического компаса
        self.showCompassButton = QPushButton('Show compass')
        self.showCompassButton.clicked.connect(self.showCompass)
        self.openFolderFilesButton = QPushButton('Open files folder')
        self.openFolderFilesButton.clicked.connect(self.openFolderFiles)

        layout.addWidget(self.showCompassButton, 1)
        layout.addWidget(self.startButton, 5)
        layout.addWidget(self.stopButton, 5)
        layout.addWidget(self.openFolderFilesButton, 1)

        widget.setLayout(layout)
        return widget

    def digitsBlock(self):
        '''Виджет лога и текущих показаний'''
        widget = QWidget()
        layout = QHBoxLayout()
        self.logTextEdit = QTextEdit()
        self.logTextEdit.setReadOnly(True)
        self.currentFilteredAngleLabel = QLabel('0')
        self.currentFilteredAngleLabel.setAlignment(
            Qt.AlignVCenter | Qt.AlignRight
        )
        self.currentFilteredAngleLabel.setStyleSheet("color: red;")
        self.currentFilteredAngleLabel.setFont(QFont("Arial", 45))
        self.currentRealAngleLabel = QLabel('0')
        self.currentRealAngleLabel.setAlignment(
            Qt.AlignVCenter | Qt.AlignLeft
        )
        self.currentRealAngleLabel.setStyleSheet("color: black;")
        self.currentRealAngleLabel.setFont(QFont("Arial", 15))
        layout.addWidget(self.logTextEdit, 5)
        layout.addWidget(self.currentFilteredAngleLabel, 3)
        layout.addWidget(self.currentRealAngleLabel, 1)
        widget.setLayout(layout)
        return widget

    def settingsBlock(self):
        '''Блок настроек'''
        settingsWidget = QWidget()
        settingsLayout = QHBoxLayout()

        leftLayout = QFormLayout()
        self.frequencyReceiverLine = QLineEdit('100')
        self.frequencySaveFileLine = QLineEdit('10')
        leftLayout.addRow(
            'Частота опроса компаса(мс): ', self.frequencyReceiverLine
        )
        leftLayout.addRow(
            'Частота записи в файл: ', self.frequencySaveFileLine
        )
        rightLayout = QFormLayout()
        self.lengthFilterWindowLine = QLineEdit('50')
        self.filterAlphaLine = QLineEdit('0.1')
        rightLayout.addRow(
            'Длина окна фильтра: ', self.lengthFilterWindowLine
        )
        rightLayout.addRow(
            'Множитель фильтра: ', self.filterAlphaLine
        )
        settingsLayout.addLayout(leftLayout)
        settingsLayout.addLayout(rightLayout)
        settingsWidget.setLayout(settingsLayout)
        return settingsWidget

    def startProcess(self):
        '''Метод старта отслеживания результатов'''
        if self.portMenu.currentIndex() == -1:
            self.stopProcess()
            self.alert(
                QMessageBox.Warning,
                'Устройство не выбрано или не найдено'
            )
            return
        # Генерация имени файла, в который будет сохранены результаты
        self.fileName = (
            'data-' + datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        )
        self.clearDataForFile()
        # Создание экземпляра класса фильтрации
        self.lowPassFilter = LowPassFilter(
            int(self.lengthFilterWindowLine.text()),
            float(self.filterAlphaLine.text())
        )
        self.startButton.hide()
        self.stopButton.show()
        # Старт отслеживания
        self.timer.start(
            int(self.frequencyReceiverLine.text()))

    def stopProcess(self):
        '''Остановка отслеживания'''
        self.timer.stop()
        self.startButton.show()
        self.stopButton.hide()

    def showCompass(self):
        self.compass.show()

    def updateInterface(self):
        '''Метод обновления элементов интерфейса'''
        data: NamedTuple = self.getCurrentData()
        if not data:
            return
        # Обновляем график
        self.updateGraph()
        filteredAngle = self.lowPassFilter.filter(data.angle)
        # Обновляем графический компас, текущие показания, логи
        self.compass.updateDirection(filteredAngle)
        self.currentFilteredAngleLabel.setText(
            f'{filteredAngle:.3f}'
        )
        self.currentRealAngleLabel.setText(
            f'{data.angle:.3f}'
        )
        # self.currentMagneticDeviationLabel.setText(f'{horizontalComponent:.3f}')
        self.updateTextLogs(data.angle)
        self.writeFileLogs(data.angle, data.x, data.y)

    def getCurrentData(self):
        '''Метод получения текущих данных'''
        # Если данных больше, чем отслеживаемый прериод, удаляем лишние данные
        while len(self.dataForGraphX) > self.maxDataSize:
            self.dataForGraphX.pop(0)
            self.dataForGraphY.pop(0)
        # Получаем новые данные
        try:
            data = self.reciever.get_angle(
                self.portMenu.currentIndex()
            )
            # data = self.reciever.get_fake_angle()
        except Exception as e:
            self.stopProcess()
            self.alert(QMessageBox.Warning, str(e))
            return False
        # horizontalComponent = sqrt(data["x"]**2 + data["y"])
        self.dataForGraphX.append(next(self.dataForX))
        self.dataForGraphY.append(data.angle)
        return data

    def updateGraph(self):
        self.curve.setData(self.dataForGraphX, self.dataForGraphY)

    def openFolderFiles(self):
        if not os.path.exists('data'):
            os.mkdir('data')
        os.startfile('data')

    def updateTextLogs(self, y):
        self.timestamp = datetime.now().strftime("%Y.%m.%d.%H.%M.%S.%f")[:-3]
        # Строка лога
        textLog = (
            f'<i>{self.timestamp}</i> : <font color="red"><b>{y:.4f}</b></font><br>'
        )
        # Перемещаем курсор в конец текста
        self.logTextEdit.moveCursor(QTextCursor.End)
        # Добавляем строку лога в конец текста
        self.logTextEdit.insertHtml(textLog)
        # Если количество строк превышает 1000
        if self.logTextEdit.toPlainText().count('\n') > 1000:
            # Удаляем первую строку (самую старую)
            self.logTextEdit.moveCursor(QTextCursor.Start)
            self.logTextEdit.moveCursor(
                QTextCursor.Down, QTextCursor.KeepAnchor)
            self.logTextEdit.insertPlainText('')
        self.logTextEdit.moveCursor(QTextCursor.End)

    def writeFileLogs(self, currentAngle, sourceX, sourceY) -> None:
        '''Запись лога в файл'''
        self.dataForFile.angle.append(currentAngle)
        self.dataForFile.x.append(sourceX)
        self.dataForFile.y.append(sourceY)
        if len(self.dataForFile.angle) < int(self.frequencySaveFileLine.text()):
            return
        try:
            if not os.path.exists('data'):
                os.mkdir('data')
            with open(f'data/{self.fileName}.csv', 'a') as file:
                if self.isSameSignAngles:
                    mean = (
                        sum(self.dataForFile.angle) /
                        len(self.dataForFile.angle)
                    )
                else:
                    mean = self.dataForFile.angle[-1]
                realAngle = self.dataForFile.angle[-1]
                x, y = self.dataForFile.x[-1], self.dataForFile.y[-1]
                file.write(f'{self.timestamp},{mean},{realAngle},{x},{y}\n')
                self.clearDataForFile()
        except Exception as e:
            self.stopProcess()
            self.alert(QMessageBox.Warning, str(e))

    def clearDataForFile(self):
        self.dataForFile = self.DataFile([], [], [])

    @staticmethod
    def isSameSignAngles(dataForFile: NamedTuple) -> bool:
        allPlus = all(i >= 0 for i in dataForFile.angle)
        allMinus = all(i <= 0 for i in dataForFile.angle)
        return allPlus or allMinus

    @staticmethod
    def alert(type, message):
        msgBox = QMessageBox()
        msgBox.setIcon(type)
        msgBox.setWindowTitle("Предупреждение")
        msgBox.setText(message)
        msgBox.addButton(QMessageBox.Ok)
        msgBox.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec_())
