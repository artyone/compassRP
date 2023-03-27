from serial import Serial, EIGHTBITS
from serial.tools import list_ports
from serial.serialutil import SerialException
import numpy as np
from collections import deque

class LowPassFilter:
    def __init__(self, window_size, alpha):
        self.alpha = alpha
        self.window = deque(maxlen=window_size)
        self.prev_avg = None

    def filter(self, x):
        self.window.append(x)
        if all(i > 0 for i in self.window) or all(i > 0 for i in self.window):
            if len(self.window) == self.window.maxlen:
                    self.prev_avg = self.alpha * x + (1 - self.alpha) * self.prev_avg
            else:
                self.prev_avg = sum(self.window) / len(self.window)
        else: self.prev_avg = x
        return self.prev_avg

class Reciever():
    @staticmethod
    def get_ports() -> list:
        """Получение ком-портов компьютера"""
        ports_list: list = list_ports.comports()
        return ports_list

    @staticmethod
    def is_start(first_number: str, five_number: str) -> bool:
        if first_number == '0' and five_number == 'f':
            return True
        return False

    @staticmethod
    def get_numbers_from_bytes(bytes: bytes) -> list:
        numbers = bytes.hex().zfill(8)
        return numbers

    @classmethod
    def get_hex_data(cls, port_index):
        with Serial(bytesize=EIGHTBITS, timeout=0.1, baudrate=115200) as ser:
            ser.port = list(map(lambda x: x.device, cls.get_ports()))[port_index]
            ser.open()
            while True:
                byte_data = ser.read(4)
                hex_data = cls.get_numbers_from_bytes(byte_data)
                is_start = cls.is_start(hex_data[0], hex_data[4])
                while not is_start:
                    byte_data = byte_data[1:] + ser.read(1)
                    hex_data = cls.get_numbers_from_bytes(byte_data)
                    is_start = cls.is_start(hex_data[0], hex_data[4])
                return hex_data

    @classmethod
    def get_int_number(cls):
        for hex_data in cls.get_hex_data():
            return int(''.join(hex_data[1:4]), 16), int(''.join(hex_data[5:9]), 16)

    @classmethod
    def get_ungle(cls, port_index):
        hex_data = cls.get_hex_data(port_index)
        x = np.array(int(hex_data[1:4], 16)).astype(np.int16)
        y = np.array(int(hex_data[5:9], 16)).astype(np.int16)
        if x & 0x800:
            x = x + np.array(0xF000).astype(np.int16)
        if y & 0x800:
            y = y + np.array(0xF000).astype(np.int16)

        angle = np.arctan2(x, y)
        return np.rad2deg(angle)


# reciever = Reciever()
# while True:
#     angle = reciever.get_ungle()
#     print(angle)
