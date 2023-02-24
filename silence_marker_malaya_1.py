import malaya_speech
import numpy as np
import librosa
from malaya_speech import Pipeline
import matplotlib.pyplot as plt
import IPython.display as ipd

def norm_mel(y, sr):
    mel = librosa.feature.melspectrogram(y, sr = sr, n_mels = 80)
    return np.log10(np.maximum(mel, 1e-10)).T

def plot(y, sr):
    mel = norm_mel(y, sr)
    fig, axs = plt.subplots(2, figsize=(10, 8))
    axs[0].plot(y)
    im = axs[1].imshow(np.rot90(mel), aspect='auto', interpolation='none')
    fig.colorbar(mappable=im, shrink=0.65, orientation='horizontal', ax=axs[1])
    plt.show()

y, sr = malaya_speech.load('test_recording.wav')
#plot(y, sr)

quantized_model = malaya_speech.vad.deep_model(model = 'vggvox-v2', quantized = True)

p = Pipeline()
pipeline_left = (
    p.map(malaya_speech.generator.frames, frame_duration_ms = 40, sample_rate = 16000)
)

pipeline_right = (
    pipeline_left.batching(5)
    .foreach_map(quantized_model.predict)
    .flatten()
)
#p.visualize()
pipeline_left.foreach_zip(pipeline_right).map(malaya_speech.combine.without_silent, 
                                             threshold_to_stop = 0.10)

results = p(y)
print(len(results['without_silent']))
audio = ipd.Audio(results['without_silent'], rate = sr)
with open('test.wav', 'wb') as f:
    f.write(audio.data)
#plot(results['without_silent'], sr)