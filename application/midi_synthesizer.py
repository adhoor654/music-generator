from midi2audio import FluidSynth
from pathlib import Path

def synthesize(filepath): #path and filename, without extension
    print("MIDI filepath, according to synthesizer: " + filepath+'.mid')
    fs = FluidSynth(sound_font='GeneralUser.sf2')
    fs.midi_to_audio(filepath+'.mid', filepath+'.wav')
    fs.midi_to_audio(filepath+'.mid', filepath+'.mp3')
