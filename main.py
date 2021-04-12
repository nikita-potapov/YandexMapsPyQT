import sys
from pprint import pprint
from itertools import cycle

import requests
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QTextEdit
from PyQt5.QtCore import Qt

# views settings
#########################################
CORDS = (48.403238, 54.314231)
SPN = 0.5
MAP_VIEW = 'map'
#########################################

MAP_SPN_COEFFICIENT = 0.05
MAP_CORDS_COEFFICIENT = 0.005

MIN_SPN = 0
MAX_SPN = 90

MIN_CORDS_COEFFICIENT = 0.001
MAX_CORDS_COEFFICIENT = 50

MIN_LONGITUDE = -179
MAX_LONGITUDE = 179

MIN_LATITUDE = -85
MAX_LATITUDE = 85

SCREEN_SIZE = [600, 475]

GEOCODER_API_URL = "http://geocode-maps.yandex.ru/1.x/"
GEOCODER_API_KEY = "40d1649f-0493-4b70-98ba-98533de7710b"

STATIC_MAPS_API_URL = "http://static-maps.yandex.ru/1.x/"


def get_toponym_by_name(name_to_find):
    geocoder_params = {
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        "geocode": name_to_find,
        "format": "json"
    }
    response = requests.get(GEOCODER_API_URL, params=geocoder_params)

    if not response:
        print("Ошибка выполнения запроса:")
        print(response.request.url)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        return None

    json_response = response.json()

    toponyms = json_response["response"]["GeoObjectCollection"]["featureMember"]

    if not toponyms:
        print(f'Топоним "{name_to_find}" не найден')
        return None

    toponym = toponyms[0]["GeoObject"]

    return toponym


def get_cords_by_name(name_to_find):
    toponym = get_toponym_by_name(name_to_find)
    return get_cords_by_toponym(toponym)


def get_cords_by_toponym(toponym):
    if toponym is None:
        return None
    toponym_coodrinates = toponym["Point"]["pos"]
    longitude, latitude = toponym_coodrinates.split(" ")
    return float(longitude), float(latitude)


def check_value(value, min_value, max_value):
    value = max(value, min_value)
    value = min(value, max_value)
    return value


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


def spread_value_range_to_other_range(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.map_settings = {
            'cords': CORDS,
            'spn': SPN,
            'map_view': MAP_VIEW,
            'pt': '',
            'cords_coefficient': MAP_CORDS_COEFFICIENT
        }
        self.map_mode = cycle([
            ('Схема', 'map'),
            ('Спутник', 'sat'),
            ('Гибрид', 'sat,skl')])

        self.setGeometry(100, 100, *SCREEN_SIZE)
        self.setWindowTitle('Отображение карты')
        self.image = QLabel(self)
        self.pixmap = QPixmap()
        self.get_map()
        self.init_map()

        self.btn_map_mode_change = QPushButton(self)
        self.btn_map_mode_change.move(0, 450)
        self.btn_map_mode_change.resize(100, 25)
        self.btn_map_mode_change.setText('')
        self.btn_map_mode_change.clicked.connect(self.btn_map_mode_clicked)
        self.btn_map_mode_clicked()

        self.search_phrase = QTextEdit(self)
        self.search_phrase.resize(400, 23)
        self.search_phrase.move(100, 451)
        self.search_phrase.setPlaceholderText('Введите адрес для поиска')
        self.search_phrase.setText('Москва')

        self.btn_search_submit = QPushButton(self)
        self.btn_search_submit.move(500, 450)
        self.btn_search_submit.resize(100, 25)
        self.btn_search_submit.setText('Поиск')
        self.btn_search_submit.clicked.connect(self.btn_search_submit_clicked)

    def get_map(self):
        params = {
            'll': '{0},{1}'.format(*self.map_settings['cords']),
            'spn': '{0},{1}'.format(self.map_settings['spn'], self.map_settings['spn']),
            'l': self.map_settings['map_view'],
            'pt': self.map_settings['pt']
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
        self.image.move(0, 0)
        self.image.resize(600, 450)
        self.image.setPixmap(self.pixmap)

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key_PageUp, Qt.Key_PageDown]:
            spn = self.map_settings['spn']
            if event.key() == Qt.Key_PageUp:
                spn += MAP_SPN_COEFFICIENT
                print('PgUP')
            elif event.key() == Qt.Key_PageDown:
                spn -= MAP_SPN_COEFFICIENT
                print('PgDOWN')

            spn = check_value(spn, MIN_SPN, MAX_SPN)
            self.map_settings['spn'] = spn

            cords_coefficient = spread_value_range_to_other_range(spn, MIN_SPN, MAX_SPN,
                                                                  MIN_CORDS_COEFFICIENT,
                                                                  MAX_CORDS_COEFFICIENT)
            cords_coefficient = check_value(cords_coefficient, MIN_CORDS_COEFFICIENT,
                                            MAX_CORDS_COEFFICIENT)
            self.map_settings['cords_coefficient'] = cords_coefficient
            # todo
            print('SPN =', self.map_settings['spn'])

        if event.key() in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
            x, y = self.map_settings['cords']
            cords_coefficient = self.map_settings['cords_coefficient']
            if event.key() == Qt.Key_Up:
                y += cords_coefficient
            elif event.key() == Qt.Key_Down:
                y -= cords_coefficient
            elif event.key() == Qt.Key_Right:
                x += cords_coefficient
            elif event.key() == Qt.Key_Left:
                x -= cords_coefficient

            x = check_value(x, MIN_LONGITUDE, MAX_LONGITUDE)
            y = check_value(y, MIN_LATITUDE, MAX_LATITUDE)

            self.map_settings['cords'] = (x, y)
            # todo
            print('CORDS', f'({x}, {y})')
        self.get_map()
        self.init_map()

    def btn_map_mode_clicked(self):
        curr = next(self.map_mode)
        self.map_settings['map_view'] = curr[1]
        self.btn_map_mode_change.setText(curr[0])
        self.get_map()
        self.init_map()

    def btn_search_submit_clicked(self):
        search_phrase = self.search_phrase.toPlainText()
        if not search_phrase:
            self.map_settings['pt'] = ''
            self.get_map()
            self.init_map()
            return
        toponym = get_toponym_by_name(search_phrase)
        cords = get_cords_by_toponym(toponym)
        if cords is not None:
            self.map_settings['cords'] = cords
            self.map_settings['spn'] = round(max(get_spn_size(toponym)), 3)
            self.map_settings['pt'] = f'{cords[0]},{cords[1]},pm2rdm'
            self.get_map()
            self.init_map()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
