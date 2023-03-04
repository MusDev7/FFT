import scipy.interpolate as inter
import os
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
#import torch
import math

def traverse_files(path, draw_pic = False, convert=False, skip_lens = 50):
    for root, dirs, files in os.walk(path):
        # print(files)
        for f in files:
            if 'ROUTE' in f or 'interp' in f:
                continue
            with open(os.path.join(root, f), 'r') as fr:
                lines = fr.readlines()
            if len(lines) < skip_lens:
                continue
            data = generate_dataGrid(lines)
            if not data[-1]:
                continue
            timestamp, interp_lats, interp_lons, interp_hdgs, interp_kphs, interp_alts, interp_rocs = interpolate(*data[:-2])
            wlines = np.array([timestamp, interp_lats, interp_lons, interp_hdgs, interp_kphs, interp_alts, interp_rocs]).transpose().tolist()
            store_path1 = os.path.join('./processed/notConverted',os.path.split(root)[-1])
            store_path2 = os.path.join('./processed/converted',os.path.split(root)[-1])
            if not os.path.exists(store_path1):
                os.makedirs(store_path1)
            if not os.path.exists(store_path2):
                os.makedirs(store_path2)
            with open(os.path.join(store_path1, 'interp_'+f), 'w') as fr:
                for line in wlines:
                    time, lat, lon, hdg, kph, alt, roc = line
                    fr.write(f'{(datetime.timedelta(seconds=time)+data[-2]).strftime("%H%M%S")}\t')
                    fr.write(f'{round(lat, 6)}\t')
                    fr.write(f'{round(lon, 6)}\t')
                    fr.write(f'{round(hdg, 6)}\t')
                    fr.write(f'{round(kph, 6)}\t')
                    fr.write(f'{round(alt, 3)}\t')
                    fr.write(f'{round(roc, 3)}\n')
            if convert:
                times, lons, lats, alts, vx, vy, vz = convert_LLAVxyz(timestamp, interp_lats, interp_lons, interp_hdgs,
                                                                      interp_kphs, interp_alts, interp_rocs)
                wlines = np.array([times, lons, lats, alts, vx, vy, vz]).transpose().tolist()
                with open(os.path.join(store_path2, 'interpConvert_' + f), 'w') as fr:
                    for line in wlines:
                        time, lon, lat, alt, vx, vy, vz = line
                        fr.write(f'{(datetime.timedelta(seconds=time) + data[-2]).strftime("%H%M%S")}\t')
                        fr.write(f'{round(lon, 6)}\t')
                        fr.write(f'{round(lat, 6)}\t')
                        fr.write(f'{round(alt, 3)}\t')
                        fr.write(f'{round(vx, 6)}\t')
                        fr.write(f'{round(vy, 6)}\t')
                        fr.write(f'{round(vz, 3)}\n')
            print(os.path.join(root, f)+' finished')
            if draw_pic:
                plt.figure()
                fig = plt.gcf()
                axis = fig.add_subplot(111, projection='3d')
                axis.plot3D(data[1], data[2], data[-4], marker='o', markeredgecolor='orangered', label='trg')
                axis.plot3D(interp_lats, interp_lons, interp_alts, marker='+', markeredgecolor='dodgerblue', label='interp')
                axis.legend()
                axis.set_xlabel('lat')
                axis.set_ylabel('lon')
                axis.set_zlabel('alt')
                plt.title(str(os.path.join(root, f))+f'({len(data[1])} pnts)')
    if draw_pic:
        plt.show()

def convert_LLAVxyz(times, lats, lons, hdgs, kphs, alts, rocs):
    vx = (np.cos(hdgs) * kphs).tolist() # eastward towards
    vy = (np.sin(hdgs) * kphs).tolist() # westward towards
    vz = (np.array(rocs) / 3.2808399 / 60).tolist() # m/s
    return times, lons, lats, alts, vx, vy, vz

def generate_dataGrid(lines):
    lines = lines[2:] # remove 1,2 rows
    times, lats, lons, hdgs, kphs, alts, rocs = [] , [], [], [], [], [], []
    time0 = datetime.datetime.strptime(lines[0][:6], '%H%M%S')
    for line in lines:
        items = line.strip().split('\t')
        time, lat, lon, hdg, kph, alt, roc = items[0], items[1], items[2], items[3], items[5], items[6], items[7]
        times.append((datetime.datetime.strptime(time, '%H%M%S')-time0).seconds)
        lats.append(float(lat)) # degree
        lons.append(float(lon)) # degree
        hdgs.append(float(hdg)) # degree
        kphs.append(float(kph.strip("[]'")) if len(kph.strip("[]'"))!=0 else -1) # kph
        alts.append(float(alt.strip("[]'")) if len(alt.strip("[]'"))!=0 else -1) # m
        rocs.append(float(roc)) # ft/min
    unique_timeBool = np.diff([-1]+times) != 0 # redundancy removed
    if (np.array(kphs)[unique_timeBool]==-1).sum() / len(np.array(kphs)[unique_timeBool]) > 0.5 or \
       (np.array(alts)[unique_timeBool]==-1).sum() / len(np.array(alts)[unique_timeBool]) > 0.5 or \
       (np.array(rocs)[unique_timeBool]).sum() == 0:
        validation = False
    else:
        validation = True
    return np.array(times)[unique_timeBool], np.array(lats)[unique_timeBool], np.array(lons)[unique_timeBool], \
           np.array(hdgs)[unique_timeBool], np.array(kphs)[unique_timeBool], np.array(alts)[unique_timeBool], \
           np.array(rocs)[unique_timeBool], time0, validation

def interpolate(times, lats, lons, hdgs, kphs, alts, rocs, interval=20, kind='linear'):
    timestamp = list(range(max(min(np.array(times)[np.array(kphs)!=-1].tolist()),
                               min(np.array(times)[np.array(alts)!=-1].tolist())),
                           min(max(np.array(times)[np.array(kphs)!=-1].tolist()),
                               max(np.array(times)[np.array(alts)!=-1].tolist()))+1, interval))
    # cs_lats = inter.interp1d(times, lats, kind=kind, fill_value="extrapolate")
    # cs_lons = inter.interp1d(times, lons, kind=kind, fill_value="extrapolate")
    # cs_hdgs = inter.interp1d(times, hdgs, kind=kind, fill_value="extrapolate")
    # cs_kphs = inter.interp1d(np.array(times)[np.array(kphs)!=-1], np.array(kphs)[np.array(kphs)!=-1], kind=kind, fill_value="extrapolate")
    # cs_alts = inter.interp1d(np.array(times)[np.array(alts)!=-1], np.array(alts)[np.array(alts)!=-1], kind=kind, fill_value="extrapolate")
    # cs_rocs = inter.interp1d(times, rocs, kind=kind, fill_value="extrapolate")
    cs_lats = inter.interp1d(times, lats, kind=kind, fill_value="extrapolate")
    cs_lons = inter.interp1d(times, lons, kind=kind, fill_value="extrapolate")
    cs_hdgs = inter.interp1d(times, hdgs, kind=kind, fill_value="extrapolate")
    cs_kphs = inter.interp1d(np.array(times)[np.array(kphs)!=-1], np.array(kphs)[np.array(kphs)!=-1], kind=kind, fill_value="extrapolate")
    cs_alts = inter.interp1d(np.array(times)[np.array(alts)!=-1], np.array(alts)[np.array(alts)!=-1], kind=kind, fill_value="extrapolate")
    cs_rocs = inter.interp1d(times, rocs, kind=kind, fill_value="extrapolate")
    interp_lats = cs_lats(timestamp).tolist()
    interp_lons = cs_lons(timestamp).tolist()
    interp_hdgs = cs_hdgs(timestamp).tolist()
    interp_kphs = cs_kphs(timestamp).tolist()
    interp_alts = cs_alts(timestamp).tolist()
    interp_rocs = cs_rocs(timestamp).tolist()
    return timestamp, interp_lats, interp_lons, interp_hdgs, interp_kphs, interp_alts, interp_rocs

if __name__ == '__main__':
    try:
        import matplotlib
        matplotlib.use('Qt5Agg')
    except:
        pass
    traverse_files('./data/AAL28', True, False)
