
import torch
import torch.nn as nn
import torch.nn.functional as F
from cnn_gan_ops import *




class Generator(nn.Module):
    def __init__(self,batch_size, c_dim, gf_dim):
        super(Generator, self).__init__()
        self.batch_size = batch_size
        self.c_dim = c_dim
        self.gf_dim = gf_dim

        self.h1      = nn.ConvTranspose2d(in_channels=144, out_channels=self.gf_dim*2, kernel_size=(2,1), stride=(2,2))
        self.h2      = nn.ConvTranspose2d(in_channels=144, out_channels=self.gf_dim*2, kernel_size=(2,1), stride=(2,2))
        self.h3      = nn.ConvTranspose2d(in_channels=144, out_channels=self.gf_dim*2, kernel_size=(2,1), stride=(2,2))
        self.h4      = nn.ConvTranspose2d(in_channels=144, out_channels=1, kernel_size=(1,self.gf_dim*2), stride=(1,2))

        self.h0_prev = nn.Conv2d(in_channels=1, out_channels=16, kernel_size=(1,128), stride=(1,2))
        self.h1_prev = nn.Conv2d(in_channels=16, out_channels=16, kernel_size=(2,1), stride=(2,2))
        self.h2_prev = nn.Conv2d(in_channels=16, out_channels=16, kernel_size=(2,1), stride=(2,2))
        self.h3_prev = nn.Conv2d(in_channels=16, out_channels=16, kernel_size=(2,1), stride=(2,2))

        self.linear1 = nn.Linear(100,1024)
        self.linear2 = nn.Linear(1024,self.gf_dim*2*2*1)

    def forward(self, z, prev_x=None):

        h0_prev = lrelu(batch_norm_2d(self.h0_prev(prev_x)),0.2)   
        h1_prev = lrelu(batch_norm_2d(self.h1_prev(h0_prev)),0.2)  
        h2_prev = lrelu(batch_norm_2d(self.h2_prev(h1_prev)),0.2)  
        h3_prev = lrelu(batch_norm_2d(self.h3_prev(h2_prev)),0.2)  

        h0 = F.relu(self.linear1(z))    

        h1 = F.relu(self.linear2(h0))   
        h1 = h1.view(self.batch_size, self.gf_dim * 2, 2, 1)
        h1 = conv_prev_concat(h1,h3_prev)

        h2 = F.relu(batch_norm_2d(self.h1(h1))) 
        h2 = conv_prev_concat(h2,h2_prev) 
        h3 = F.relu(batch_norm_2d(self.h2(h2))) 
        h3 = conv_prev_concat(h3,h1_prev) 
        h4 = F.relu(batch_norm_2d(self.h3(h3))) 
        h4 = conv_prev_concat(h4,h0_prev)
        g_x = torch.sigmoid(self.h4(h4)) 
        return g_x


class Discriminator(nn.Module):
    def __init__(self,batch_size):
        super(Discriminator, self).__init__()


        self.df_dim = 64
        self.dfc_dim = 1024
        self.batch_size = batch_size



        self.h0_prev = nn.Conv2d(in_channels=1, out_channels=14, kernel_size=(2,128), stride=(2,2))
        self.h1_prev = nn.Conv2d(in_channels=14, out_channels=64, kernel_size=(4,1), stride=(2,2))
        self.linear1 = nn.Linear(192,self.dfc_dim)
        self.linear2 = nn.Linear(1024,1)

    def forward(self,x):

        x= self.h0_prev(x)

        h0 = lrelu(x,0.2)
        fm = h0.clone()


        h1 = self.h1_prev(h0)
        h1 = lrelu(batch_norm_2d(h1),0.2) 
        h1 = h1.view(self.batch_size, -1) 
        print("h1 shape: ",h1.shape)

        h2 = self.linear1(h1)
        h2 = lrelu(h2)
        print("h2 shape:",h2.shape)
        h3 = self.linear2(h2)
        h3_sigmoid = torch.sigmoid(h3)


        return h3_sigmoid, h3, fm


class SampleGenerator(nn.Module):
    def __init__(self,batch_size):
        super(SampleGenerator, self).__init__()
        self.batch_size = batch_size
        self.c_dim = c_dim
        self.gf_dim = gf_dim


        self.h1      = nn.ConvTranspose2d(in_channels=144, out_channels=self.gf_dim*2, kernel_size=(2,1), stride=(2,2))
        self.h2      = nn.ConvTranspose2d(in_channels=144, out_channels=self.gf_dim*2, kernel_size=(2,1), stride=(2,2))
        self.h3      = nn.ConvTranspose2d(in_channels=144, out_channels=self.gf_dim*2, kernel_size=(2,1), stride=(2,2))
        self.h4      = nn.ConvTranspose2d(in_channels=144, out_channels=1, kernel_size=(1,self.gf_dim*2), stride=(1,2))

        self.h0_prev = nn.Conv2d(in_channels=1, out_channels=16, kernel_size=(1,128), stride=(1,2))
        self.h1_prev = nn.Conv2d(in_channels=16, out_channels=16, kernel_size=(2,1), stride=(2,2))
        self.h2_prev = nn.Conv2d(in_channels=16, out_channels=16, kernel_size=(2,1), stride=(2,2))
        self.h3_prev = nn.Conv2d(in_channels=16, out_channels=16, kernel_size=(2,1), stride=(2,2))

        self.linear1 = nn.Linear(100,1024)
        self.linear2 = nn.Linear(1024,self.gf_dim*2*2*1)

    def forward(self, z, prev_x=None):

        h0_prev = lrelu(batch_norm_2d(self.h0_prev(prev_x)),0.2)   
        h1_prev = lrelu(batch_norm_2d(self.h1_prev(h0_prev)),0.2)  
        h2_prev = lrelu(batch_norm_2d(self.h2_prev(h1_prev)),0.2)  
        h3_prev = lrelu(batch_norm_2d(self.h3_prev(h2_prev)),0.2)  


        h0 = F.relu(batch_norm_1d(self.linear1(z)))    


        h1 = F.relu(batch_norm_1d(self.linear2(h0)))   
        h1 = h1.view(self.batch_size, self.gf_dim * 2, 2, 1)   
        h1 = conv_prev_concat(h1,h3_prev)  

        h2 = F.relu(batch_norm_2d(self.h1(h1)))  
        h2 = conv_prev_concat(h2,h2_prev) 
        h3 = F.relu(batch_norm_2d(self.h2(h2))) 
        h3 = conv_prev_concat(h3,h1_prev) 
        h4 = F.relu(batch_norm_2d(self.h3(h3)))  
        h4 = conv_prev_concat(h4,h0_prev) 
        g_x = torch.sigmoid(self.h4(h4)) 
        return g_x

