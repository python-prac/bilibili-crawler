import requests
import time
from requests.adapters import HTTPAdapter


headers = {
    'Host': 'api.bilibili.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:47.0) Gecko/20100101 Firefox/47.0',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}


class Project(object):
    def __init__(self, max_retries=3):
        """
        :param max_retries:自动重连最大次数
        """
        self.S = requests.Session()
        self.S.mount('https://', HTTPAdapter(max_retries=max_retries))

    def url_get(self, url, sleep_time=0.5, proxy_ip=None):
        """
        爬虫
        :param url:输入的url
        :param sleep_time:每次抓取的暂停时间
        :param proxy_ip: 代理服务器IP
        :return: 成功则返回utf-8格式的字符串，失败返回None
        """
        try:
            if proxy_ip:
                proxies = {"http":"http://" + proxy_ip, "https":"https://" + proxy_ip}
                response = self.S.get(url, headers=headers, proxies=proxies)
            else:
                response = self.S.get(url, headers=headers)
            time.sleep(sleep_time)
            return response.content.decode('utf-8')
        except:
            return None



proj = Project()
for ID in range(2, 400000000+2+1, 40000):
    url = 'https://api.bilibili.com/x/relation/followings?vmid=%d&pn=1&ps=50&order=desc' % ID
    print(proj.url_get(url, sleep_time=1))







