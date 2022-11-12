import requests
import time
from lxml import etree
import re, os
import datetime, time
import argparse
import logging
import pandas as pd


class Client:
    def __init__(self, opt):
        self.opt = opt
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                     "Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.44"}

    def _get_od_set(self):
        files = pd.read_csv('T_T100D_MARKET_US_CARRIER_ONLY_YEAR.csv', sep=',')
        od_set = (files[files['PASSENGERS'] > self.opt.minPs]['ORIGIN'] + '-' +
                  files[files['PASSENGERS'] > self.opt.minPs]['DEST']).unique().tolist()
        print(f'totally {len(od_set)} routes:')
        print(od_set)
        return od_set

    def fetch_flt(self, f, od_set):
        for od in od_set:
            o, d = od.split('-')[0], od.split('-')[1]
            url = f'https://zh.flightaware.com/live/findflight?origin={o}&destination={d}'
            wrt_str = []
            for i in range(self.opt.retran + 1):
                try:
                    r = requests.get(url=url, headers=self.headers, timeout=self.opt.timeout)
                    r.encoding = 'utf-8'
                    html = r.text
                    tmps = html.split('ffinder-main')[1].split('</div>')[3].split('url=')
                    flts = []
                    for i, tmp in enumerate(tmps[1:]):
                        if i == self.opt.top:
                            break
                        flt = tmp.split("'")[1].split('/live/flight/id/')[1].split('-')[0]
                        flts.append(flt)
                    flts = list(set(flts))
                    for flt in flts:
                        wrt_str.append(f'{o}\t{d}\t{flt}\n')
                    break
                except Exception as e:
                    if i == self.opt.retran:
                        prt_str = "fail to download data from {}".format(url) + '\n' + str(e)
                        return prt_str
                    print(f"fail to fetch data. Will retry({i + 1}) soon...")
                    time.sleep(2)
            print(f'Finished to fetch on Route {od}, totally {len(wrt_str)} flts!')
            f.writelines(wrt_str)

    def run(self):
        with open(self.opt.file, 'w') as f:
            f.write('ORIGIN\tDEST\tFLT\n')
            self.fetch_flt(f, self._get_od_set())
        print('Finished!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', default=f'od_{datetime.datetime.now().strftime("%y%m%d")}.txt', type=str)
    parser.add_argument('--minPs', default=5e4, type=int, help='the least passenger volume')
    parser.add_argument('--top', default=10, type=int, help='fetch top-n flts')
    parser.add_argument('--datadir', default='./data', type=str)
    parser.add_argument('--timeout', default='2', type=int)
    parser.add_argument('--retran', default='5', type=int, help='max time of retry')
    client = Client(parser.parse_args())
    client.run()
