import glob
import os
import pickle
import numpy
import tensorflow as tf
from tensorflow import keras
#print(tf.version.VERSION)

from music21 import converter, instrument, note, chord, stream
from pathlib import Path
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import Dropout
from keras.layers import LSTM
from keras.layers import Activation
from keras.layers import BatchNormalization as BatchNorm
from keras.utils import np_utils
from keras.callbacks import ModelCheckpoint

def get_notes():
    
    """ Extracts all notes and chords from midi files in the ./MIDI
    directory and creates a file with all notes in string format"""
    
    notes = []

    cwd = Path.cwd()
    print("Current directory: ", cwd)
    relative_path_midi = 'MIDI/'
    relative_path_notes = 'MIDI/data/notes'

    midis_path = (cwd / relative_path_midi).resolve()
    for file in midis_path.glob("*.midi"):
        print(file)

    for file in midis_path.glob("*.midi"):
        midi = converter.parse(file)

        print("Parsing %s" % file)

        notes_to_parse = None

        try: # file has instrument parts
            s2 = instrument.partitionByInstrument(midi)
            notes_to_parse = s2.parts[0].recurse() 
        except: # file has notes in a flat structure
            notes_to_parse = midi.flat.notes

        for element in notes_to_parse:
            if isinstance(element, note.Note):
                notes.append(str(element.pitch))
            elif isinstance(element, chord.Chord):
                notes.append('.'.join(str(n) for n in element.normalOrder))

    notes_path = (cwd / relative_path_notes).resolve()

    with open(notes_path, 'wb') as filepath:
        pickle.dump(notes, filepath)

    return notes


def prepare_sequences(notes, n_vocab):
    
    """ Prepare the sequences which are the inputs for the LSTM """
    
    # sequence length should be changed after experimenting with different numbers (def: 30)
    sequence_length = 10 

    # get all pitch names
    pitchnames = sorted(set(item for item in notes))

    # create a dictionary to map pitches to integers
    note_to_int = dict((note, number) for number, note in enumerate(pitchnames))

    network_input = []
    network_output = []

    # create input sequences and the corresponding outputs
    for i in range(0, len(notes) - sequence_length, 1):
        sequence_in = notes[i:i + sequence_length]
        sequence_out = notes[i + sequence_length]
        network_input.append([note_to_int[char] for char in sequence_in])
        network_output.append(note_to_int[sequence_out])

    n_patterns = len(network_input)

    # reshape the input into a format compatible with LSTM layers
    network_input = numpy.reshape(network_input, (n_patterns, sequence_length, 1))
    # normalize input
    network_input = network_input / float(n_vocab)

    network_output = np_utils.to_categorical(network_output)

    return (network_input, network_output)


def create_network(network_input, n_vocab):
    
    """ Creates the structure of the neural network """
    
    model = Sequential()
    model.add(LSTM(
        512,
        input_shape=(network_input.shape[1], network_input.shape[2]),
        return_sequences=True
    ))
    model.add(Dropout(0.3))
    model.add(LSTM(512, return_sequences=True))
    model.add(Dropout(0.3))
    model.add(LSTM(512))
    model.add(Dense(256))
    model.add(Dropout(0.3))
    model.add(Dense(n_vocab))
    model.add(Activation('softmax'))
    model.compile(loss='categorical_crossentropy', optimizer='rmsprop')

    # see model architecture
    model.summary()

    return model


def train(model, network_input, network_output):
    
    """ Train the neural network """
    
    cwd = Path.cwd()
    relative_path_model = "weights-improvement-{epoch:02d}-{loss:.4f}-bigger.hdf5"
    filepath = (cwd / relative_path_model).resolve()
    checkpoint = ModelCheckpoint(
        filepath,
        monitor='loss',
        verbose=0,
        save_best_only=True,
        mode='min'
    )
    callbacks_list = [checkpoint]

    # experiment with different epoch sizes and batch sizes (def: 30 epochs)
    #model.fit(network_input, network_output, epochs=3, batch_size=64, callbacks=callbacks_list)


def train_network():
    
    """ This function calls all other functions and trains the LSTM"""
    
    notes = get_notes()

    # get amount of pitch names
    n_vocab = len(set(notes))

    network_input, network_output = prepare_sequences(notes, n_vocab)

    model = create_network(network_input, n_vocab)

    train(model, network_input, network_output)


def main():
    train_network()

if __name__ == "__main__":
    main()
  