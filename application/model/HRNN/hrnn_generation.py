# python hrnn_generation.py \
# 	--gen_dir=./test/generated_result \
# 	--logdir_root=logdir/ \
# 	--rhythm_temp=0.4\
# 	--note_temp=0.7

from __future__ import print_function
import argparse
from datetime import datetime
import os
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
import sys
import time
import glob


from collections import defaultdict
from midiutil import MIDIFile
from pypianoroll import Multitrack, Track

import numpy as np
import tensorflow as tf

from model import HRNN
from model import decode_melody,decode_rhythm, rhythm_to_index,index_to_chord, chord_symbol_to_midi_notes

COND_DIRECTORY = './test/test_condition'
GEN_DIR = './test/generated_result'
LOGDIR_ROOT= None

BATCH_SIZE = 1
NUM_GPU = 1

SEED_LENGTH = 8
   

def get_arguments():
    parser = argparse.ArgumentParser(description='HRNN example network')
    parser.add_argument('--num_gpus',         type=int,   default=NUM_GPU)
    parser.add_argument('--cond_dir',         type=str,
                        default=COND_DIRECTORY)
    parser.add_argument('--gen_dir',         type=str,
                        default=GEN_DIR)  
    parser.add_argument('--logdir_root',      type=str,   default=LOGDIR_ROOT)
    parser.add_argument('--note_temp',type=float)
    parser.add_argument('--rhythm_temp',type=float)
    args = parser.parse_args()
    config_file = os.path.join(*args.logdir_root.split("/")[0:-1])+'/config.txt'
    big_frame_size = int(open(config_file).readlines()[1].split(":")[-1][1:-1])
    frame_size = int(open(config_file).readlines()[2].split(":")[-1][1:-1])   
    mode_choice_ckpt = open(config_file).readlines()[4].split(":")[-1][1:-1]
    if_cond_ckpt = open(config_file).readlines()[5].split(":")[-1][1:-1]
    no_rnn = int(open(config_file).readlines()[6].split(":")[-1][1:-1])
    note_channel = int(open(config_file).readlines()[7].split(":")[-1][1:-1])
    rhythm_channel = int(open(config_file).readlines()[8].split(":")[-1][1:-1])
    chord_channel = int(open(config_file).readlines()[12].split(":")[-1][1:-1])
    rnn_type = open(config_file).readlines()[9].split(":")[-1][1:-1]
    dim = int(open(config_file).readlines()[10].split(":")[-1][1:-1])
    try:
        birnndim = int(open(config_file).readlines()[18].split(":")[-1][1:-1])
    except:
        birnndim = 128
    bar_channel = int(open(config_file).readlines()[16].split(":")[-1][1:-1])
    piano_dim = note_channel + rhythm_channel + chord_channel +bar_channel

    class model_arg(object):
        def __init__(self, seq_len, big_frame_size,frame_size,mode_choice,rnn_type,n_rnn,dim, if_cond,piano_dim,note_channel,rhythm_channel,chord_channel,birnndim):
            self.seq_len = seq_len
            self.big_frame_size = big_frame_size
            self.frame_size = frame_size
            self.mode_choice = mode_choice
            self.rnn_type = rnn_type
            self.n_rnn = n_rnn
            self.dim = dim
            self.if_cond = if_cond
            self.piano_dim = piano_dim
            self.note_channel = note_channel
            self.rhythm_channel = rhythm_channel
            self.chord_channel = chord_channel
            self.bar_channel = bar_channel
            self.batch_size =1
            self.alpha1 = 0.5
            self.alpha2 = 0.4
            self.drop_out =1
            self.birnndim = birnndim
            print(self.seq_len,
            self.big_frame_size,
            self.frame_size,
            self.mode_choice,
            self.rnn_type,
            self.n_rnn,
            self.dim,
            self.if_cond,
            self.piano_dim,
            self.note_channel,
            self.rhythm_channel,
            self.chord_channel,
            self.bar_channel,
            self.batch_size,
            self.alpha1,
            self.alpha2,
            self.drop_out)
    
    mod_arg = model_arg(seq_len = 128, big_frame_size = big_frame_size,frame_size = frame_size,
                        mode_choice = mode_choice_ckpt,rnn_type = rnn_type,n_rnn = no_rnn,dim = dim, 
                        if_cond =if_cond_ckpt,piano_dim = piano_dim,note_channel = note_channel,
                        rhythm_channel = rhythm_channel,chord_channel= chord_channel, birnndim = birnndim)

    return args, mod_arg


class define_placeholder(object):
    def __init__(self, net):
        self.infe_para = dict()
        if net.mode_choice=="ad_rm2t_fc":
            self.inpt_lst_dim = net.piano_dim + net.chord_channel
        self.infe_para['infe_big_frame_state'] = net.big_frame_cell.zero_state(net.batch_size,tf.float32)

        self.infe_para['infe_big_frame_inp'] = tf.placeholder(tf.float32, name = "infe_big_frame_inp",shape = [net.batch_size,net.big_frame_size,self.inpt_lst_dim])

        self.infe_para['infe_big_frame_outp'] = tf.placeholder(tf.float32, name = "infe_big_frame_out",shape = [net.batch_size,net.big_frame_size / net.frame_size,net.dim])
        
        self.infe_para['infe_big_frame_outp_slices'] = tf.placeholder(tf.float32, name = "infe_big_frame_outp_slices",shape = [net.batch_size,1,net.dim])

        self.infe_para['infe_frame_inp'] = tf.placeholder(tf.float32, name = "infe_frame_inp",shape = [net.batch_size,net.frame_size,self.inpt_lst_dim])

        self.infe_para['infe_frame_outp'] = tf.placeholder(tf.float32, name = "infe_frame_outp",shape = [net.batch_size,net.frame_size,net.dim])
        
        self.infe_para['infe_frame_state'] = net.frame_cell.zero_state(net.batch_size,tf.float32) 

        self.infe_para['infe_sample_inp'] = tf.placeholder(tf.float32, name = "infe_sample_inp",shape = [net.batch_size,net.frame_size,self.inpt_lst_dim])
        
        self.infe_para['infe_frame_outp_slices'] = tf.placeholder(tf.float32, name = "infe_frame_outp_slices",shape = [net.batch_size,1,net.dim])

        self.infe_para['infe_rm_tm'] = tf.placeholder(tf.float32, name = "infe_rm_tm",shape = [net.batch_size,1,net.rhythm_channel])
        
        self.infe_para['bln_ipt'] = tf.placeholder(tf.float32, name = "infe_bln_ipt",shape = [net.batch_size,1,net.piano_dim+net.chord_channel])

        self.infe_para['bln_state'] = net.sample_cell.zero_state(net.batch_size,tf.float32)

        self.infe_para['bln_attn_state'] = net.attn_cell.zero_state(net.batch_size,tf.float32)

        print("initialize placeholder", self.infe_para['infe_big_frame_state'],self.infe_para['infe_big_frame_inp'] ,self.infe_para['infe_big_frame_outp'])

def choose_from_distribution(preds, temperature=1.0):

    preds = np.asarray(preds).astype('float64')
    return_array = np.zeros_like(preds)
    preds = np.log(preds[0]) / temperature
    exp_preds = np.exp(preds)
    preds = exp_preds / np.sum(exp_preds)
    probas = np.random.multinomial(1, preds, 1)
    return_array[:,np.argmax(probas)] = 1
    return return_array

def decode_event_slice(event_slice, net, ignore_bar_event = True):
    CHORD_CHANNELS_REST = net.chord_channel
    RHYTHMS_CHANNELS = net.rhythm_channel

    rhythm_info = np.argmax(event_slice[CHORD_CHANNELS_REST:CHORD_CHANNELS_REST+RHYTHMS_CHANNELS])
    melody_info = np.argmax(event_slice[CHORD_CHANNELS_REST+RHYTHMS_CHANNELS:])
    chord_info = np.argmax(event_slice[:CHORD_CHANNELS_REST])

    melody = decode_melody(melody_info, ignore_bar_event)
    rhythm = decode_rhythm(rhythm_info, ignore_bar_event)  
    chord = index_to_chord(chord_info, ignore_bar_event)    

    return melody, rhythm, chord
def check_if_start_bar(bar_info_at_pos):
    if np.argmax(bar_info_at_pos)==1:
        return True
    else:
        return False
def generate_midi(np_file, mid_name, net ,original_file,if_save = True):

    np_f = np.load(np_file)[0]
    bar_info = np_f[:,:net.bar_channel]
    np_f = np_f[:, net.bar_channel:]
    if not net.if_cond:
        np_f = np.concatenate((original_file[0][:,net.bar_channel:net.bar_channel+net.chord_channel], np_f), axis = -1)
    MyMIDI = MIDIFile(numTracks=2,ticks_per_quarternote=220) #track0 is melody, track1 is chord
    MyMIDI_eva = MIDIFile(numTracks=1,ticks_per_quarternote=220) #track0 is melody

    cum_time = float(0)
    ##melody track: melody + rhythm
    for pos, event_slice in enumerate(np_f): 
        melody, rhythm, _ = decode_event_slice(event_slice, net,ignore_bar_event = True)
        if melody==1: 
            continue
        else:
            #check future pos whether sustain
            next_pos = pos + 1 
            if next_pos<=len(np_f)-1:
                melody_next, rhythm_next, _ = decode_event_slice(np_f[next_pos], net,ignore_bar_event = True)
                while(melody_next == 1 and next_pos<=len(np_f)-1):
                    rhythm += rhythm_next
                    next_pos+=1
                    try:
                        melody_next, rhythm_next, _ = decode_event_slice(np_f[next_pos], net,ignore_bar_event = True)
                    except:
                        melody_next = "break the loop"
                        rhythm_next = "break the loop"
            on_time = cum_time
            dur = rhythm
            if melody==0:
                cum_time = on_time+rhythm
            else:
                MyMIDI.addNote(track = 0, channel = 0, pitch = melody, time = on_time, duration = dur, volume = 100)
                MyMIDI_eva.addNote(track = 0, channel = 0, pitch = melody, time = on_time, duration = dur, volume = 100)
                cum_time = on_time+rhythm

    ##chord track: chord + rhythm
    cum_time = float(0)
    ignore_pos = []
    for pos, event_slice in enumerate(np_f):

        _, rhythm, chord = decode_event_slice(event_slice, net,ignore_bar_event = True)
        if pos in ignore_pos:
            continue

        next_pos = pos + 1 
        if next_pos<=len(np_f)-1:
            
            _, rhythm_next, chord_next = decode_event_slice(np_f[next_pos],net,ignore_bar_event = True)
            
            while(chord_next == chord and next_pos<=len(np_f)-1):

                ignore_pos.append(next_pos)
                rhythm += rhythm_next
                next_pos+=1
                try:
                    _, rhythm_next, chord_next = decode_event_slice(np_f[next_pos],net,ignore_bar_event = True)
                except:
                    rhythm_next = "break the loop"
                    chord_next = "break the loop"
            on_time = cum_time
            dur = rhythm
            if chord==("rest","rest"):
                cum_time = on_time+rhythm
            else:
                chord_notes = chord_symbol_to_midi_notes(chord)
                for chord_note in chord_notes:
                    chord_note = int(chord_note)
                    chord_note+=60
                    MyMIDI.addNote(track = 1, channel = 0, pitch = chord_note, time = on_time, duration = dur, volume = 100)
                cum_time = on_time+rhythm


    if if_save:
        print("saving to {} ".format(mid_name))
        mid_eva_name = mid_name[:-4]+"_eva.mid"
        with open(mid_name, "wb") as output_file:
            MyMIDI.writeFile(output_file)     
            print("{} has been updated".format(mid_name))
        with open(mid_eva_name, "wb") as output_file2:
            MyMIDI_eva.writeFile(output_file2)     
            print("{} has been updated".format(mid_eva_name))

def create_graph_ad_rm2t_fc(net):
    with tf.name_scope('infe_para'):
        infe_para = define_placeholder(net).infe_para

        tf.get_variable_scope().reuse_variables()

        infe_para['infe_frame_outp'], infe_para['infe_next_frame_state'] = net.frame_level_switch(
                frame_input=infe_para['infe_frame_inp'],
                frame_state = infe_para['infe_frame_state']
        )

        pd_sustain, pd_bar, pd_note = net.sample_level_tweek_last_layer(
            frame_output=infe_para['infe_frame_outp_slices'],
            sample_input_sequences=infe_para['infe_sample_inp'],
            rm_time=infe_para['infe_rm_tm']
        )

        infe_para['note'] = tf.nn.softmax(pd_note[0])
        infe_para['rhythm'] = tf.nn.softmax(pd_sustain[0])
        infe_para['bar'] = tf.nn.softmax(pd_bar[0])
        return infe_para


def find_rm_tm_array(net, samples,current_time):
    rm_tm_array = np.zeros((net.batch_size,1,net.rhythm_channel))
    #current_time = t
    prev_time = current_time-1
    while np.argmax(samples[0][prev_time][:net.bar_channel])!=1:
        prev_time -= 1
    duration_accumulated = 0
    for idx in range(prev_time,current_time):
        duration_raw = np.argmax(samples[0][idx][net.bar_channel+2*net.chord_channel: net.bar_channel+2*net.chord_channel+net.rhythm_channel])
        duration = decode_rhythm(duration_raw,ignore_bar_event = True)
        duration_accumulated+=duration
    duration_left_raw = duration_accumulated
    if duration_left_raw>4:
        print("dur warning",duration_accumulated)
        duration_left_raw = 4
    rm_duration_idx = rhythm_to_index(duration_left_raw)
    rm_tm_array[:,:,rm_duration_idx] = 1
    return rm_tm_array

def sample_from_distribution(net,args,sample_out_note_distribution, rhythm_out_distribution,bar_out_distribution, chord_this_time):

    sample_out_note = choose_from_distribution(sample_out_note_distribution, temperature = args.note_temp)
    sample_out_rhythm = choose_from_distribution(rhythm_out_distribution, temperature = args.rhythm_temp)
    sample_out_bar = choose_from_distribution(bar_out_distribution,temperature = 0.1)
    if net.if_cond:
        sample_ori_chord = chord_this_time
        return np.concatenate((sample_out_bar,sample_ori_chord, sample_out_rhythm, sample_out_note), axis = 1)
    else:
        return np.concatenate((sample_out_bar,sample_out_rhythm, sample_out_note), axis = 1)

def forward_prop(net, infe_para, sess, condition, condition_name, gen_dir,args,seed_length,mode_choice):
    #prepare input
    for i in range(len(condition)-1,0,-1):
        if np.argmax(condition[i][net.bar_channel:net.bar_channel+net.chord_channel])!=0:
            print("chord is rest")
            break
        else:
            trim_index = i
    condition = condition[:trim_index, :]
    LENGTH = condition.shape[0]
    rest_chord = np.zeros((1,net.chord_channel))
    rest_chord[:,0] = 1
    all_chords= condition[:,net.bar_channel:net.bar_channel+net.chord_channel] #(len, chord_dim)
    shifted_chord = np.concatenate((all_chords[1:,:],rest_chord),axis = 0) 
    condition_with_fc_chord = np.concatenate((condition[:,:net.bar_channel],shifted_chord,condition[:,net.bar_channel:]),axis = -1)
    original_file= np.reshape(condition_with_fc_chord,(net.batch_size, LENGTH, net.piano_dim+net.chord_channel))
    samples = np.zeros((net.batch_size, LENGTH, net.piano_dim+net.chord_channel), dtype='float32')
    samples[:, :seed_length, :] = original_file[:,:seed_length, :]
    #run graph based on choice
    final_big_s, final_s, bln_s, bln_attn_s= sess.run([net.big_frame_init, net.frame_init, net.sample_init, net.attn_cell_init])
    if mode_choice == "ad_rm2t_fc":
        for t in range(net.frame_size, LENGTH):
            # frame level
            if t % net.frame_size == 0: #if (t - net.frame_size) % net.frame_size == 0:
                frame_input_sequences = samples[: , t - net.frame_size:t, :]
                frame_out, final_s = sess.run(
                    [   infe_para['infe_frame_outp'],
                        infe_para['infe_next_frame_state']],
                    feed_dict={
                        infe_para['infe_frame_inp']: frame_input_sequences,
                        infe_para['infe_frame_state']: final_s})
            # sample level
            sample_input_sequences = samples[:, t-net.frame_size:t, :]
            frame_output_idx = t % net.frame_size
            #find rm_tm array
            rm_tm_array = find_rm_tm_array(net,samples, current_time = t)

            sample_out_note_distribution, rhythm_out_distribution, bar_out_distribution= sess.run(
                [infe_para['note'],infe_para["rhythm"],infe_para["bar"]
                ],
                feed_dict={ infe_para['infe_frame_outp_slices']: np.expand_dims(frame_out[: , frame_output_idx, :], axis = 1),
                            infe_para['infe_sample_inp']: sample_input_sequences,
                            infe_para['infe_rm_tm']:rm_tm_array} )

            samples[:, t] = sample_from_distribution(net,args,sample_out_note_distribution, rhythm_out_distribution,bar_out_distribution, chord_this_time = original_file[:, t, net.bar_channel:net.bar_channel+2*net.chord_channel])

    data_genre = args.logdir_root.split("/")[-2]
    ckpt = args.logdir_root.split("/")[-1].split("-")[-1]
    seed_length = str(seed_length)
    temp = str(args.note_temp)+"_"+str(args.rhythm_temp)
    unique_name = "_".join((data_genre,ckpt,seed_length,temp,condition_name))

    melody_npy = os.path.join(gen_dir,unique_name+'.npy')
    melody_mid = os.path.join(gen_dir,unique_name+'.mid')
    samples_wo_fc = np.delete(samples,np.s_[net.bar_channel:net.bar_channel+net.chord_channel],axis=-1)
 
    np.save(melody_npy,samples_wo_fc)
    generate_midi(melody_npy, melody_mid, net, original_file)

def preprocess_condition(condition_dir, seed_length):
    cond_file_list = []
    for condition_name in condition_dir:
        condition = np.load(condition_name)
        if condition.shape[0]<=seed_length:
            continue
        condition_name = condition_name.split('/')[-1].split(".")[0]
        pair = (condition,condition_name)
        cond_file_list.append(pair)
    return cond_file_list

def main():

    ####retrieve config####
    args, mod_arg= get_arguments()

    #print(args_model)
    net = HRNN(args = mod_arg, if_train = False)

    if mod_arg.if_cond == "cond":
        network_input_plder= tf.placeholder(tf.float32,shape =(None, mod_arg.seq_len, mod_arg.piano_dim+mod_arg.chord_channel), name = "input_batch_rnn")

        if mod_arg.mode_choice=="ad_rm2t_fc" :
            rm_time_plder = tf.placeholder(tf.float32,shape =(None, mod_arg.seq_len-mod_arg.frame_size, mod_arg.rhythm_channel), name = "rm_tm_rnn")
            network_output_plder = tf.placeholder(tf.float32,shape =(None, mod_arg.seq_len-mod_arg.frame_size, mod_arg.piano_dim-mod_arg.chord_channel), name = "output_batch_rnn")

    else:
        if mod_arg.mode_choice=="ad_rm2t":
            network_input_plder= tf.placeholder(tf.float32,shape =(None, mod_arg.seq_len, mod_arg.piano_dim-mod_arg.chord_channel), name = "input_batch_rnn")
            rm_time_plder = tf.placeholder(tf.float32,shape =(None, mod_arg.seq_len-mod_arg.frame_size, mod_arg.rhythm_channel), name = "rm_tm_rnn")
            network_output_plder = tf.placeholder(tf.float32,shape =(None, mod_arg.seq_len-mod_arg.frame_size, mod_arg.piano_dim-mod_arg.chord_channel), name = "output_batch_rnn")

    ##build graph##
    with tf.variable_scope(tf.get_variable_scope(),reuse = tf.AUTO_REUSE):
        with tf.name_scope('TOWER_0') as scope:
            if mod_arg.mode_choice=="ad_rm2t_fc":
                (   gt,
                    pd,
                    loss
                )=net.loss_HRNN(
                    X = network_input_plder,
                    y = network_output_plder,
                    rm_time= rm_time_plder
                )                
            tf.get_variable_scope().reuse_variables()

    ####sess config####
    tf_config = tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)
    tf_config.gpu_options.allow_growth = True
    saver = tf.train.Saver()

    if mod_arg.mode_choice =="ad_rm2t_fc":
        graph= create_graph_ad_rm2t_fc(net)

    logdir = args.logdir_root
    gen_dir = args.gen_dir
    temp = str(args.note_temp)+"_"+str(args.rhythm_temp)
    logdir_path = logdir.split('/')[-2] 
    model_name = logdir.split('/')[-1] 
    model_number = model_name.split('-')[-1]
    if mod_arg.mode_choice=="ad_rm2t_fc":
        seed_length = mod_arg.frame_size
    
    gen_dir_model_number = gen_dir +'/'+logdir_path+ '/'+model_number+'/'+str(seed_length)+"/"+temp
    if not os.path.exists(gen_dir_model_number):
        os.makedirs(gen_dir_model_number)

    ####condition input####
    test_file_list = preprocess_condition(glob.glob(args.cond_dir+'/*.npy'), seed_length)  #(condition, condition_name)
    ####restore session####
    session = tf.Session(config=tf_config)

    with session as sess:
        saver.restore(sess, logdir)
        count = 0
        total_count = len(test_file_list)
        for original_test_file,file_name in test_file_list:
            print('Processing',file_name)
            print("process:{}/{}".format(count,total_count))
            t_start = time.time()

            forward_prop(net, graph, sess, original_test_file, file_name, gen_dir_model_number, args, int(seed_length),mod_arg.mode_choice)

            t_end = time.time()
            count+=1
            print(file_name,' processing time: ', t_end-t_start)
    
if __name__ == '__main__':
    main()

