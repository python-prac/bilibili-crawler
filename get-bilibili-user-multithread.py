from threading import Thread
from time import sleep
import argparse
from os import path
import json
import basics
from random import randrange
from queue import Queue
from time import time
import get_info
from regex import regex
from dataclasses import dataclass


@dataclass
class bilibili_following_page:
    uid: int
    page: int
    size: int
    asc: bool

    def __str__(self):
        return f'https://api.bilibili.com/x/relation/followings?' \
            f'vmid={int(self.uid)}&pn={int(self.page)}&ps={int(self.size)}&order={"asc" if self.asc else "desc"}'


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--conf', type=str, help='configure file', default='./config.json')
    args = parser.parse_args()

    assert path.exists(args.conf)
    with open(args.conf, 'r') as f:
        conf = json.load(f)

    Qip = Queue(conf['max_ip'])
    Qtask = Queue(conf['max_task'])
    Qlist = Queue(conf['max_list'])
    Qrecord = Queue(conf['max_record'])
    Qlog = Queue(conf['max_log'])

    class GetIp(object):
        def __init__(self, ip_api: str, ip_format: str, sleeping: float):
            super(GetIp, self).__init__()
            self.api = ip_api
            self.form = regex.compile(ip_format)
            self.sleeping = sleeping
            self.spider = get_info.Project()

        def __call__(self):
            sleep(self.sleeping)
            res = self.spider.url_get(self.api, sleep_time=0)
            l = self.form.findall(res)
            assert len(l) == 2
            return basics.Resource(time() + l[-1] / 1000 - 1, l[0])

    def recorder(filename: str, Q: Queue, stop: basics.Remainder):
        while not stop.stop.data or not Q.empty():
            s = Q.get() + '\n'
            with open(filename, 'a') as f:
                f.write(s)
            Q.task_done()
        stop.left.data -= 1

    class GetList(object):
        def __init__(self, total, unit, Q):
            self.unit = unit
            self.total = total // unit
            self.refresh()
            self.Q = Q

        def refresh(self):
            self.seed = randrange(0, self.unit) + 1
            self.i = 0

        def __call__(self):
            if self.i >= self.total:
                self.refresh()
            page = bilibili_following_page(int(self.i * self.unit + self.seed), 1, 50, False)
            self.i += 1
            return page

    def pager():
        res, page = Qlist.get()
        page: bilibili_following_page = page
        try:
            res = json.loads(res)
            if res['code'] != 0:
                return None
            Qrecord.put(json.dumps({"uid": page.uid, "follows": [[i['mid'], i['mtime']] for i in res['data']['list']]}))
            total = res['data']['total']

            def enough():
                if not page.asc:
                    return page.page * 50 >= total
                return 250 + (page.page - 1) * 50 + page.size >= total

            if enough():
                return None
            if page.asc:
                if page.page >= 5:
                    return None
                page.page += 1
                page.size = max(50, total - 250)
            elif page.page < 5:
                page.page += 1
            else:
                page.asc = True
                page.page = 1
                page.size = max(50, total - 250)
            return page
        except json.decoder.JSONDecodeError:
            Qlog.put('[pager] cannot decode, resending ' + str(page))
            return page
        finally:
            Qlist.task_done()

    class Spider(get_info.Project):
        def __init__(self, sleep_time):
            super(Spider, self).__init__()
            self.sleep = sleep_time

        def __call__(self, ip, page: bilibili_following_page):
            return [self.url_get(str(page), sleep_time=self.sleep, proxy_ip=ip), page]

    tasks = basics.Remainder(stop=basics.Holder(False), left=basics.Holder(2))
    list = Thread(
        target=basics.storable,
        args=(Qtask, GetList(conf['uid_total'], conf['uid_unit'], Qlist), tasks, lambda: 1)
    )
    page = Thread(target=basics.storable, args=(Qtask, pager, tasks, lambda: 1))

    spides = basics.Remainder(stop=basics.Holder(False), left=basics.Holder(conf['n_spider']))
    spiders = [Thread(target=basics.process, args=(Qip, Qtask, Spider(0), Qlist, spides, lambda: 1)) for _ in range(conf['n_spider'])]

    ips = basics.Remainder(stop=basics.Holder(False), left=basics.Holder(1))
    ip = Thread(
        target=basics.unstorable,
        args=(Qip, GetIp(conf['ip_addr'], conf['ip_format'], conf['ip_interval']), ips, lambda: 1)
    )

    records = basics.Remainder(stop=basics.Holder(False), left=basics.Holder(2))
    record = Thread(target=recorder, args=(conf['result_file'], Qrecord, records.stop))
    log = Thread(target=recorder, args=(conf['log_file'], Qlog, records.stop))

    threads = [log, ip, list, page, record] + spiders

    for th in threads:
        th.start()

    sleep(conf['total_time'])

    for stopped in [tasks, spides, ips, records]:
        stopped.stop.data = True
        while stopped.left.data:
            sleep(0.5)

if __name__ == '__main__':
    main()