import numpy as np 
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import torch.optim as optim
import ipdb
import torchvision.utils as vutils
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from cnn_gan_model import *
from cnn_gan_ops import *
from sklearn.utils import shuffle

class DataLoaderWrapper(object):
    def __init__(self, data, prev_data):
        self.size = data.shape[0]
        self.data = torch.from_numpy(data).float()
        self.prev_data = torch.from_numpy(prev_data).float()
        
    def __getitem__(self, index):
        return self.data[index],self.prev_data[index] 
    def __len__(self):
        return self.size

def load_data():
    check_range_st = 0
    check_range_ed = 129
    X_tr = np.load("data")
    prev_X_tr = np.load("prev data")
    X_tr = np.transpose(X_tr,(0,1,3,2))
    prev_X_tr = np.transpose(prev_X_tr,(0,1,3,2))
    X_tr = X_tr[:,:,:,check_range_st:check_range_ed]
    prev_X_tr = prev_X_tr[:,:,:,check_range_st:check_range_ed]
    X_tr, prev_X_tr = shuffle(X_tr,prev_X_tr, random_state=0)

    train_iter = DataLoaderWrapper(X_tr,prev_X_tr)
    kwargs = {'num_workers': 2, 'pin_memory': True}
    train_loader = DataLoader(
                   train_iter, batch_size=4, shuffle=True, **kwargs)

    print('data prep completed')
    #######################################
    return train_loader
def main():
    is_train = 1
    is_draw = 0
    is_sample = 0

    epochs = 2
    lr = 0.0002

    check_range_st = 0
    check_range_ed = 129
    batch_size = 4

    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader = load_data()
    c_dim = 1
    gf_dim = 64
    if is_train == 1 :
        netG = Generator(batch_size,c_dim,gf_dim).to(device)
        netD = Discriminator(batch_size).to(device)

        netD.train()
        netG.train()
        optimizerD = optim.Adam(netD.parameters(), lr=lr, betas=(0.5, 0.999))
        optimizerG = optim.Adam(netG.parameters(), lr=lr, betas=(0.5, 0.999))
        nz = 100
        fixed_noise = torch.randn(batch_size, nz, device=device)
        real_label = 1
        fake_label = 0
        average_lossD = 0
        average_lossG = 0
        average_D_x   = 0
        average_D_G_z = 0

        lossD_list =  []
        lossD_list_all = []
        lossG_list =  []
        lossG_list_all = []
        D_x_list = []
        D_G_z_list = []
        for epoch in range(epochs):
            sum_lossD = 0
            sum_lossG = 0
            sum_D_x   = 0
            sum_D_G_z = 0
            for i, (data,prev_data) in enumerate(train_loader, 0):

                ############################
                # (1) Update D network: maximize log(D(x)) + log(1 - D(G(z)))
                ###########################
                # train with real
                netD.zero_grad()
                real_cpu = data.to(device)
                prev_data_cpu = prev_data.to(device)

                print("real shape",real_cpu.shape)
                print("prev_data shape",prev_data_cpu.shape)
                batch_size = real_cpu.size(0)
                print("batch_size",batch_size)
                label = torch.full((batch_size,), real_label, device=device)
                D, D_logits, fm = netD(real_cpu)
                print("D, D_logits",D, D_logits)

                #####loss
                d_loss_real = reduce_mean(sigmoid_cross_entropy_with_logits(D_logits, 0.9*torch.ones_like(D)))
                d_loss_real.backward(retain_graph=True)
                D_x = D.mean().item()
                sum_D_x += D_x

                # train with fake
                noise = torch.randn(batch_size, nz, device=device)
                fake = netG(noise,prev_data_cpu)
                print("fake",fake)
                label.fill_(fake_label)
                D_, D_logits_, fm_ = netD(fake.detach())
                d_loss_fake = reduce_mean(sigmoid_cross_entropy_with_logits(D_logits_, torch.zeros_like(D_)))

                d_loss_fake.backward(retain_graph=True)
                D_G_z1 = D_.mean().item()
                errD = d_loss_real + d_loss_fake
                errD = errD.item()
                lossD_list_all.append(errD)
                sum_lossD += errD
                optimizerD.step()

                ############################
                # (2) Update G network: maximize log(D(G(z)))
                ###########################
                netG.zero_grad()
                label.fill_(real_label)  # fake labels are real for generator cost
                D_, D_logits_, fm_= netD(fake)

                ###loss
                g_loss0 = reduce_mean(sigmoid_cross_entropy_with_logits(D_logits_, torch.ones_like(D_)))
                #Feature Matching
                features_from_g = reduce_mean_0(fm_)
                features_from_i = reduce_mean_0(fm)
                fm_g_loss1 =torch.mul(l2_loss(features_from_g.detach()*1.0, features_from_i.detach()*1.0), 0.1)

                mean_image_from_g = reduce_mean_0(fake)
                smean_image_from_i = reduce_mean_0(real_cpu)
                fm_g_loss2 = torch.mul(l2_loss(mean_image_from_g.detach()*1.0, smean_image_from_i.detach()*1.0), 0.01)

                errG = g_loss0 + fm_g_loss1 + fm_g_loss2
                errG.backward(retain_graph=True)
                D_G_z2 = D_.mean().item()
                optimizerG.step()

                ############################
                # (3) Update G network again: maximize log(D(G(z)))
                ###########################
                netG.zero_grad()
                label.fill_(real_label)  # fake labels are real for generator cost
                D_, D_logits_, fm_ = netD(fake)

                ###loss
                g_loss0 = reduce_mean(sigmoid_cross_entropy_with_logits(D_logits_, torch.ones_like(D_)))
                #Feature Matching
                features_from_g = reduce_mean_0(fm_)
                features_from_i = reduce_mean_0(fm)
                loss_ = nn.MSELoss(reduction='sum')
                feature_l2_loss = loss_(features_from_g, features_from_i)/2
                fm_g_loss1 =torch.mul(feature_l2_loss, 0.1)

                mean_image_from_g = reduce_mean_0(fake)
                smean_image_from_i = reduce_mean_0(real_cpu)
                mean_l2_loss = loss_(mean_image_from_g, smean_image_from_i)/2
                fm_g_loss2 = torch.mul(mean_l2_loss, 0.01)
                errG = g_loss0 + fm_g_loss1 + fm_g_loss2
                sum_lossG +=errG
                errG.backward()
                lossG_list_all.append(errG.item())

                D_G_z2 = D_.mean().item()
                sum_D_G_z += D_G_z2
                optimizerG.step()

                if epoch % 1 == 0:
                    print('[%d/%d][%d/%d] Loss_D: %.4f Loss_G: %.4f D(x): %.4f D(G(z)): %.4f / %.4f'
                          % (epoch, epochs, i, len(train_loader),
                             errD, errG, D_x, D_G_z1, D_G_z2))

                if i % 10 == 0:
                    vutils.save_image(real_cpu,
                            '%s/real_samples.png' % 'file',
                            normalize=True)
                    fake = netG(fixed_noise,prev_data_cpu)
                    vutils.save_image(fake.detach(),
                            '%s/fake_samples_epoch_%03d.png' % ('file', epoch),
                            normalize=True)

            average_lossD = (sum_lossD / len(train_loader.dataset))
            average_lossG = (sum_lossG / len(train_loader.dataset))
            average_D_x = (sum_D_x / len(train_loader.dataset))
            average_D_G_z = (sum_D_G_z / len(train_loader.dataset))

            lossD_list.append(average_lossD)
            lossG_list.append(average_lossG)
            D_x_list.append(average_D_x)
            D_G_z_list.append(average_D_G_z)

            print('==> Epoch: {} Average lossD: {:.10f} average_lossG: {:.10f},average D(x): {:.10f},average D(G(z)): {:.10f} '.format(
              epoch, average_lossD,average_lossG,average_D_x, average_D_G_z))

        np.save('lossD_list.npy',lossD_list)
        np.save('lossG_list.npy',lossG_list)
        np.save('lossD_list_all.npy',lossD_list_all)
        np.save('lossG_list_all.npy',lossG_list_all)
        np.save('D_x_list.npy',D_x_list)
        np.save('D_G_z_list.npy',D_G_z_list)

        # do checkpointing
        torch.save(netG.state_dict(), '%s/netG_epoch_%d.pth' % ('../models', epoch))
        torch.save(netD.state_dict(), '%s/netD_epoch_%d.pth' % ('../models', epoch))

    if is_draw == 1:
        lossD_print = np.load('lossD_list.npy')
        lossG_print = np.load('lossG_list.npy')
        length = lossG_print.shape[0]

        x = np.linspace(0, length-1, length)
        x = np.asarray(x)
        plt.figure()
        plt.plot(x, lossD_print,label=' lossD',linewidth=1.5)
        plt.plot(x, lossG_print,label=' lossG',linewidth=1.5)

        plt.legend(loc='upper right')
        plt.xlabel('data')
        plt.ylabel('loss')
        plt.savefig('where you want to save/lr='+ str(lr) +'_epoch='+str(epochs)+'.png')

    if is_sample == 1:
        batch_size = 4
        nz = 100
        n_bars = 7
        X_te = np.load(' testing x')
        prev_X_te = np.load(' testing prev x')
        prev_X_te = prev_X_te[:,:,check_range_st:check_range_ed,:]

        test_iter = DataLoaderWrapper(X_te,prev_X_te,y_te)
        kwargs = {'num_workers': 4, 'pin_memory': True}# if args.cuda else {}
        test_loader = DataLoader(test_iter, batch_size=batch_size, shuffle=False, **kwargs)

        netG = SampleGenerator()
        netG.load_state_dict(torch.load('your model'))

        output_songs = []
        for i, (data,prev_data) in enumerate(test_loader, 0):
            list_song = []
            first_bar = data[0].view(1,1,16,128)
            list_song.append(first_bar)


            noise = torch.randn(batch_size, nz)

            for bar in range(n_bars):
                z = noise[bar].view(1,nz)
                if bar == 0:
                    prev = data[0].view(1,1,16,128)
                else:
                    prev = list_song[bar-1].view(1,1,16,128)
                sample = netG(z, prev)
                list_song.append(sample)

            print('num of output_songs: {}'.format(len(output_songs)))
            output_songs.append(list_song)
        np.save('output_songs.npy',np.asarray(output_songs))
        print('done creating')