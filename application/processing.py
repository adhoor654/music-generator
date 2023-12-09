from mido import MidiFile
from music21 import converter, instrument, note, chord, stream
import midi_clip
from pathlib import Path
import ntpath

# #midi_filepath: path and filename of midi, without an extension
# #generation_params: dataframe of generation parameters, 
#     #including genre, tempo, length, instruments, dynamics
def postprocess(midi_filepath, generation_params):

    INSTRUMENTS = {
        'piano' : 'Piano',
        'guitar' : 'Guitar',
        'drums' : 'BassDrum',
        'violin' : 'Violin',
        'flute' : 'Flute',
        'saxophone' : 'Saxophone'
    }

    cwd = Path.cwd()
    #print("Current directory: ", cwd)

    instr = generation_params['instruments']

    #print("These are the instruments: " + instr)

    gen = generation_params['genre']

    #print("This is the genre: " + gen)

    tem = int(generation_params['tempo'])

    #print("This is the tempo: " + str(tem))

    leng = int(generation_params['length'])

    #print("This is the length: " + str(leng))

    dynam = int(generation_params['dynamics'])
    
    #print("This is the dynamics: " + str(dynam))

    instr_base_name = instr.split(' ', 1)[0]

    #print("This is the base instrument: " + instr_base_name)

    instr_full_name = ""

    if (instr_base_name in INSTRUMENTS.keys()):
        instr_full_name = INSTRUMENTS.get(instr_base_name)
        #print("This is the full name: " + instr_full_name)

    instr_instance = getattr(instrument, instr_full_name)
    #print(instr_instance())

    midi = converter.parse(midi_filepath + ".mid")

    #print("Parsing %s" % file)

    #no patch defined (may be needed for certain MIDI files, not needed for MAESTRO dataset)

    # for p in midi.parts:
    #     p.insert(0, instrument.Violin())

    #patch defined


    # Define a lookup table for modifications
    ## for tem = 1 (slow) -> 2x slow, for tem = 3 (fast) -> .75x slow
    tempo_mod_table = {1: 2, 2: 1, 3: 0.75}
    tempo_multplier = tempo_mod_table.get(tem)

    # Define a lookup table for dynamics modifications
    ## for dynam = 1 (soft) -> .25x velocity, for 3 (loud) -> 1.5x velocity
    dynamic_mod_table = {1: .25, 2: 1, 3: 1.5}
    velocity_multiplier = dynamic_mod_table.get(dynam)

    for element in midi.recurse():
        if 'Instrument' in element.classes:
            element.activeSite.replace(element, instr_instance())

    ## check if dynamics is not selected as normal (2), then change velocity, dynam {1,2,3}            
        if (velocity_multiplier != 1):
            if 'Note' in element.classes:
                ## velocity range = {0,127} both inclusive
                element.volume.velocity *= velocity_multiplier        

    ## check if tempo is not selected as normal (2), then change tempo, tem {1,2,3}
    if (tempo_multplier != 1):
        midi = midi.augmentOrDiminish(tempo_multplier) 

    relative_path_output = 'model/MIDI/test_output_' + str(instr_instance()) + 'withdynam_' + str(dynam) + '_withtem_' +str(tem) +'_' +  str(path_leaf(midi_filepath + ".mid"))

    #print(relative_path_output)

    output_path = (cwd / relative_path_output).resolve()

    #print(output_path)

    midi.write('midi', output_path)


    #doing length customization

    # Define a lookup table for modifications of length
    ## for leng = 1 (short) -> 10s, for leng = 2 (medium) -> 20s and for leng = 3(long) -> 30s
    length_mod_table = {1: 10., 2: 20., 3: 30.}
    end_timestamp = length_mod_table.get(leng)

    mid_to_clip = MidiFile(output_path)
    
    output_mid = midi_clip.midi_clip(mid_to_clip, 0., end_timestamp)

    duration = midi_clip.midi_duration(output_mid)

    #print(output_mid, duration)

    relative_path_output = 'model/MIDI/test_output_clip_' + str(instr_instance()) + 'withdynam_' + str(dynam) + '_withtem_' +str(tem) +'_''_withLeng_'+str(leng)+ str(path_leaf(midi_filepath + ".mid"))

    #print(relative_path_output)

    output_path = (cwd / relative_path_output).resolve()

    #print(output_path)

    output_mid.save(output_path)

    result = "" + output_path
    return result

        
def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)