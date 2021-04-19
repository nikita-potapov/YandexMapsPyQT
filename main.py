import sys
from pprint import pprint
from itertools import cycle
from math import exp
import requests
from PyQt5 import QtGui
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QLineEdit
from PyQt5.QtCore import Qt

# views settings
#########################################
CORDS = (48.403238, 54.314231)
SPN = 0.005
MAP_VIEW = 'map'
#########################################


POINTS = [
    (40.452111, 93.742111),
    (32.1499889, -110.8358417),
    (37.401573, -116.867808),
    (35.5246, -104.5722778),
    (-33.8678889, -63.987),
]

MAP_SPN_COEFFICIENT = 0.05
MAP_CORDS_COEFFICIENT = 0.005

MIN_SPN = 0
MAX_SPN = 90

MIN_CORDS_COEFFICIENT = 0.001
MAX_CORDS_COEFFICIENT = 50

MIN_SPN_COEFFICIENT = 0.001
MAX_SPN_COEFFICIENT = 2

MIN_LONGITUDE = -179
MAX_LONGITUDE = 179

MIN_LATITUDE = -85
MAX_LATITUDE = 85

SCREEN_SIZE = [600, 500]

GEOCODER_API_URL = "http://geocode-maps.yandex.ru/1.x/"
GEOCODER_API_KEY = "40d1649f-0493-4b70-98ba-98533de7710b"

SEARCH_API_SERVER_URL = "https://search-maps.yandex.ru/v1/"
SEARCH_API_KEY = "dda3ddba-c9ea-4ead-9010-f43fbc15c6e3"

STATIC_MAPS_API_URL = "http://static-maps.yandex.ru/1.x/"


def get_spn_size(toponym):
    envelope = toponym['boundedBy']['Envelope'].values()
    lower, upper = envelope
    lower = tuple(map(float, lower.split()))
    upper = tuple(map(float, upper.split()))

    x1, y1 = lower
    x2, y2 = upper
    width = abs(x1 - x2)
    height = abs(y1 - y2)
    return width, height


def check_value(value, min_value, max_value):
    value = max(value, min_value)
    value = min(value, max_value)
    return value


def spread_value_range_to_other_range(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.map_settings = {
            'cords': CORDS,
            'spn': SPN,
            'map_view': MAP_VIEW,
        }
        self.map_points = cycle(POINTS)

        self.setGeometry(100, 100, *SCREEN_SIZE)
        self.setMaximumSize(*SCREEN_SIZE)
        self.setMinimumSize(*SCREEN_SIZE)
        self.setWindowTitle('Отображение карты')
        self.image = QLabel(self)
        self.pixmap = QPixmap()
        self.get_map()
        self.init_map()

    def get_map(self):
        params = {
            'll': '{0},{1}'.format(*self.map_settings['cords']),
            'spn': '{0},{1}'.format(self.map_settings['spn'], self.map_settings['spn']),
            'l': 'sat'
        }
        response = requests.get(STATIC_MAPS_API_URL, params=params)

        if not response:
            print("Ошибка выполнения запроса:")
            print(response.request.url)
            print("Http статус:", response.status_code, "(", response.reason, ")")
            sys.exit(1)

        # Запишем полученное изображение в файл.
        self.map_data = response.content

    def init_map(self):
        self.pixmap.loadFromData(self.map_data)
        self.image.move(0, 25)
        self.image.resize(600, 450)
        self.image.setPixmap(self.pixmap)

    def keyPressEvent(self, event):
        pos = next(self.map_points)

        self.map_settings['cords'] = next(self.map_points)[::-1]

        self.get_map()
        self.init_map()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
