import os
import traceback
from time import sleep
import requests
from lxml.html import fromstring


FORUM_URL = "https://www.ignboards.com/forums/vale-tudo.80331"  # os.environ["FORUM_URL"]
COOKIE = "96560654%2CiJWC5zredtWJPaW6LD-7Dgwfp-PIOte5nC0O0ta6"  # os.environ["COOKIE"]
ISP_BLACKLIST = ["AMAZON-AES", "INSTITUTO CYBER DE ENSINO E PESQUISA", "AMAZON-02"]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
)


def get_newest_from_new_members(cache, new_list):
    return [member for member in new_list if member not in cache]


def get_ip_info(ip):
    res = requests.get("https://glookup.info/api/json/" + ip)
    if res.status_code == 200:
        return res.json()
    raise Exception(f"get_ip_info error: ststus code {res.status_code}")


class Xenforo_Auto_Ban:
    def __init__(self, url: str, cookie: str, test: bool = False):
        """
           Parameters:
               url : xenforo forum URL.
               cookie : *xf_user* moderator cookie.
               test : for xenforo demo tests.
        """
        self.xf_token = ""
        self.test = test
        self.url = url
        self.ses = requests.Session()
        self.ses.headers.update({"user-agent": USER_AGENT})
        self.ses.cookies.update({"xf_user": cookie}) if not test else self.ses.cookies.update({"2213_user": cookie})

        self.get_authorization()

    def request(self, uri=None, data=None, method="get", base_url=True, return_as="html"):
        url = (f'{self.url.split("/forums")[0]}{uri}' if base_url else self.url) if not self.test else (
            f'{self.url.split("/2213/forums")[0]}{uri}' if base_url else self.url)
        res = self.ses.get(url) if method == "get" else self.ses.post(url, data)
        if res.status_code > 303:
            raise Exception(f"request error, code: {res.status_code}")
        return fromstring(res.content) if return_as == "html" else res.json()

    def get_authorization(self):
        try:
            html = self.request(base_url=False)
            self.xf_token = html.find('.//input[@name="_xfToken"]').value
        except AttributeError:
            raise Exception("error: not logged in!")

    def spam_cleaner(self, user="coveiro.2"):
        data = {
            "_xfToken": self.xf_token,
            "action_threads": 1,
            "delete_messages": 1,
            "delete_conversations": 1,
            "ban_user": 1,
            "_xfResponseType": "json",
        }
        return self.request(
            uri=f"/spam-cleaner/{user[9:]}" if not self.test else f"/2213/spam-cleaner/{user[14:]}",
            data=data,
            method="post",
            return_as="json"
        )

    def get_ips(self, user):
        res = self.request(
            uri=f'{user.replace("/", "?", 1)}user-ips&_xfToken={self.xf_token}&_xfResponseType=json' if not self.test
            else f'{user}user-ips?_xfToken={self.xf_token}&_xfResponseType=json',
            return_as="json"
        )
        try:
            html = fromstring(res["html"]["content"])
        except KeyError:
            return []
        table = html.find_class('dataList-row dataList-row--noHover')
        return [cell.xpath('./td[1]/a/text()')[0] for cell in table]

    def get_newest_members(self):
        html = self.request(uri="/members/" if not self.test else "/2213/members/")
        members = html.find_class('listHeap')[0]
        return [member.xpath('./a/@href')[0] for member in members]

    def ban_new_members(self, isps: list, members_cache: list = None) -> list:
        if members_cache is None:
            members_cache = []

        new_members = self.get_newest_members()
        print(new_members)

        for member in get_newest_from_new_members(members_cache, new_members):
            print("realy new members: ", member)
            ips = self.get_ips(member)
            print(f"user: {member}  ips: {ips}")
            sleep(1.5)
            for ip in ips:
                ip_info = get_ip_info(ip)
                if ip_info["isp"] in isps:
                    print("bany", member)
                    res = self.spam_cleaner(member)
                    print(res)
                    sleep(1.5)
                    break
        return new_members


def main():
    xab = Xenforo_Auto_Ban(FORUM_URL, COOKIE)
    # print(xab.get_newest_members())
    # print(xab.get_ips("/members/damocl3s.96596669/"))
    # print(xab.spam_cleaner("/members/elena.96596403/"))
    xab.ban_new_members(ISP_BLACKLIST)


def run():
    while True:
        print("init...")
        try:
            users_cache = []
            xab = Xenforo_Auto_Ban(FORUM_URL, COOKIE, test=False)
            while True:
                print("run...")
                new_members = xab.ban_new_members(ISP_BLACKLIST, users_cache)
                users_cache = new_members
                print("waiting 30 seconds...")
                sleep(30)
        except Exception:
            print(traceback.format_exc())
            print("[!] O erro acima ocorreu, tentando de novo apos 30 segundos aguarde...")
            sleep(30)


run()