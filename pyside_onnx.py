from multiprocessing import Manager, Process, Value
import threading
import invoker
from time import sleep
from PySide6.QtCore import (
    QSize, 
    Qt,
    QPoint
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

from onnx_wrapper import OnnxWrapper
 

# PyAudio Setup
num_samples = 3024
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 16000
CHUNK = int(SAMPLE_RATE / 10)

audio = pyaudio.PyAudio()
recording_length = 15 # in seconds
time_between_recordings = 300
confidence_threshold = 0.92
conf_length = 20 # how much measurements to take
conf_enough = 10

stream = None
window = None
lock_vad = None

cur_feeling = None

desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop') 
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

def detect_voice_activity(_cur_file_name, _ready_recording_present, _cur_mic):
    model = OnnxWrapper('silero_vad.onnx', True)
    
    # to actually open stream
    stream = open_audio_stream(_cur_mic.value)
    prev_cur_mic = _cur_mic.value

    voiced_confidences = []
    print("Detecting voice")

    while True:
        if prev_cur_mic != _cur_mic.value:
            prev_cur_mic = _cur_mic.value
            stream.close()
            stream = open_audio_stream(_cur_mic.value)
            print(f'changed mic to {_cur_mic.value}')
        audio_chunk = stream.read(num_samples, exception_on_overflow = False)    
        # takes significant amount of time
        # if done on the fly in the same thread, brings noticeable artifacts to 
        audio_int16 = np.frombuffer(audio_chunk, np.int16)
        audio_float32 = int2float(audio_int16)
        # get the confidences
        _x = np.expand_dims(audio_float32, axis = 0)
        new_confidence = model(_x, SAMPLE_RATE)

        voiced_confidences.append(new_confidence)
        print(new_confidence)
        # drop earliest chunk 
        if (len(voiced_confidences) > conf_length):
            voiced_confidences = voiced_confidences[2:]
        # check if in 20 latest chunks there is more than 10 with high speech probability
        if (len(list(i for i in voiced_confidences if i >= confidence_threshold)) > conf_enough):
            print("Detected voice activity")
            voiced_confidences.clear()
            record_active_voice(stream, _cur_file_name)
            _ready_recording_present.value = True
            while _ready_recording_present.value:
                sleep(0.01)
            print("Sleeping between recordings for " + str(time_between_recordings) +" seconds")
            sleep(time_between_recordings)
            
    stream.close()

def stop_recording():
    global continue_recording
    time.sleep(recording_length)
    continue_recording = False

def record_active_voice(stream: pyaudio.Stream, _cur_file_name):
    data = []
    global continue_recording
    continue_recording = True
    print("Starting recording")

    stop_listener = threading.Thread(target=stop_recording)
    stop_listener.start()

    while continue_recording:
        audio_chunk = stream.read(num_samples, exception_on_overflow = False)    
        data.append(audio_chunk)

    dt_string = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    _cur_file_name.value = dt_string
    print("Recorded " + str(recording_length) + " seconds at " + dt_string)
    wav_file = os.path.normpath(os.path.join(desktop, records_path, dt_string + '.wav'))
    try:
        wf = wave.open(wav_file, 'wb')
    except FileNotFoundError:
        record_txt_path = os.path.normpath(os.path.join(desktop, 'records'))
        os.mkdir(record_txt_path)
        wf = wave.open(wav_file, 'wb')
    
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(b''.join(data))

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):
    def __init__(self, ready_recording_present, button_pushed, cur_file_name):
        super().__init__()
        self._ready_recording_present = ready_recording_present
        self._button_pushed = button_pushed
        self._cur_file_name = cur_file_name

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
        self.write_emotional_state(_cur_file_name.value, cur_feeling)
        _button_pushed.value = True
        _ready_recording_present.value = False

    def skip_entry(self):
        wav_file = os.path.normpath(os.path.join(desktop, records_path, _cur_file_name.value + '.wav'))
        os.remove(wav_file)
        print("Recording removed")
        _button_pushed.value = True
        _ready_recording_present.value = False


    def write_emotional_state(self, record_name: str, result: str):
        record_txt_path = os.path.normpath(os.path.join(desktop, records_path))
        try:
            with open(os.path.join(record_txt_path, records_txt), 'a') as f:
                f.write(record_name + ': ' + result + '\n')
        except FileNotFoundError:
            record_txt_path = os.path.normpath(os.path.join(desktop, 'records'))
            os.mkdir(record_txt_path)
            with open(os.path.join(record_txt_path, records_txt), 'w') as f:
                f.write(record_name + ': ' + result + '\n')

def ui_handler(_ready_recording_present, _button_pushed):
    while True:
        while not _ready_recording_present.value:
            sleep(0.1)
        print('Recording ready, showing UI') 
        invoker.invoke_in_main_thread(window.show)
        #window.show()
        while not _button_pushed.value:
            sleep(0.1)
        # wait for button push
        print('Button pushed, hiding UI') 
        _button_pushed.value = False
        invoker.invoke_in_main_thread(window.hide)

def quit_():
    p.terminate()
    tray.setVisible(False)
    print('Child terminated, exiting')
    app.quit()
    # sys.exit()

if __name__ == '__main__':
    app = QApplication()
    manager = Manager()
    _cur_file_name = manager.Value(ctypes.c_wchar_p, '00-00-0000_00-00-00')
    _ready_recording_present = Value(ctypes.c_bool, False)
    _button_pushed = Value(ctypes.c_bool, False)
    _cur_mic = Value(ctypes.c_int, False)

    window = MainWindow(_ready_recording_present, _button_pushed, _cur_file_name)
    window.hide()

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

    p = Process(target=detect_voice_activity, args=(_cur_file_name, _ready_recording_present, _cur_mic))
    p.start()
    stop_listener = threading.Thread(target=ui_handler, args=(_ready_recording_present, _button_pushed))
    stop_listener.start()
    #ui_handler(_ready_recording_present, _button_pushed)
    #p.join()
    
    app.exec()
  