import numpy as np
import os
import argparse
from tqdm import tqdm
import json

def listdirs(data_path):
    attr_names = ['lon', 'lat', 'alt', 'spdx', 'spdy', 'spdz']
    # attr_names = ['lat', 'lon', 'hdg', 'kph', 'alt', 'roc']
    data = {name:[] for name in attr_names}
    with tqdm(desc=f'Loading files from {data_path}', total=sum(len(files) for _, _, files in os.walk(data_path))) as pbar:
        for root, dirs, files in os.walk(data_path):
            for f in files:
                pbar.update(1)
                if not f.endswith('.txt'):
                    continue

                txt_path = os.path.join(root, f)
                with open(txt_path, 'r') as fr:
                    lines = fr.readlines()

                for record in lines:
                    items = record.strip().split()
                    for i, name in enumerate(attr_names):
                        data[name].append(float(items[i+1]))
            # print(f'{len(files)} files has been loaded')
    import matplotlib.pyplot as plt
    for name in attr_names:
        plt.figure()
        plt.hist(data[name], bins=1000)
        plt.title(name)
    plt.show()
    # exit()
    return {name:{'max': max(data[name]), 
                  'min': min(data[name]), 
                  'mu': sum(data[name])/len(data[name]), 
                  'sigma': np.std(np.array(data[name]))} for name in attr_names}


if __name__ == '__main__':
    parsers = argparse.ArgumentParser()
    parsers.add_argument('--datadir', default='.\data', type=str)
    args = parsers.parse_args()
    jsoN = listdirs(args.datadir)
    try:
        with open('data_statistics.json', 'r') as f:
            his = json.load(f)
    except:
        his = {}
    for key, value in jsoN.items():
        his[key] = value
    with open('data_statistics.json', 'w') as f:
        json.dump(his, f)
    print('Finished!')
    print(his)
