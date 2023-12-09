import os
import re
import threading
import sys
import copy
import numpy as np
import tensorflow as tf
import glob
import argparse
from .val_search import rhythm_to_index,decode_rhythm
class InputHandler(object):
    def __init__(self,coord, args, queue_size=16):
        self.audio_dir = args.data_dir
        self.validation_dir = args.val_data_dir
        self.piano_dim = args.bar_channel + args.chord_channel + args.rhythm_channel+ args.note_channel
        self.note_channel = args.note_channel
        self.rhythm_channel = args.rhythm_channel
        self.chord_channel = args.chord_channel
        self.bar_channel = args.bar_channel
        self.coord = coord
        self.seq_len = args.seq_len
        self.big_frame_size = args.big_frame_size
        self.frame_size = args.frame_size
        self.mode_choice = args.mode_choice
        self.if_cond = True if args.if_cond=="cond" else False
        self.threads = []
        self.X = tf.placeholder(dtype=tf.float32, shape=None)
        self.Y = tf.placeholder(dtype=tf.float32, shape=None)
        self.rm_tm = tf.placeholder(dtype=tf.float32, shape=None)
        if self.mode_choice =="ad_rm2t_fc":
            self.queue = tf.PaddingFIFOQueue(
                    capacity = queue_size, dtypes=[tf.float32, tf.float32, tf.float32], shapes=[(None, self.piano_dim+self.chord_channel), (None, self.piano_dim-self.chord_channel), (None, self.rhythm_channel)])
            self.enqueue = self.queue.enqueue([self.X, self.Y, self.rm_tm])

    def dequeue(self, num_elements):
        output = self.queue.dequeue_many(num_elements)
        return output

    def encode_npy(self, mid_files):
        npy_lst = []
        for mid_file in mid_files:
            mid = np.load(mid_file)
            npy_lst.append(mid)
        print("encoding........FINISHED!")
        return npy_lst

    def find_remaining_time(self,ipt,prev_len):
        #ipt [len, dim]
        #opt [len - prev_len, rhythm_channel]
        out_lst = []
        for t in range(prev_len, len(ipt)):
            #print("hey",t)
            current_time = t
            prev_time = t-1
            while np.argmax(ipt[prev_time][:self.bar_channel])!=1:
                prev_time -= 1
            duration_accumulated = 0
            for idx in range(prev_time,current_time):
                duration_raw = np.argmax(ipt[idx][self.bar_channel+self.chord_channel: self.bar_channel+self.chord_channel+self.rhythm_channel])
                duration = decode_rhythm(duration_raw,ignore_bar_event = True)
                duration_accumulated+=duration
            duration_left_raw = duration_accumulated
            rm_duration_idx = rhythm_to_index(duration_left_raw)
            duration_left = np.zeros((self.rhythm_channel,))
            duration_left[rm_duration_idx,] = 1

            out_lst.append(duration_left) #in the end will be [(1,16),(1,16) ]
        output = np.stack(out_lst, axis = 0)
        return output       
    
    def prepare_all_data(self,audio, all_xy_lst):
        if not self.if_cond:
            audio = np.delete(audio,np.s_[self.bar_channel:self.bar_channel+self.chord_channel],axis=1)
      
        if self.mode_choice=="ad_rm2t_fc":
            #make sure data starts with a bar event
            for i in range(len(audio)):
                if np.argmax(audio[i][:self.bar_channel])==1:
                    trim_index = i
                    break
            audio = audio[trim_index:]

            seq_list_tmp = [] 
            ground_truth_tmp = []
            rm_tm_tmp = []
            rest_chord = np.zeros((1,self.chord_channel))
            rest_chord[:,0] = 1
            while len(audio) >= self.seq_len:
                #make sure X starts with a bar event
                X = audio[:self.seq_len, :]
                all_chords_forX = X[:,self.bar_channel:self.bar_channel+self.chord_channel] #(len, chord_dim)
                shifted_chord = np.concatenate((all_chords_forX[1:,:],rest_chord),axis = 0) 
                X_with_fc_chord = np.concatenate((X[:,:self.bar_channel],shifted_chord,X[:,self.bar_channel:]),axis = -1)

                #y is okay, no pre-process needed
                y = X[self.frame_size:,:]
                gt = np.delete(y,np.s_[self.bar_channel:self.bar_channel+self.chord_channel],axis=1)

                #process remaining time lst
                rm_time_output = self.find_remaining_time(X, prev_len = self.frame_size) #(len-framesize, rhythm_channel)
                seq_list_tmp.append(X_with_fc_chord)  
                ground_truth_tmp.append(gt)
                rm_tm_tmp.append(rm_time_output)
                audio = audio[self.seq_len:, :]
            X_y_lst = zip(seq_list_tmp, ground_truth_tmp, rm_tm_tmp) #[(X,y,z), (X,y,z) ]
            all_xy_lst.extend(X_y_lst)

        return all_xy_lst
    def thread_main2(self, sess):
        stop = False
        mid_files = glob.glob(self.audio_dir+'/*.npy')
        npy_lst = [(mid_file,np.load(mid_file)) for mid_file in mid_files]
        all_xyz_lst = []

        for npy_name, npy_file in npy_lst:
            all_xyz_lst = self.prepare_all_data(npy_file, all_xyz_lst)
        
        while not stop:
            if self.mode_choice=="ad_rm2t_fc":
                for xyz in all_xyz_lst:
                    if self.coord.should_stop():
                        stop = True
                        break
                    sess.run(self.enqueue,feed_dict={self.X: xyz[0], self.Y: xyz[1], self.rm_tm: xyz[2]})  

    def start_threads(self, sess, n_threads=1):
        for _ in range(n_threads):
            thread = threading.Thread(target=self.thread_main2, args=(sess,))
            thread.daemon = True  # Thread will close when parent quits.
            thread.start()
            self.threads.append(thread)
        return self.threads     
        
    def get_validation_data(self):
        val_files = glob.glob(self.validation_dir+'/*.npy')

        npy_lst = [(mid_file,np.load(mid_file)) for mid_file in val_files]

        all_xyz_lst = []
        for npy_name, npy_file in npy_lst:
            all_xyz_lst = self.prepare_all_data(npy_file, all_xyz_lst)


        if self.mode_choice=="ad_rm2t_fc":
            X_lst, y_lst,z_lst = zip(*all_xyz_lst)
            X = np.stack(X_lst, axis = 0)
            y = np.stack(y_lst, axis = 0)
            z = np.stack(z_lst, axis = 0)
            return X, y, z        

if __name__=='__main__':

    parser = argparse.ArgumentParser(description='HRNN example network')
    parser.add_argument('--data_dir', type=str,default="AUDIO/train/")
    parser.add_argument('--val_data_dir',type=str,default = "AUDIO/val/")                  

    parser.add_argument('--seq_len',          type=int, default = 128)
    parser.add_argument('--big_frame_size',   type=int, default = 32)
    parser.add_argument('--frame_size',       type=int, default = 16)

    parser.add_argument('--mode_choice', choices=["ad_rm2t_fc"], type = str,default="ad_rm2t_fc")
    parser.add_argument('--if_cond',type=str, choices=['cond','no_cond'], default = "cond")
    parser.add_argument('--note_channel',type=int, default = 130)
    parser.add_argument('--rhythm_channel',type=int, default = 16)
    parser.add_argument('--chord_channel',type=int, default = 49)
    parser.add_argument('--bar_channel',type=int, default = 2)
    args =  parser.parse_args()


    tf_config = tf.ConfigProto(allow_soft_placement=True, log_device_placement=False)
    tf_config.gpu_options.allow_growth = True
    coorder = tf.train.Coordinator()
    sess = tf.Session(config=tf_config)
    init = tf.global_variables_initializer()
    sess.run(init)
    threads = tf.train.start_queue_runners(sess=sess, coord=coorder)
    reader = InputHandler(coord = coorder, args = args)
    print('init finish')
    reader.start_threads(sess)
    print('threads started')
    audio_batch = reader.dequeue(4)
    print('deququed')
    if args.mode_choice=="ad_rm2t_fc":
        X_train, y_train,rm_time = sess.run(audio_batch)
        X, y,rm_time_val = reader.get_validation_data()
        print(X_train.shape, y_train.shape,rm_time.shape)
        print(X.shape, y.shape,rm_time_val.shape)
        """np.save("X.npy",X_train)
        np.save("y.npy",y_train)
        np.save("rm.npy",rm_time)  """    
