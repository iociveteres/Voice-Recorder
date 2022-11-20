# Import the required libraries
from tkinter import *
from pystray import MenuItem as item
import pystray
from PIL import Image, ImageTk
import tkinter
import tkinter as tk
import tkinter.messagebox
from recorder import Recorder


class window:
    def __init__(self):
        # Start Tkinter and set Title
        self.tk_main = tk.Tk()
        self.collections = []
        self.tk_main.geometry('500x300')
        self.tk_main.title('Record')
        self.rec = Recorder()
        self.continue_recording = True
        # Set Frames
        self.buttons = tkinter.Frame(self.tk_main, padx=120, pady=20)

        # Pack Frame
        self.buttons.pack(fill=tk.BOTH)

        # Start and Stop buttons
        self.strt_rec = tkinter.Button(
            self.buttons, width=10, padx=10, pady=5, text='Start Recording', command=lambda: self.start_record())
        self.strt_rec.grid(row=0, column=0, padx=50, pady=5)
        self.stop_rec = tkinter.Button(
            self.buttons, width=10, padx=10, pady=5, text='Stop Recording', command=lambda: self.stop())
        self.stop_rec.grid(row=1, column=0, columnspan=1, padx=50, pady=5)
        
        self.tk_main.protocol('WM_DELETE_WINDOW', self.hide_window)
        tkinter.mainloop()

    # Define a function for quit the window
    def quit_window(self, icon, item):
        icon.stop()
        self.tk_main.destroy()

    # Define a function to show the window again
    def show_window(self, icon, item):
        icon.stop()
        self.tk_main.after(0, win.deiconify())


    # Hide the window and show on the system taskbar
    def hide_window(self):
        self.tk_main.withdraw()
        image = Image.open("mic_white.ico")
        menu = (item('Quit', self.quit_window),
                item('Show', self.show_window),
                item('Start recording', self.start_record_rcmenu),
                item('Stop recording', self.stop_record_rcmenu))
        icon = pystray.Icon("Voice Recorder Icon", image, "Voice Recorder", menu)
        icon.run_detached()

    def start_record_rcmenu(self, icon: pystray.Icon):
        with self.rec.open('nonblocking.wav', 'wb') as recfile:
            recfile.start_recording()
            while self.continue_recording:
                pass
            recfile.stop_recording()
            
   
    def stop_record_rcmenu(self, icon: pystray.Icon):
        self.continue_recording = False
        

# class rec_aud:
#     def __init__(self, chunk=3024, format=pyaudio.paInt16, channels=1, rate=44100, py=pyaudio.PyAudio()):
#         # Start Tkinter and set Title
#         self.CHUNK = chunk
#         self.FORMAT = format
#         self.CHANNELS = channels
#         self.RATE = rate
#         self.p = py
#         self.frames = []
#         self.st = 1
#         self.stream = self.p.open(format=self.FORMAT, channels=self.CHANNELS, rate=self.RATE,
#                                   input=True, frames_per_buffer=self.CHUNK, input_device_index=1)

#     def start_record(self):
#         self.st = 1
#         self.frames = []
#         stream = self.p.open(format=self.FORMAT, channels=self.CHANNELS,
#                              rate=self.RATE, input=True, frames_per_buffer=self.CHUNK)
#         while self.st == 1:
#             data = stream.read(self.CHUNK)
#             self.frames.append(data)
#             print("* recording")

#         stream.close()

#         wf = wave.open('test_recording.wav', 'wb')
#         wf.setnchannels(self.CHANNELS)
#         wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
#         wf.setframerate(self.RATE)
#         wf.writeframes(b''.join(self.frames))
#         wf.close()

#     def stop_record(self):
#        


# Create an instance of tkinter frame or window
win = window()