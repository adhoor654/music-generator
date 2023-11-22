from midi2audio import FluidSynth

#filepath: path and filename, without an extension
def synthesize(filepath): 
    print("MIDI filepath, according to synthesizer: " + filepath+'.mid')
    fs = FluidSynth(sound_font='GeneralUser.sf2')
    fs.midi_to_audio(filepath+'.mid', filepath+'.wav')
