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

import math


def lonlat_distance(a, b):
    degree_to_meters_factor = 111 * 1000  # 111 километров в метрах
    a_lon, a_lat = a
    b_lon, b_lat = b

    # Берем среднюю по широте точку и считаем коэффициент для нее.
    radians_lattitude = math.radians((a_lat + b_lat) / 2.)
    lat_lon_factor = math.cos(radians_lattitude)

    # Вычисляем смещения в метрах по вертикали и горизонтали.
    dx = abs(a_lon - b_lon) * degree_to_meters_factor * lat_lon_factor
    dy = abs(a_lat - b_lat) * degree_to_meters_factor

    # Вычисляем расстояние между точками.
    distance = math.sqrt(dx * dx + dy * dy)

    return distance


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


def get_toponym_by_cords(pos, kind=None):
    if kind is None:
        kind = 'house'
    geocoder_params = {
        "apikey": "40d1649f-0493-4b70-98ba-98533de7710b",
        # "kind": kind,
        "geocode": "{},{}".format(*pos),
        "format": "json"
    }
    response = requests.get(GEOCODER_API_URL, params=geocoder_params)

    if not response:
        print("Ошибка выполнения запроса:")
        print(response.request.url)
        print("Http статус:", response.status_code, "(", response.reason, ")")
        return None

    json_response = response.json()
    data = json_response['response']['GeoObjectCollection']['featureMember']
    return data


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


def get_cords_by_name(name_to_find):
    toponym = get_toponym_by_name(name_to_find)
    return get_cords_by_toponym(toponym)


def get_cords_by_toponym(toponym):
    if toponym is None:
        return None
    toponym_coodrinates = toponym["Point"]["pos"]
    longitude, latitude = toponym_coodrinates.split(" ")
    return float(longitude), float(latitude)


def get_address_by_toponym(toponym):
    try:
        address = toponym['metaDataProperty']['GeocoderMetaData']['Address']
        return address
    except Exception:
        return None


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
            'pt': '',
            'cords_coefficient': MAP_CORDS_COEFFICIENT,
        }
        self.map_mode = cycle([
            ('Схема', 'map'),
            ('Спутник', 'sat'),
            ('Гибрид', 'sat,skl')])

        self.is_index_show = True

        self.current_search_result_toponym = None

        self.setGeometry(100, 100, *SCREEN_SIZE)
        self.setMaximumSize(*SCREEN_SIZE)
        self.setMinimumSize(*SCREEN_SIZE)
        self.setWindowTitle('Отображение карты')
        self.image = QLabel(self)
        self.pixmap = QPixmap()
        self.get_map()
        self.init_map()

        self.btn_map_mode_change = QPushButton(self)
        self.btn_map_mode_change.move(0, 475)
        self.btn_map_mode_change.resize(100, 25)
        self.btn_map_mode_change.setText('')
        self.btn_map_mode_change.clicked.connect(self.btn_map_mode_clicked)
        self.btn_map_mode_clicked()

        self.btn_search_submit = QPushButton(self)
        self.btn_search_submit.move(500, 475)
        self.btn_search_submit.resize(100, 25)
        self.btn_search_submit.setText('Поиск')
        self.btn_search_submit.clicked.connect(self.btn_search_submit_clicked)

        self.btn_search_result_reset = QPushButton(self)
        self.btn_search_result_reset.move(0, 0)
        self.btn_search_result_reset.resize(150, 25)
        self.btn_search_result_reset.setText('Сброс результата поиска')
        self.btn_search_result_reset.clicked.connect(self.btn_search_result_reset_clicked)

        self.search_phrase = QLineEdit(self)
        self.search_phrase.resize(400, 23)
        self.search_phrase.move(100, 476)
        self.search_phrase.setPlaceholderText('Введите адрес для поиска')
        self.search_phrase.setText('Москва')
        self.search_phrase.returnPressed.connect(self.btn_search_submit_clicked)

        self.search_result_address = QLineEdit(self)
        self.search_result_address.resize(400, 23)
        self.search_result_address.move(152, 1)
        self.search_result_address.setPlaceholderText('Адрес найденного объекта')
        self.search_result_address.setReadOnly(True)

        self.btn_show_index = QPushButton(self)
        self.btn_show_index.move(552, 0)
        self.btn_show_index.resize(48, 25)
        self.btn_show_index.setText('Индекс')
        self.btn_show_index.clicked.connect(self.btn_show_index_clicked)

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
        self.image.move(0, 25)
        self.image.resize(600, 450)
        self.image.setPixmap(self.pixmap)

    def keyPressEvent(self, event):
        if event.key() in [Qt.Key_PageUp, Qt.Key_PageDown]:
            print('-' * 20)
            spn = self.map_settings['spn']
            spn_coefficient = round(spread_value_range_to_other_range(spn, MIN_SPN, MAX_SPN,
                                                                      MIN_SPN_COEFFICIENT,
                                                                      MAX_SPN_COEFFICIENT), 6)

            if event.key() == Qt.Key_PageUp:
                spn += spn_coefficient
                print('PgUP')
            elif event.key() == Qt.Key_PageDown:
                spn -= spn_coefficient
                print('PgDOWN')

            print('spn_coef = ', spn_coefficient)

            spn = check_value(spn, MIN_SPN, MAX_SPN)
            self.map_settings['spn'] = round(spn, 6)

            cords_coefficient = spread_value_range_to_other_range(spn, MIN_SPN, MAX_SPN,
                                                                  MIN_CORDS_COEFFICIENT,
                                                                  MAX_CORDS_COEFFICIENT)
            cords_coefficient = round(check_value(cords_coefficient, MIN_CORDS_COEFFICIENT,
                                                  MAX_CORDS_COEFFICIENT), 5)
            self.map_settings['cords_coefficient'] = cords_coefficient
            # todo
            print('SPN =', self.map_settings['spn'])
            print('cords coef =', self.map_settings['cords_coefficient'])
            print('-' * 20)

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

            x = round(check_value(x, MIN_LONGITUDE, MAX_LONGITUDE), 6)
            y = round(check_value(y, MIN_LATITUDE, MAX_LATITUDE), 6)

            self.map_settings['cords'] = (x, y)
            # todo
            print('CORDS', f'({x}, {y})')
        self.get_map()
        self.init_map()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        x, y = event.x(), event.y()
        if self.image.x() < x < self.image.x() + self.image.width() and \
                self.image.y() < y < self.image.y() + self.image.height():
            x -= self.image.x()
            y -= self.image.y()
            pos = self.get_gps_cords_by_program_cords((x, y))
            toponyms = get_toponym_by_cords(pos)
            if not toponyms:
                return
            current_toponym = min(toponyms, key=lambda x: lonlat_distance(pos, tuple(
                map(float, x['GeoObject']['Point']['pos'].split(' ')))))

            # pprint(toponyms)

            self.image.setFocus()
            current_toponym = current_toponym['GeoObject']
            self.current_search_result_toponym = current_toponym
            self.show_current_toponym_address()
            cords = get_cords_by_toponym(current_toponym)
            if cords is not None:
                # self.map_settings['cords'] = cords
                # self.map_settings['spn'] = round(max(get_spn_size(current_toponym)), 4)
                self.map_settings['pt'] = f'{cords[0]},{cords[1]},pm2rdm'
                self.get_map()
                self.init_map()

    def btn_map_mode_clicked(self):
        curr = next(self.map_mode)
        self.map_settings['map_view'] = curr[1]
        self.btn_map_mode_change.setText(curr[0])
        self.get_map()
        self.init_map()

    def btn_search_submit_clicked(self):
        self.image.setFocus()
        search_phrase = self.search_phrase.text()
        if not search_phrase:
            self.search_result_address.setText('')
            self.map_settings['pt'] = ''
            self.get_map()
            self.init_map()
            return

        current_toponym = get_toponym_by_name(search_phrase)
        self.current_search_result_toponym = current_toponym
        self.show_current_toponym_address()
        cords = get_cords_by_toponym(current_toponym)
        if cords is not None:
            self.map_settings['cords'] = cords
            self.map_settings['spn'] = round(max(get_spn_size(current_toponym)), 4)
            self.map_settings['pt'] = f'{cords[0]},{cords[1]},pm2rdm'
            self.get_map()
            self.init_map()

    def btn_search_result_reset_clicked(self):
        self.current_search_result_toponym = None
        self.search_result_address.setText('')
        self.map_settings['pt'] = ''
        self.get_map()
        self.init_map()

    def show_current_toponym_address(self):
        toponym_address = get_address_by_toponym(self.current_search_result_toponym)
        if toponym_address is None:
            address = ''
        else:
            address = toponym_address['formatted']
            if self.is_index_show:
                if 'postal_code' in toponym_address:
                    address += ', ' + toponym_address['postal_code']
        self.search_result_address.setText(address)

    def btn_show_index_clicked(self):
        self.is_index_show = not self.is_index_show
        self.show_current_toponym_address()

    def get_gps_cords_by_program_cords(self, program_cords):
        c_x, c_y = self.map_settings['cords']
        x, y = program_cords
        dx = x - (self.image.x() + self.image.width() / 2)
        dy = - y + (self.image.y() + self.image.height() / 2)

        coef_cords = self.map_settings['spn'] / self.image.width()

        new_x = c_x + dx * coef_cords
        new_y = c_y + dy * coef_cords

        gps_cords = (new_x, new_y)
        return gps_cords


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MainWindow()
    ex.show()
    sys.exit(app.exec())
