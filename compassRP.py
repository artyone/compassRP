from math import sqrt
import sys
import datetime
import pyqtgraph as pg
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
from itertools import count
import os


class MainWindow(QMainWindow):
    '''Класс главного окна'''

    def __init__(self):
        super().__init__()
        self.reciever: Reciever = Reciever()
        self.dataX: list[float] = list(range(10))
        self.dataY: list[float] = [0] * 10
        self.dataForX = count(10)
        self.maxDataSize = 50
        self.dataForFile = {'angle': [], 'x': [], 'y': []}
        self.portList = self.reciever.get_ports()
        self.setWindowTitle('КомпасРП вер. 1.1')
        self.initInterface()

    def initInterface(self):
        self.portMenu = QComboBox()
        self.portMenu.addItems([i.description for i in self.portList])

        self.initGraph()

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.plotWidget)
        splitter.addWidget(self.logAndCurrentLabel())

        self.compass = Compass()
        self.compass.hide()

        # Создаем главный макет окна и добавляем в него виджеты
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.portMenu)
        mainLayout.addWidget(splitter)
        mainLayout.addWidget(self.buttonBlock())
        mainLayout.addWidget(self.settingsWidget())

        # Создаем виджет, в который добавляем главный макет и устанавливаем его в качестве центрального виджета окна
        mainWidget = QWidget()
        mainWidget.setLayout(mainLayout)
        self.setCentralWidget(mainWidget)
        self.showMaximized()

    def initGraph(self):
        # Создаем виджет графика
        self.plotWidget = pg.PlotWidget()
        self.plotWidget.setBackground('black')
        # Создаем кривую для виджета графика
        self.curve = pg.PlotDataItem(self.dataX,
                                     self.dataY,
                                     pen=pg.mkPen('red', width=2))
        self.plotWidget.addItem(self.curve)
        self.plotWidget.setRange(yRange=list(range(-180, 180, 10)))
        self.plotWidget.setMouseEnabled(False)
        self.plotWidget.showGrid(x=True, y=True)

        # Создаем таймер для обновления графика и текущего времени
        self.timer = QTimer()
        self.timer.timeout.connect(self.updatePlotAndLogs)

    def buttonBlock(self):
        widget = QWidget()
        layout = QHBoxLayout()

        # Создаем кнопку для старта построения графика
        self.startButton = QPushButton('Start')
        self.startButton.clicked.connect(self.startPlotting)
        self.startButton.setFont(QFont('Arial', 14, QFont.Bold))
        # Создаем кнопку для остановки построения графика
        self.stopButton = QPushButton('Stop')
        self.stopButton.clicked.connect(self.stopPlotting)
        self.stopButton.setFont(QFont('Arial', 14, QFont.Bold))
        self.stopButton.hide()

        # Создаем кнопку показа графического компаса
        self.showCompassButton = QPushButton('Show compass')
        self.showCompassButton.clicked.connect(self.showCompass)

        # Создаем кнопку для открытия папки с логами
        self.openFolderFilesButton = QPushButton('Open files folder')
        self.openFolderFilesButton.clicked.connect(self.openFolderFiles)

        layout.addWidget(self.showCompassButton, 1)
        layout.addWidget(self.startButton, 5)
        layout.addWidget(self.stopButton, 5)
        layout.addWidget(self.openFolderFilesButton, 1)

        widget.setLayout(layout)
        return widget

    def logAndCurrentLabel(self):
        '''Виджет лога и текущих показаний'''
        widget = QWidget()
        layout = QHBoxLayout()
        # Создаем виджет лога
        self.logTextEdit = QTextEdit()
        self.logTextEdit.setReadOnly(True)
        # Создаем виджет показа текущего угла
        self.currentFilteredAngleLabel = QLabel('0')
        self.currentFilteredAngleLabel.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        self.currentFilteredAngleLabel.setStyleSheet("color: red;")
        self.currentFilteredAngleLabel.setFont(QFont("Arial", 45))

        self.currentRealAngleLabel = QLabel('0')
        self.currentRealAngleLabel.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.currentRealAngleLabel.setStyleSheet("color: black;")
        self.currentRealAngleLabel.setFont(QFont("Arial", 15))

        # self.currentMagneticDeviationLabel = QLabel('0')
        # self.currentMagneticDeviationLabel.setAlignment(Qt.AlignCenter)
        # self.currentMagneticDeviationLabel.setStyleSheet(
        #     "color: blue;")
        self.currentMagneticDeviationLabel.setFont(
            QFont("Arial", 45))

        layout.addWidget(self.logTextEdit, 5)
        layout.addWidget(self.currentFilteredAngleLabel, 3)
        layout.addWidget(self.currentRealAngleLabel, 1)
        layout.addWidget(self.currentMagneticDeviationLabel, 3)
        widget.setLayout(layout)
        return widget

    def settingsWidget(self):
        '''Виджеты настроек'''
        settingsWidget = QWidget()
        settingsLayout = QHBoxLayout()

        leftLayout = QFormLayout()
        self.frequencyReceiverLine = QLineEdit('100')
        self.frequencySaveFileLine = QLineEdit('10')
        leftLayout.addRow(
            'Частота опроса компаса(мс): ', self.frequencyReceiverLine)
        leftLayout.addRow(
            'Частота записи в файл: ', self.frequencySaveFileLine)

        rightLayout = QFormLayout()
        self.lengthFilterWindowLine = QLineEdit('50')
        self.filterAlphaLine = QLineEdit('0.1')
        rightLayout.addRow(
            'Длина окна фильтра: ', self.lengthFilterWindowLine)
        rightLayout.addRow(
            'Множитель фильтра: ', self.filterAlphaLine)

        settingsLayout.addLayout(leftLayout)
        settingsLayout.addLayout(rightLayout)
        settingsWidget.setLayout(settingsLayout)
        return settingsWidget

    def startPlotting(self):
        '''Метод старта отслеживания результатов'''

        if self.portMenu.currentIndex() == -1:
            self.stopPlotting()
            self.alert(QMessageBox.Warning, 'Устройство не выбрано или не найдено')
            return
        # Генерация имени файла, в который будет сохранены результаты
        self.fileName = (
            'data-' + str(datetime.datetime.now().strftime("%H-%M-%S")))
        self.clearDataForFile()
        # Создание экземпляра класса фильтрации
        self.lowPassFilter = LowPassFilter(
            int(self.lengthFilterWindowLine.text()), float(self.filterAlphaLine.text()))
        self.startButton.hide()
        self.stopButton.show()
        # Старт отслеживания
        self.timer.start(int(self.frequencyReceiverLine.text()))

    def stopPlotting(self):
        '''Остановка отслеживания'''
        self.timer.stop()  # Обновление каждую секунду
        self.startButton.show()
        self.stopButton.hide()


    def showCompass(self):
        self.compass.show()

    def updatePlotAndLogs(self):
        #TODO переделать метод, разделить создание на обновление данных, запись их в массивы и 
        # и отдельное построение графика и логов
        # Если данных больше, чем отслеживаемый прериод, удаляем лишние данные
        while len(self.dataX) > self.maxDataSize:
            self.dataX.pop(0)
            self.dataY.pop(0)
        # Получаем новые данные
        try:
            data = self.reciever.get_ungle(self.portMenu.currentIndex())
        except Exception:
            self.stopPlotting()
            self.alert(QMessageBox.Warning, 'Ошибка получения данных от компаса')
            return
        y = data['angle']
        #horizontalComponent = sqrt(data["x"]**2 + data["y"])
        self.dataX.append(next(self.dataForX))
        self.dataY.append(y)
        # Считаем среднее
        filteredY = self.lowPassFilter.filter(y)
        # Обновляем график
        self.curve.setData(self.dataX, self.dataY)
        # Обновляем графический компас, текущие показания, логи
        self.compass.updateDirection(filteredY)
        self.currentFilteredAngleLabel.setText(f'{filteredY:.3f}')
        self.currentRealAngleLabel.setText(f'{y:.3f}')
        #self.currentMagneticDeviationLabel.setText(f'{horizontalComponent:.3f}')
        self.updateTextLogs(y)
        self.updateFileLogs(y, data['x'], data['y'])

    def openFolderFiles(self):
        if not os.path.exists('data'):
            os.mkdir('data')
        os.startfile('data')

    def updateTextLogs(self, y):
        self.timestamp = datetime.datetime.now().strftime("%H.%M.%S.%f")[:-3]
        # Строка лога
        textLog = (
            f'<i>{self.timestamp}</i> : <font color="red"><b>{y:.4f}</b></font><br>')
        # Перемещаем курсор в конец текста
        self.logTextEdit.moveCursor(QTextCursor.End)
        # Добавляем строку лога в конец текста
        self.logTextEdit.insertHtml(textLog)
        if self.logTextEdit.toPlainText().count('\n') > 1000:  # Если количество строк превышает 1000
            # Удаляем первую строку (самую старую)
            self.logTextEdit.moveCursor(QTextCursor.Start)
            self.logTextEdit.moveCursor(
                QTextCursor.Down, QTextCursor.KeepAnchor)
            self.logTextEdit.insertPlainText('')
        self.logTextEdit.moveCursor(QTextCursor.End)

    def updateFileLogs(self, agnle, sourceX, sourceY):
        self.dataForFile['angle'].append(agnle)
        self.dataForFile['x'].append(sourceX)
        self.dataForFile['y'].append(sourceY)
        if len(self.dataForFile['angle']) < int(self.frequencySaveFileLine.text()):
            return
        try:
            if not os.path.exists('data'):
                os.mkdir('data')
            with open(f'data/{self.fileName}.csv', 'a') as file:
                if all(i >= 0 for i in self.dataForFile['angle']) or all(i <= 0 for i in self.dataForFile['angle']):
                    mean = sum(self.dataForFile['angle']) / len(self.dataForFile['angle'])
                else:
                    mean = self.dataForFile['angle'][-1]
                realAngle = self.dataForFile['angle'][-1]
                x, y = self.dataForFile['x'][-1], self.dataForFile['y'][-1]
                file.write(f'{self.timestamp},{mean},{realAngle},{x},{y}\n')
                self.clearDataForFile()
        except Exception as e:
            self.stopPlotting()
            self.alert(QMessageBox.Warning, str(e))
    
    def clearDataForFile(self):
        self.dataForFile = {'angle': [], 'x': [], 'y': []}

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
