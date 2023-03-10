from pydub import AudioSegment 
from pydub.utils import make_chunks
import os
from datetime import datetime, timedelta

folder = './records/temp/'

def process_sudio(file_name, folder, label):
        myaudio = AudioSegment.from_file(folder + file_name, "wav") 
        chunk_length_ms = 15000 # pydub calculates in millisec 
        chunks = make_chunks(myaudio, chunk_length_ms) #Make chunks of one sec 
        with open(folder + 'new.txt', 'a') as n_file:
            for i, chunk in enumerate(chunks):
                if chunk.duration_seconds == 15: 
                    base_date = datetime.strptime(file_name.removesuffix('.wav'), '%Y-%m-%d_%H-%M-%S')
                    mod_date = base_date + timedelta(seconds = 15 * i)
                    new_file_name = mod_date.strftime('%Y-%m-%d_%H-%M-%S')
                    chunk_name = folder + 'chunked/' + new_file_name + ".wav"
                    n_file.write(new_file_name + ': ' + label + '\n')
                    print("exporting", chunk_name) 
                    chunk.export(chunk_name, format="wav") 

all_file_names = os.listdir(folder)
try:
    os.makedirs(folder + 'chunked') # creating a folder named chunked
except:
    pass
with open(folder + 'new.txt', 'w'):
    pass
with open(folder + "m_records.txt", 'r') as r_file:
    contents = list(map(str.rstrip, r_file.readlines()))

    for each_file in all_file_names:
        if ('.wav' in each_file):
            label = None
            for line in contents:
                if each_file.removesuffix('.wav') in line:
                    splitted = line.split(':')
                    label = splitted[1].strip()
                    break
            process_sudio(each_file, folder, label)