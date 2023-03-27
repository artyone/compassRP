from serial import Serial, EIGHTBITS
from serial.tools import list_ports
from serial.serialutil import SerialException
from random import choice
from time import sleep
import numpy as np


class VirtualSender():

    data: list = [0x1F1C, 0x1A3C, 0x7510, 0x1000]

    @staticmethod
    def get_ports() -> list:
        """Получение ком-портов компьютера"""
        ports_list: list = list_ports.comports()
        return ports_list

    def start_spam(self) -> None:
        with Serial(bytesize=EIGHTBITS, write_timeout=0.1016) as ser:
            ser.port = list(map(lambda x: x.device, self.get_ports()))[0]
            while True:
                try:
                    ser.open()
                    command: bytes = choice(
                        self.data).to_bytes(4, byteorder='big')
                    ser.write(command)
                    print(command)
                    ser.close()
                    sleep(0.5)
                except SerialException:
                    sleep(0.33)
                    continue

                # answer = ser.read(4)
                # while answer:
                #     print(hex(int.from_bytes(answer, byteorder='big')))
                #     answer = ser.read(4)


# sender = VirtualSender()
# print(sender.get_ports())
# sender.start_spam()

import numpy as np

def moving_average(data, weights):
    weights = weights / weights.sum()
    sma = np.convolve(data, weights, mode='valid')
    return sma


data = np.array([25, 2, 3, 4, 5, 6, 7, 8, 9, 10])
weights = np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

sma = moving_average(data, weights)
print(sma)