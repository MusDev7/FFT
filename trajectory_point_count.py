import scipy.interpolate as inter
import os
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import torch


def traverse_files(path):
    counts = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if 'ROUTE' in f or 'interp' in f:
                continue
            with open(os.path.join(root, f), 'r') as fr:
                lines = fr.readlines()
            counts.append(len(lines)-2)
    return counts

if __name__ == '__main__':
    counts = traverse_files('E:\Coooodes\FFT\data')
    print(max(counts),min(counts),np.mean(counts),np.median(counts),np.percentile(counts, 3, method='midpoint'))
    plt.hist(counts, bins=len(counts))
    plt.show()

