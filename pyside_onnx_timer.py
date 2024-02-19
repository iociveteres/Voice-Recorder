from multiprocessing import Manager, Process, Value, Event
import threading
import random
import invoker
from time import sleep
from PySide6.QtCore import (
    QSize, 
    Qt,
    QPoint,
    QTimer
)

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
    QMenu,
    QSystemTrayIcon
)
from PySide6.QtGui import (
    QGuiApplication,
    QIcon,
    QAction
)
from functools import partial

import numpy as np
import pyaudio

import time
import threading
import wave
from datetime import datetime
import ctypes
import os
 
import json
with open('./settings.json', encoding='utf-8') as f:
    settings_json = json.load(f)
    mode = settings_json['mode']
    save_location_setting = settings_json['save_location']
    poll_frequency = settings_json['poll_frequency'] # in minutes

with open('./quotes.json', encoding='utf-8') as f:
    quotes_json = json.load(f)

# PyAudio Setup
num_samples = 3024
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 16000
CHUNK = int(SAMPLE_RATE / 10)

audio = pyaudio.PyAudio()
recording_length = 15 # in seconds


stream = None
poll_ready_window = None
text_window = None
feeling_poll_window = None

cur_feeling = None

if save_location_setting == "desktop":  
    save_location = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop') 
else:
    save_location = './'

records_path = 'records'
records_txt = '_records.txt'

storing_mode = 'single_folder'

def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1/abs_max
    sound = sound.squeeze()  # depends on the use case
    return sound

def make_folders(mode):
    pass

def get_input_devices():
    info = audio.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount') 
    devices = {}
    for i in range(0, numdevices):
        if (audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            device_name = audio.get_device_info_by_host_api_device_index(0, i).get('name')
            if device_name != 'Microsoft Sound Mapper - Input': 
                devices[i] = device_name
    return devices

def select_microphone(mic_id, mic_name, _cur_mic):
    print(f"Selected microphone: {mic_id}")
    _cur_mic.value = mic_id
    for action in microphone_submenu.actions():
        action.setChecked(action.text() == f'{mic_id}: {mic_name}')
    
def open_audio_stream(mic_id):
    return audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE, 
                    input=True,
                    frames_per_buffer=CHUNK,
                    input_device_index=mic_id
                    )    

def stop_recording():
    global continue_recording
    time.sleep(recording_length)
    continue_recording = False

def record_active_voice():
    stream = open_audio_stream(_cur_mic.value)
    data = []
    global continue_recording
    continue_recording = True
    print("Starting recording")

    stop_listener = threading.Thread(target=stop_recording)
    stop_listener.start()

    while continue_recording:
        audio_chunk = stream.read(num_samples, exception_on_overflow = False)    
        data.append(audio_chunk)

    return data


def save_audio(audio_data):
    dt_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    cur_file_name = dt_string
    print("Recorded " + str(recording_length) + " seconds at " + dt_string)
    wav_file = os.path.normpath(os.path.join(save_location, records_path, dt_string + '.wav'))
    try:
        wf = wave.open(wav_file, 'wb')
    except FileNotFoundError:
        record_txt_path = os.path.normpath(os.path.join(save_location, 'records'))
        os.mkdir(record_txt_path)
        wf = wave.open(wav_file, 'wb')
    
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(b''.join(audio_data))

    return cur_file_name


from threading import Thread
class ThreadWithReturnValue(Thread):
    
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,
                                                **self._kwargs)
    def join(self, *args):
        Thread.join(self, *args)
        return self._return


# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cur_file_name = ''
        self.setWindowFlags(Qt.Tool)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle("My App")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(QSize(300, 160))
        
        layout = QVBoxLayout()

        label = QLabel("Оцените ваше самочувствие")
        label.setMinimumSize(250, 0)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        button_1 = QPushButton("Хорошее")
        button_2 = QPushButton("Нейтральное")
        button_3 = QPushButton("Плохое")
        button_4 = QPushButton("Пропустить запись")
        button_1.clicked.connect(partial(self.set_cur_feeling, ('good')))
        button_2.clicked.connect(partial(self.set_cur_feeling, ('neutral')))
        button_3.clicked.connect(partial(self.set_cur_feeling, ('bad')))
        button_4.clicked.connect(partial(self.skip_entry))
        layout.addWidget(button_1)
        layout.addWidget(button_2)
        layout.addWidget(button_3)
        layout.addWidget(button_4)

        widget = QWidget()
        widget.setLayout(layout)
        self.bottom_right()
        # Set the central widget of the Window.
        self.setCentralWidget(widget)

    def bottom_right(self):
        bottomRightPoint = QGuiApplication.primaryScreen().availableGeometry().bottomRight()
        size = self.size()
        bottomRightPoint -= QPoint(size.width()+30, size.height()+50)
        self.move(bottomRightPoint)

    def set_cur_feeling(self, cur_feeling):
        self.write_emotional_state(self.cur_file_name, cur_feeling)
        self.hide()

    def skip_entry(self):
        wav_file = os.path.normpath(os.path.join(save_location, records_path, self.cur_file_name + '.wav'))
        os.remove(wav_file)
        print("Recording removed")
        self.hide()


    def write_emotional_state(self, record_name: str, result: str):
        record_txt_path = os.path.normpath(os.path.join(save_location, records_path))
        try:
            with open(os.path.join(record_txt_path, records_txt), 'a') as f:
                f.write(record_name + ': ' + result + '\n')
        except FileNotFoundError:
            record_txt_path = os.path.normpath(os.path.join(save_location, 'records'))
            os.mkdir(record_txt_path)
            with open(os.path.join(record_txt_path, records_txt), 'w') as f:
                f.write(record_name + ': ' + result + '\n')

    def what_to_do_with_entry(self, audio_data):
        self.cur_file_name = save_audio(audio_data)
        self.show()


class PollIfReady(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Tool)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle("My App")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(QSize(300, 160))
        
        layout = QVBoxLayout()

        label = QLabel("Сделать запись сейчас?\nВам будет предложен текст,\nпрочитайте его в спокойном темпе")
        label.setMinimumSize(250, 0)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        button_1 = QPushButton("Да")
        button_2 = QPushButton("Нет")
        button_1.clicked.connect(partial(self.show_text))
        button_2.clicked.connect(partial(self.skip))
        layout.addWidget(button_1)
        layout.addWidget(button_2)

        self.setLayout(layout)
        self.bottom_right()

    def bottom_right(self):
        bottomRightPoint = QGuiApplication.primaryScreen().availableGeometry().bottomRight()
        size = self.size()
        bottomRightPoint -= QPoint(size.width()+30, size.height()+50)
        self.move(bottomRightPoint)

    def show_text(self):
        self.hide()
        text_window.show_new_text()

    def skip(self):
        self.hide()


def secs_to_minsec(secs: int):
    mins = secs // 60
    secs = secs % 60
    minsec = f'{mins:02}:{secs:02}'
    return minsec


class RecordTextWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.time_left_int = recording_length
        self.myTimer = QTimer(self)
        self.audio_data = None
        self.record_thread = None

        self.setWindowFlags(Qt.Tool)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle("My App")
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setFixedSize(QSize(300, 160))
        
        layout = QVBoxLayout()

        self.text = QLabel()
        self.text.setMinimumSize(250, 0)
        self.text.setAlignment(Qt.AlignCenter)
        self.text.setWordWrap(True)
        layout.addWidget(self.text)
        
        self.timerLabel = QLabel()
        self.timerLabel.setText(f"00:{self.time_left_int}")
        self.timerLabel.setAlignment(Qt.AlignCenter)
        self.timerLabel.setStyleSheet("font: 10pt Helvetica")
        layout.addWidget(self.timerLabel)

        self.setLayout(layout)
        self.bottom_right()

    
    def bottom_right(self):
        bottomRightPoint = QGuiApplication.primaryScreen().availableGeometry().bottomRight()
        size = self.size()
        bottomRightPoint -= QPoint(size.width()+30, size.height()+50)
        self.move(bottomRightPoint)

    
    def show_new_text(self):
        self.show()
        rand = random.randrange(len(quotes_json))
        self.text.setText(quotes_json[rand][0])
        self.start_timer()

    
    def start_timer(self):
        print('started timer')
        self.time_left_int = recording_length
        self.record_thread = ThreadWithReturnValue(target=record_active_voice)
        self.record_thread.start()

        self.myTimer.timeout.connect(self.timer_tick)
        self.myTimer.start(1000)

    
    def timer_tick(self):
        self.time_left_int -= 1

        if self.time_left_int == 0:
            self.time_left_int = recording_length
            self.myTimer.timeout.disconnect(self.timer_tick)
            self.hide()
            self.audio_data = self.record_thread.join()
            feeling_poll_window.what_to_do_with_entry(self.audio_data)

        self.update_gui()

    
    def update_gui(self):
        minsec = secs_to_minsec(self.time_left_int)
        self.timerLabel.setText(minsec)


class MyThread(threading.Thread):
    def __init__(self, event):
        threading.Thread.__init__(self)
        self.stopped = event

    def run(self):
        while not self.stopped.wait(poll_frequency * 60):
            print("Timer went out")
            invoker.invoke_in_main_thread(ui_handler())


def ui_handler():
    print('Showing UI') 
    poll_ready_window.show()
    

def quit_():
    tray.setVisible(False)
    app.quit()


if __name__ == '__main__':
    app = QApplication()
    manager = Manager()

    _cur_mic = Value(ctypes.c_int, False)

    feeling_poll_window = MainWindow()
    feeling_poll_window.hide()

    poll_ready_window = PollIfReady()
    poll_ready_window.show()

    text_window = RecordTextWindow()
    text_window.hide()

    tray = QSystemTrayIcon()
    icon = QIcon('mic_icon.png')
    tray.setIcon(icon)
    tray.setVisible(True)

    # Create the menu
    menu = QMenu()
    
    mics = get_input_devices()
    microphone_submenu = QMenu("Микрофон")
    menu.addMenu(microphone_submenu)
    mic_actions = []
    for mic_id in mics:
        mic_actions.append(QAction(f'{mic_id}: {mics[mic_id]}'))
        mic_actions[-1].setCheckable(True)
        mic_actions[-1].triggered.connect(lambda _cur_mic = _cur_mic, mic=mic_id, 
                                          mic_name = mics[mic_id]: 
                                    select_microphone(mic, mic_name, _cur_mic))
        microphone_submenu.addAction(mic_actions[-1])

    for key in mics:
        print("Input Device id ", key, " - ", mics[key])
    # get any mic from the dict to initialize
    mic_id = next(iter(mics.keys()))
    print(mic_id)
    mic_name = mics[mic_id]
    _cur_mic.value = mic_id
    select_microphone(mic_id, mic_name, _cur_mic)

    # Add a Quit option to the menu.
    quit = QAction("Выход")
    quit.triggered.connect(quit_)
    menu.addAction(quit)
    # Add the menu to the tray
    tray.setContextMenu(menu)

    stop_flag = Event()
    stop_listener = MyThread(stop_flag)
    stop_listener.start()
    
    app.exec()
  