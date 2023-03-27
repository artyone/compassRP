from serial import Serial, EIGHTBITS
from serial.tools import list_ports
from serial.serialutil import SerialException
from random import choice


class VirtualSender():
    '''Класс для отправки данных на ком-порт'''
    data: list = [0x1F1C, 0x1A3C, 0x7510, 0x1000]

    @staticmethod
    def get_ports() -> list:
        """Получение ком-портов компьютера"""
        ports_list: list = list_ports.comports()
        return ports_list

    def start_spam(self) -> None:
        with Serial(bytesize=EIGHTBITS, write_timeout=0.5) as ser:
            ser.port = list(map(lambda x: x.device, self.get_ports()))[0]
            while True:
                try:
                    ser.open()
                    command: bytes = choice(
                        self.data).to_bytes(4, byteorder='big')
                    ser.write(command)
                    ser.close()
                except SerialException:
                    continue

# Отладка в консоли
# sender = VirtualSender()
# print(sender.get_ports())
# sender.start_spam()

