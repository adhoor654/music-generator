import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim



def lrelu(x, leak=0.2):
    z = torch.mul(x,leak)
    return torch.max(x, z)


def l2_loss(x,y):
    loss_ = nn.MSELoss(reduction='sum')
    return loss_(x, y)/2



def batch_norm_1d(x):
    x_shape = x.shape[1]
    batch_norm = nn.BatchNorm1d(x_shape, eps=1e-05, momentum=0.9, affine=True)
    batch_norm = batch_norm.cuda()
    batch_norm = batch_norm

    return batch_norm(x)



def batch_norm_2d(x):
    x_shape = x.shape[1]
    batch_norm = nn.BatchNorm1d(x_shape, eps=1e-05, momentum=0.9, affine=True)
    batch_norm = batch_norm.cuda()
    batch_norm = batch_norm

    return batch_norm(x)


def sigmoid_cross_entropy_with_logits(inputs,labels):
    loss = nn.BCEWithLogitsLoss()
    return loss(inputs, labels)

def conv_prev_concat(x, y):
    x_shapes = x.shape
    y_shapes = y.shape
    if x_shapes[2:] == y_shapes[2:]:
        y2 = y.expand(x_shapes[0],y_shapes[1],x_shapes[2],x_shapes[3])

        return torch.cat((x, y2),1)

    else:
        print(x_shapes[2:])
        print(y_shapes[2:])

def reduce_mean(x):
    output = torch.mean(x,dim=0, keepdim = False)
    output = torch.mean(output,dim=-1, keepdim = False)
    return output


def reduce_mean_0(x):
    output = torch.mean(x,dim=0, keepdim = False)
    return output





