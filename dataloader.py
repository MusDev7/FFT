import json
import logging
import os
import random
# import coordinate_conversion as cc
import numpy as np
import torch
import torch.utils.data as tu_data
from tqdm import tqdm


class DataGenerator:
    def __init__(self, data_path, minibatch_len, interval=1, scale_method='minmax', data_statistics_path='./data_statistics.json', retrieve_data=False, data_percentage=1.0,
                 train=True, test=True, dev=True, train_shuffle=True, test_shuffle=False, dev_shuffle=False):
        assert os.path.exists(data_path)
        # self.attr_names = ['lon', 'lat', 'alt', 'spdx', 'spdy', 'spdz']
        self.attr_names = ['lat', 'lon', 'hdg', 'kph', 'alt', 'roc']
        self.data_path = data_path
        self.interval = interval
        self.minibatch_len = minibatch_len
        self.scale_method = scale_method
        self.retrieve_data = retrieve_data
        self.data_percentage = min(max(0., data_percentage), 1.)
        with open(data_statistics_path, 'r') as f:
            self.data_statistics = json.load(f)
        self.rng = random.Random(123)
        self.readtxt = self.readtxt_data if retrieve_data else self.readtxt_idx
        if train:
            self.train_set = mini_DataGenerator(self.readtxt(os.path.join(self.data_path, 'train'), shuffle=train_shuffle))
        if dev:
            self.dev_set = mini_DataGenerator(self.readtxt(os.path.join(self.data_path, 'dev'), shuffle=dev_shuffle))
        if test:
            self.test_set = mini_DataGenerator(self.readtxt(os.path.join(self.data_path, 'test'), shuffle=test_shuffle))
        print('data percentage:', self.data_percentage)
        print('data statistics:', self.data_statistics)

    def readtxt_idx(self, txt_path, shuffle=True):
        data = []
        with tqdm(desc=f'Loading files from {txt_path}', total=sum(len(files) for _, _, files in os.walk(txt_path))) as pbar:
            for root, dirs, files in os.walk(txt_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    with open(file_path, 'r') as f:
                        line_count = len(f.readlines())
                    idx = list(range(line_count))[::self.interval]
                    if len(idx) == self.minibatch_len:
                        if random.random() <= self.data_percentage:
                            data.append((os.path.relpath(file_path, self.data_path), 0))
                    elif len(idx) < self.minibatch_len:
                        continue
                    else:
                        for i in range(len(idx)-self.minibatch_len+1):
                            if random.random() <= self.data_percentage:
                                data.append((os.path.relpath(file_path, self.data_path), i))
                    pbar.update(1)
        print(f'{len(data)} items loaded from \'{txt_path}\'')
        if shuffle:
            random.shuffle(data)
        return data
    
    def collate(self, inp):
        if self.retrieve_data:
            return self.collate_data(inp)
        else:
            return self.collate_idx(inp)

    def collate_idx(self, inp):
        '''
        :param inp: batch * 1
        :return:
        '''
        oup = []
        for minibatch_path_idx in inp:
            with open(os.path.join(self.data_path, minibatch_path_idx[0]), 'r') as f:
                minibatch = f.readlines()[minibatch_path_idx[1]:minibatch_path_idx[1]+self.minibatch_len]
            tmp = []
            for line in minibatch:
                items = line.strip().split()
                tmp.append([round(float(items[i+1]), 6) for i in range(len(items)-1)])
            minibatch = np.array(tmp)
            # print(minibatch.shape)
            for i, name in enumerate(self.attr_names):
                minibatch[:, i] = self.scale(minibatch[:, i], name)
            oup.append(minibatch)
        return np.array(oup)

    def readtxt_data(self, txt_path, shuffle=True):
        data = []
        with tqdm(desc=f'Loading files from {txt_path}', total=sum(len(files) for _, _, files in os.walk(txt_path))) as pbar:
            for root, dirs, files in os.walk(txt_path):
                for file_name in files:
                    if not file_name.endwith('txt'):
                        continue
                    file_path = os.path.join(root, file_name)
                    with open(file_path, 'r') as f:
                        lines = f.readlines()
                    lines = lines[::self.interval]
                    if len(lines) == self.minibatch_len:
                        if random.random() <= self.data_percentage:
                            data.append(lines)
                    elif len(lines) < self.minibatch_len:
                        continue
                    else:
                        for i in range(len(lines)-self.minibatch_len+1):
                            if random.random() <= self.data_percentage:
                                data.append(lines[i:i+self.minibatch_len])
                    pbar.update(1)
        print(f'{len(data)} items loaded from \'{txt_path}\'')
        if shuffle:
            random.shuffle(data)
        return data
    
    def collate_data(self, inp):
        '''
        :param inp: batch * n_sequence * n_attr
        :return:
        '''
        oup = []
        for minibatch in inp:
            tmp = []
            for line in minibatch:
                items = line.strip().split()
                tmp.append([round(float(items[i+1]), 6) for i in range(len(items)-1)])
            minibatch = np.array(tmp)
            # print(minibatch.shape)
            for i, name in enumerate(self.attr_names):
                minibatch[:, i] = self.scale(minibatch[:, i], name)
            oup.append(minibatch)
        return np.array(oup)

    def scale(self, inp, attr):
        assert type(attr) is str and attr in self.attr_names
        if self.scale_method == 'minmax':
            inp = (inp-self.data_statistics[attr]['min'])/(self.data_statistics[attr]['max']-self.data_statistics[attr]['min'])
        elif self.scale_method == 'zscore':
            inp = (inp-self.data_statistics[attr]['mu'])/self.data_statistics[attr]['sigma']
        return inp

    def unscale(self, inp, attr):
        assert type(attr) is str and attr in self.attr_names
        if self.scale_method == 'minmax':
            inp = inp*(self.data_statistics[attr]['max']-self.data_statistics[attr]['min'])+self.data_statistics[attr]['min']
        elif self.scale_method == 'zscore':
            inp = inp*self.data_statistics[attr]['sigma']+self.data_statistics[attr]['mu']
        return inp

class mini_DataGenerator(tu_data.Dataset):
    def __init__(self, data):
        self.data = data

    def __getitem__(self, item):
        return self.data[item]

    def __len__(self):
        return len(self.data)

if __name__ == '__main__':
    data_path = "./data"
    minibatch_len = 10
    dataGenerator = DataGenerator(data_path, minibatch_len, interval=1, scale_method='zscore', data_statistics_path='./data_statistics.json', retrieve_data=False, data_percentage=0.01,
                 train=True, test=True, dev=True, train_shuffle=True, test_shuffle=False, dev_shuffle=False)
    train_data = tu_data.DataLoader(dataGenerator.train_set, batch_size=4, shuffle=False, collate_fn=dataGenerator.collate)
    for i, batch in enumerate(train_data):
        if i > 5:
            break
        dataGenerator.unscale(batch[0,:,0], dataGenerator.attr_names[0])


