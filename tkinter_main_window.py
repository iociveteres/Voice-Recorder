# Import the required libraries
from tkinter import *
from pystray import MenuItem as item
import pystray
from PIL import Image, ImageTk
import tkinter
import tkinter as tk
import tkinter.messagebox
from recorder import Recorder
import pyaudio
import wave

class window:
    def __init__(self):
        # Start Tkinter and set Title
        self.tk_main = tk.Tk()
        self.collections = []
        self.tk_main.geometry('260x100')
        self.tk_main.title('Record')
        self.rec = rec_aud()
        self.continue_recording = True
        # Set Frames
        self.buttons = tkinter.Frame(self.tk_main)

        # Pack Frame
        self.buttons.pack(fill=tk.BOTH)

        # Start and Stop buttons
        self.start_rec = tkinter.Button(
            self.buttons, width=20, padx=10, pady=5, text='Начать запись', command=lambda: self.start_record())
        self.stop_rec = tkinter.Button(
            self.buttons, width=20, padx=10, pady=5, text='Остановить запись', state='disabled', command=lambda: self.stop_record())
        self.start_rec.grid(row=0, column=0, padx=50, pady=5)
        self.stop_rec.grid(row=1, column=0, columnspan=1, padx=50, pady=5)
        
        # minimize to tray icon on close
        #self.tk_main.protocol('WM_DELETE_WINDOW', self.hide_window)
        tkinter.mainloop()
    
    def start_record(self):
        self.start_rec.config(state="disabled")
        self.stop_rec.config(state="normal")
        self.rec.start_record(self.tk_main)

    def stop_record(self):
        self.rec.stop_record()
        self.start_rec.config(state="normal")
        self.stop_rec.config(state="disabled")
        self.popup_window("record")
       
    def popup_window(self, record_name: str):
        window = tk.Toplevel(self.tk_main)

        label = tk.Label(window, text="Пожалуйста, оцените своё эмоциональное состояние во время записи")
        label.pack(fill='y', padx=20, pady=5)

        button_close_good = tk.Button(window, pady=5, text="Хорошее", command=lambda: self.write_emotional_state(window, record_name, "good"))
        button_close_neutral = tk.Button(window, pady=5, text="Нейтральное", command=lambda: self.write_emotional_state(window, record_name, "neutral"))
        button_close_bad = tk.Button(window, pady=5, text="Плохое", command=lambda: self.write_emotional_state(window, record_name, "bad"))
        
        button_close_good.pack(fill='y')
        button_close_neutral.pack(fill='y')
        button_close_bad.pack(fill='y')

        x = self.tk_main.winfo_x()
        y = self.tk_main.winfo_y()
        window.geometry("+%d+%d" %(x+30,y+30))
        window.wm_transient(self.tk_main)

    def write_emotional_state(self, window: tk.Toplevel, record_name: str, result: str):
        with open('records.txt', 'a') as f:
            f.write(record_name + ': ' + result + '\n')
        window.destroy()


    # Define a function for quit the window
    # def quit_window(self, icon, item):
    #     icon.stop()
    #     self.tk_main.destroy()

    # # Define a function to show the window again
    # def show_window(self, icon, item):
    #     icon.stop()
    #     self.tk_main.after(0, win.deiconify())

    # # Hide the window and show on the system taskbar
    # def hide_window(self):
    #     self.tk_main.withdraw()
    #     image = Image.open("mic_white.ico")
    #     menu = (item('Quit', self.quit_window),
    #             item('Show', self.show_window),
    #             item('Start recording', self.start_record_rcmenu),
    #             item('Stop recording', self.stop_record_rcmenu)
    #             )
    #     icon = pystray.Icon("Voice Recorder Icon", image, "Voice Recorder", menu)
    #     icon.run()

    # def start_record_rcmenu(self, icon: pystray.Icon):
    #     with self.rec.open('nonblocking.wav', 'wb') as recfile:
    #         recfile.start_recording()
    #         while self.continue_recording:
    #             pass
    #         recfile.stop_recording()
            
   
    # def stop_record_rcmenu(self, icon: pystray.Icon):
    #     self.continue_recording = False
        

class rec_aud:
    def __init__(self, chunk=3024, format=pyaudio.paInt16, channels=1, rate=44100, py=pyaudio.PyAudio()):
        # Start Tkinter and set Title
        self.CHUNK = chunk
        self.FORMAT = format
        self.CHANNELS = channels
        self.RATE = rate
        self.p = py
        self.frames = []
        self.st = 1
        self.stream = self.p.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE,
                                  input=True, frames_per_buffer=self.CHUNK, input_device_index=1)
        
        info = self.p.get_host_api_info_by_index(0)
        numdevices = info.get('deviceCount')
        for i in range(0, numdevices):
            if (self.p.get_device_info_by_host_api_device_index(0, i).get('maxInputChannels')) > 0:
                print("Input Device id ", i, " - ", self.p.get_device_info_by_host_api_device_index(0, i).get('name'))

    def start_record(self, tk: tk.Tk):
        self.st = 1
        self.frames = []
        stream = self.p.open(format=self.FORMAT, channels=self.CHANNELS,
                             rate=self.RATE, input=True, frames_per_buffer=self.CHUNK)
        while self.st == 1:
            data = stream.read(self.CHUNK)
            self.frames.append(data)
            tk.update()

        stream.close()

        wf = wave.open('test_recording.wav', 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(self.frames))
        wf.close()

    def stop_record(self):
        self.st = 0

# Create an instance of tkinter frame or window
win = window()