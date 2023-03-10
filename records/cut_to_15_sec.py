from pydub import AudioSegment 
from pydub.utils import make_chunks
import os
from datetime import datetime, timedelta

folder = './records/'

def process_sudio(file_name, folder):
        myaudio = AudioSegment.from_file(folder + file_name, "wav") 
        chunk_length_ms = 15000 # pydub calculates in millisec 
        chunks = make_chunks(myaudio, chunk_length_ms) #Make chunks of one sec 
        for i, chunk in enumerate(chunks):
            if chunk.duration_seconds == 15: 
                base_date = datetime.strptime(file_name.removesuffix('.wav'), '%Y-%m-%d_%H-%M-%S')
                mod_date = base_date + timedelta(seconds = 15 * i)
                new_file_name = mod_date.strftime('%Y-%m-%d_%H-%M-%S')
                chunk_name = folder + 'cut/' + new_file_name + ".wav"
                print("exporting", chunk_name) 
                chunk.export(chunk_name, format="wav") 

try:
    os.makedirs(folder + 'cut') # creating a folder named chunked
except:
    pass
all_file_names = os.listdir(folder)
for each_file in all_file_names:
    if ('.wav' in each_file):
        process_sudio(each_file, folder)