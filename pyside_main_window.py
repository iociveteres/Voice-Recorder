from multiprocessing import Manager, Process, Pipe, Value
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
    QLabel
)
from PySide6.QtGui import (
    QGuiApplication
)
from functools import partial

import numpy as np
import torch
torch.set_num_threads(1)
import torchaudio
import matplotlib.pylab as plt
torchaudio.set_audio_backend("soundfile")
import pyaudio

import time
import threading
import wave
from datetime import datetime
import multiprocessing as mp
import ctypes
import os


# PyAudio Setup
num_samples = 3024
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 16000
CHUNK = int(SAMPLE_RATE / 10)

audio = pyaudio.PyAudio()
recording_length = 15 # in seconds
time_between_recordings = 1800
confidence_threshold = 0.92
conf_length = 20 # how much measurements to take
conf_enough = 10

window = None
lock_vad = None

cur_feeling = None


def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1/abs_max
    sound = sound.squeeze()  # depends on the use case
    return sound

def detect_voice_activity(_cur_file_name, _ready_recording_present):
    # model setup
    model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=False)

    (get_speech_timestamps,
    save_audio,
    read_audio,
    VADIterator,
    collect_chunks) = utils
    stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE, 
                    input=True,
                    frames_per_buffer=CHUNK,
                    input_device_index=1
                    )

    info = audio.get_host_api_info_by_index(0)
    numdevices = info.get('deviceCount') 
    for i in range(0, numdevices):
        if (audio.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
            print("Input Device id ", i, " - ", audio.get_device_info_by_host_api_device_index(0, i).get('name'))
  
    voiced_confidences = []
    #no_voice_found = True

    print("Detecting voice")
    while True:
        audio_chunk = stream.read(num_samples, exception_on_overflow = False)    
        # takes significant amount of time
        # if done on the fly in the same thread, brings noticeable artifacts to 
        audio_int16 = np.frombuffer(audio_chunk, np.int16)
        audio_float32 = int2float(audio_int16)
        # get the confidences
        new_confidence = model(torch.from_numpy(audio_float32), 16000).item()
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

    dt_string = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    _cur_file_name.value = dt_string
    print("Recorded " + str(recording_length) + " seconds at " + dt_string)
    wf = wave.open('./records/' + dt_string + '.wav', 'wb')
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
        #self.write_emotional_state(_cur_file_name.value, cur_feeling)
        os.remove('./records/' + _cur_file_name.value + '.wav')
        print("Recording removed")
        _button_pushed.value = True
        _ready_recording_present.value = False


    def write_emotional_state(self, record_name: str, result: str):
        with open('./records/_records.txt', 'a') as f:
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
        # подождать нажатия на кнопку
        print('Button pushed, hiding UI') 
        _button_pushed.value = False
        invoker.invoke_in_main_thread(window.hide)
        #window.hide()

if __name__ == '__main__':
    app = QApplication()
    manager = Manager()
    _cur_file_name = manager.Value(ctypes.c_wchar_p, '00-00-0000_00-00-00')
    _ready_recording_present = Value(ctypes.c_bool, False)
    _button_pushed = Value(ctypes.c_bool, False)

    window = MainWindow(_ready_recording_present, _button_pushed, _cur_file_name)
    window.hide()
    
    p = Process(target=detect_voice_activity, args=(_cur_file_name, _ready_recording_present))
    p.start()
    stop_listener = threading.Thread(target=ui_handler, args=(_ready_recording_present, _button_pushed))
    stop_listener.start()
    #ui_handler(_ready_recording_present, _button_pushed)
    #p.join()
    
    app.exec()
  
    
