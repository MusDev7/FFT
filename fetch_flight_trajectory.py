import requests
import time
from lxml import etree
import re, os
import datetime, time
import argparse
import logging


def progress_bar(step, n_step, str, start_time=time.perf_counter(), bar_len=20):
    '''
    :param bar_len: length of the bar
    :param step: from 0 to n_step-1
    :param n_step: number of steps
    :param str: info to be printed
    :param start_time: time to begin the progress_bar
    :return:
    '''
    step = step+1
    a = "*" * int(step * bar_len / n_step)
    b = " " * (bar_len - int(step * bar_len / n_step))
    c = step / n_step * 100
    dur = time.perf_counter() - start_time
    print("\r{:^3.0f}%[{}{}]{:.2f}s {}".format(c, a, b, dur, str), end="")
    if step == n_step:
        print('')


class Client:
    def __init__(self, opt):
        self.opt = opt
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                     "Chrome/95.0.4638.69 Safari/537.36 Edg/95.0.1020.44"}
        self.log_path = self.opt.logdir + f'/{datetime.datetime.now().strftime("%y-%m-%d")}'
        if not os.path.exists(self.log_path):
            os.makedirs(self.log_path)
        logging.basicConfig(filename=os.path.join(self.log_path, 'run.log'),
                            filemode='w', format='%(asctime)s   =>   %(message)s', level=logging.DEBUG)

    def fetch_fltNo(self):
        fltNos = []
        with open(self.opt.fltdir, 'r') as f:
            f.readline()
            lines = f.readlines()
            for line in lines:
                fltNos.append(line.strip().split('\t')[-1])
        return fltNos

    def fetch_query_url(self, flt):
        url = 'https://zh.flightaware.com/live/flight/{}/history'.format(flt)
        querys = []
        try:
            r = requests.get(url=url, headers=self.headers)
            r.encoding = 'utf-8'
            ret_text = r.text
            links = ret_text.split('data-target')[1:]
            for t in links:
                if ("已排班" in t) or ("已取消" in t) or ("在途中" in t):
                    continue
                link = t.split("'")[1]
                date = link.split('/')[5]
                tag = link.split('/')[6]
                intact_url = 'https://zh.flightaware.com/' + link + "/tracklog"
                querys.append([intact_url, flt, date, tag])
        except Exception as e:
            pass
        return querys

    def data_parse(self, line):
        # tree = etree.HTML(line)
        line = line.split("thirdHeader")[1].split("smallrow2")
        results = []
        for l in line:
            results.extend(l.split("smallrow1"))
        results = [r.split("small-4 columns no-padding-ad")[0] for r in results][2:]
        ret_traj = []
        for r in results:
            if 'flight_event' in r:
                continue
            segs = r.split("td align=")[1:]
            # print(segs)
            datetime = re.sub("\D", "", segs[0].split("</span>")[0])
            lat = re.findall(r"\d+\.?\d*", segs[1].split("</span>")[0])[0]
            lon = re.findall(r"\d+\.?\d*", segs[2].split("</span>")[0])[0]
            hdg = re.findall(r"\d+\.?\d*", segs[3])[0]
            spd_knot = re.findall(r"\d+\.?\d*", segs[5])  # [0]
            spd_kmph = re.findall(r"\d+\.?\d*", segs[6])  # [0]
            alt_m = re.findall(r"\d+\.?\d*", segs[7].split("</span>")[1])  # [0]
            # 8 ROCD
            temp = segs[8].split('&nbsp;')[0].split(">")[-1]
            rocd = re.findall(r"\d+\.?\d*", temp)
            if len(rocd) == 0:
                rocd = 0
            else:
                if '-' in temp:
                    rocd = -1 * float(rocd[0])
                else:
                    rocd = float(rocd[0])
            ret = [datetime, lat, lon, hdg, spd_knot, spd_kmph, alt_m, rocd]
            sl = [str(s) for s in ret]
            ret_traj.append(sl)
        return ret_traj

    def get_data_from_url(self, params):
        url, fltNo, cur_date, tag = params
        for i in range(self.opt.retran+1):
            try:
                r = requests.get(url=url, headers=self.headers, timeout=self.opt.timeout)
                break
            except Exception as e:
                if i == self.opt.retran:
                    prt_str = "fail to download data from {}".format(url) + '\n' + str(e)
                    logging.debug(prt_str)
                    return prt_str
                print(f"Fail to fetch data. Will retry({i+1}) soon...")
                time.sleep(10)
        prt_str = "Get successfully"
        logging.debug(prt_str)
        print(prt_str)
        r.encoding = 'utf-8'
        # print(url)
        if 'Flight date too far in the future' in r.text:
            prt_str = "fail to download data from {}".format(url)
            logging.debug(prt_str)
            return prt_str
        try:
            ret_traj = self.data_parse(r.text)
            datapath = self.opt.datadir + "/{}/".format(fltNo)
            if not os.path.exists(datapath):
                os.makedirs(datapath)
            with open(os.path.join(datapath, "{}-{}.txt".format(cur_date, tag)), 'w', encoding='utf-8') as fw:
                fw.write("# {}\n".format(url))
                fw.write("cst\tlat\tlon\thdg\tknot\tkph\talt\troc\n")
                for traj in ret_traj:
                    fw.write('\t'.join(traj) + "\n")
            prt_str = "sucessfully download data from {}".format(url)
            logging.debug(prt_str)
            return prt_str
        except Exception as e:
            prt_str = "fail to download data from {}".format(url) + '\n' + str(e)
            logging.debug(prt_str)
            return prt_str

    def run(self, start_from=None):
        flts = self.fetch_fltNo()
        if start_from is not None:
            idx = 0
            try:
                idx = flts.index(start_from)
            except Exception as e:
                pass
            flts = flts[idx:]
        for flt in flts:
            start_time = time.perf_counter()
            querys = self.fetch_query_url(flt)
            for i, query in enumerate(querys):
                prt_str = self.get_data_from_url(query)
                progress_bar(i, len(querys), prt_str, start_time)
            prt_str = f'Flight {flt}: Done in {datetime.datetime.now()}!'
            print(prt_str, '\n')
            logging.debug(prt_str)
        print('Finished!')
        logging.debug('Finished!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fltdir', default='./od_in.txt', type=str)
    parser.add_argument('--datadir', default='./data', type=str)
    parser.add_argument('--logdir', default='./log', type=str)
    parser.add_argument('--timeout', default='10', type=int)
    parser.add_argument('--retran', default='5', type=int, help='max time of retry')
    client = Client(parser.parse_args())
    client.run()
    # client.get_data_from_url(["https://flightaware.com/live/flight/UAL517/history/20221110/0540Z/KSAN/KEWR/tracklog", "UAL517", "20202020", "13Z"])