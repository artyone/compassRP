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
        self.data_x: list[float] = list(range(10))
        self.data_y: list[float] = [0] * 10
        self.data_for_x = count(10)
        self.max_data_size = 50
        self.data_for_file = []
        self.port_list = self.reciever.get_ports()
        self.setWindowTitle('КомпасРП вер. 1.0')
        self.initInterface()

    def initInterface(self):
        self.port_menu = QComboBox()
        self.port_menu.addItems([i.description for i in self.port_list])

        self.initGraph()

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.plot_widget)
        splitter.addWidget(self.logAndCurrentLabel())

        self.compass = Compass()
        self.compass.hide()

        # Создаем главный макет окна и добавляем в него виджеты
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.port_menu)
        main_layout.addWidget(splitter)
        main_layout.addWidget(self.buttonBlock())
        main_layout.addWidget(self.settingsWidget())

        # Создаем виджет, в который добавляем главный макет и устанавливаем его в качестве центрального виджета окна
        main_widget = QWidget()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        self.showMaximized()

    def initGraph(self):
        # Создаем виджет графика
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('black')
        # Создаем кривую для виджета графика
        self.curve = pg.PlotDataItem(self.data_x,
                                     self.data_y,
                                     pen=pg.mkPen('red', width=2))
        self.plot_widget.addItem(self.curve)
        self.plot_widget.setRange(yRange=list(range(-180, 180, 10)))

        # Создаем таймер для обновления графика и текущего времени
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot_and_logs)

    def buttonBlock(self):
        widget = QWidget()
        layout = QHBoxLayout()

        # Создаем кнопку для старта построения графика
        self.startButton = QPushButton('Start')
        self.startButton.clicked.connect(self.startPlotting)

        # Создаем кнопку для остановки построения графика
        self.stopButton = QPushButton('Stop')
        self.stopButton.clicked.connect(self.stopPlotting)
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
        layout.addWidget(self.openFolderFilesButton)

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
        self.currentLabel = QLabel('0')
        self.currentLabel.setAlignment(Qt.AlignCenter)
        self.currentLabel.setStyleSheet("color: red;") # устанавливаем красный цвет шрифта
        self.currentLabel.setFont(QFont("Arial", 30)) # устанавливаем шрифт размером 20
        layout.addWidget(self.logTextEdit, 5)
        layout.addWidget(self.currentLabel, 5)
        widget.setLayout(layout)
        return widget

    def settingsWidget(self):
        '''Виджеты настроек'''
        settings_widget = QWidget()
        settings_layout = QHBoxLayout()

        left_layout = QFormLayout()
        self.frequency_receiver = QLineEdit('100')
        self.frequency_save = QLineEdit('10')
        left_layout.addRow(
            'Частота опроса компаса(мс): ', self.frequency_receiver)
        left_layout.addRow(
            'Частота записи в файл: ', self.frequency_save)

        right_layout = QFormLayout()
        self.length_window_filter = QLineEdit('50')
        self.alpha_window_filter = QLineEdit('0.1')
        right_layout.addRow(
            'Длина окна фильтра: ', self.length_window_filter)
        right_layout.addRow(
            'Множитель фильтра: ', self.alpha_window_filter)

        settings_layout.addLayout(left_layout)
        settings_layout.addLayout(right_layout)
        settings_widget.setLayout(settings_layout)
        return settings_widget

    def startPlotting(self):
        '''Метод старта отслеживания результатов'''
        # Генерация имени файла, в который будет сохранены результаты
        self.name_file = (
            'data-' + str(datetime.datetime.now().strftime("%H-%M-%S")))
        # Создание экземпляра класса фильтрации
        self.lowPassFilter = LowPassFilter(
            int(self.length_window_filter.text()), float(self.alpha_window_filter.text()))
        self.startButton.hide()
        self.stopButton.show()
        # Старт отслеживания
        self.timer.start(int(self.frequency_receiver.text()))


    def stopPlotting(self):
        '''Остановка отслеживания'''
        self.timer.stop()  # Обновление каждую секунду
        self.startButton.show()
        self.stopButton.hide()
        self.data_for_file = []

    def showCompass(self):
        self.compass.show()

    def update_plot_and_logs(self):
        # Если данных больше, чем отслеживаемый прериод, удаляем лишние данные
        while len(self.data_x) > self.max_data_size:
            self.data_x.pop(0)
            self.data_y.pop(0)
        # Добавляем новые данные
        self.data_x.append(next(self.data_for_x))
        self.data_y.append(y)
        y = self.reciever.get_ungle(self.port_menu.currentIndex())
        # Считаем среднее
        filteredY = self.lowPassFilter.filter(y)
        # Обновляем график
        self.curve.setData(self.data_x, self.data_y)
        # Обновляем графический компас, текущие показания, логи
        self.compass.updateDirection(filteredY)
        self.currentLabel.setText(f'{filteredY:.3f}')
        self.updateTextLogs(y)

    def openFolderFiles(self):
        if not os.path.exists('data'):
            os.mkdir('data')
        os.startfile('data')

    def updateTextLogs(self, y):
        self.timestamp = datetime.datetime.now().strftime("%H.%M.%S.%f")[:-3]
        # Строка лога
        log_text = (
            f'<i>{self.timestamp}</i> : <font color="red"><b>{y:.4f}</b></font><br>')
        # Перемещаем курсор в конец текста
        self.logTextEdit.moveCursor(QTextCursor.End)
        # Добавляем строку лога в конец текста
        self.logTextEdit.insertHtml(log_text)
        if self.logTextEdit.toPlainText().count('\n') > 1000:  # Если количество строк превышает 1000
            # Удаляем первую строку (самую старую)
            self.logTextEdit.moveCursor(QTextCursor.Start)
            self.logTextEdit.moveCursor(
                QTextCursor.Down, QTextCursor.KeepAnchor)
            self.logTextEdit.insertPlainText('')
        self.logTextEdit.moveCursor(QTextCursor.End)

    def updateFileLogs(self, y):
        self.data_for_file.append(y)
        if len(self.data_for_file) >= int(self.frequency_save.text()):
            try:
                if not os.path.exists('data'):
                    os.mkdir('data')
                with open(f'data/{self.name_file}.csv', 'a') as file:
                    if all(i > 0 for i in self.data_for_file) or all(i > 0 for i in self.data_for_file):
                        mean = sum(self.data_for_file) / len(self.data_for_file)
                    else: mean = self.data_for_file[-1]
                    file.write(f'{self.timestamp},{mean}\n')
                    self.data_for_file = []
            except Exception as e:
                self.stopPlotting()
                self.alert(QMessageBox.Warning, str(e))

    @staticmethod
    def alert(type, message):
        msg_box = QMessageBox()
        msg_box.setIcon(type)
        msg_box.setWindowTitle("Предупреждение")
        msg_box.setText(message)
        msg_box.addButton(QMessageBox.Ok)
        msg_box.exec_()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
