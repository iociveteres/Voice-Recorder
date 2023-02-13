from multiprocessing import Process, Lock

import numpy as np
import torch
torch.set_num_threads(1)
import torchaudio
import matplotlib.pylab as plt
torchaudio.set_audio_backend("soundfile")
import pyaudio

import time
import threading
import msvcrt
import wave
from datetime import datetime
import multiprocessing as mp
import ctypes
# model setup
model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                              model='silero_vad',
                              force_reload=False)
(get_speech_timestamps,
save_audio,
read_audio,
VADIterator,
collect_chunks) = utils
# PyAudio Setup
num_samples = 3024
FORMAT = pyaudio.paInt16
CHANNELS = 1
SAMPLE_RATE = 16000
CHUNK = int(SAMPLE_RATE / 10)

audio = pyaudio.PyAudio()
recording_length = 15 # in seconds
confidence_threshold = 0.95
conf_length = 20 # how much measurements to take
conf_enough = 10

cur_file_name = mp.Value(ctypes.c_wchar_p, '00-00-0000_00-00-00')
# Helper Methods
# Taken from utils_vad.py
def validate(model,
             inputs: torch.Tensor):
    with torch.no_grad():
        outs = model(inputs)
    return outs

# Provided by Alexander Veysov
def int2float(sound):
    abs_max = np.abs(sound).max()
    sound = sound.astype('float32')
    if abs_max > 0:
        sound *= 1/abs_max
    sound = sound.squeeze()  # depends on the use case
    return sound

def stop():
    global continue_recording
    time.sleep(recording_length)
    continue_recording = False
    
def start_recording():
    import cProfile    
    from pstats import Stats
    pr = cProfile.Profile()
    pr.enable()

    pr.disable()
    pr.print_stats(sort='time')

def detect_voice_activity(lock: Lock,):
    lock.acquire()
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
    no_voice_found = True

    print("Detecting voice")
    while no_voice_found:
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
            record_active_voice(stream)
            
            lock.release()
            time.sleep(1)
            lock.acquire()
    stream.close()

def record_active_voice(stream: pyaudio.Stream):
    data = []
    global continue_recording
    continue_recording = True
    print("Starting recording")

    stop_listener = threading.Thread(target=stop)
    stop_listener.start()

    while continue_recording:
        audio_chunk = stream.read(num_samples, exception_on_overflow = False)    
        data.append(audio_chunk)

    dt_string = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    cur_file_name.value = dt_string
    print("Recorded " + str(recording_length) + " seconds at " + dt_string)
    wf = wave.open('./records/' + dt_string + '.wav', 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(audio.get_sample_size(FORMAT))
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(b''.join(data))

if __name__ == '__main__':
    p = Process(target=detect_voice_activity, args=())
    p.start()
    p.join()