import requests
import gzip
import time
import json
from init.config import conf_dict
import urllib

# conf_dict["THIRD"]["dig_host"] = "https://dig.lianjia.com"  # release测试用
class DigTool(object):
    @staticmethod
    def urlencode(basestr):
        return urllib.parse.quote(basestr)

    @staticmethod
    def dig_single_use_get(uicode, uuid, ssid, ucid, email_prefix, evt="1",
                           event="KeOnesApi", pid="infra_pc_keones", key="http://api.ones.ke.com", **kwargs):
        """
        单个埋点
        :param uicode:  罗盘上申请的埋点页面值 uicode
        :param uuid: 用户唯一标识
        :param ucid: 用户 的 ucid
        :param email_prefix: 用户的 邮箱前缀
        :param event: 识埋点事件的类型，如APP元素点击等。默认是KeOnesApi
        :param pid: 申请的业务线ID，默认是申请的那个，可以不传
        :param key: 当前访问唯一标识，默认是我们的后端域名
        :param evt:
        evt:1,3 页面浏览，统计web、M站、APPH5、小程序的pv、uv
        evt:2 统计用户停留时间
        evt:4 统计行为(废弃)
        evt:5 APP无埋点，APP启动
        evt:15 APP无埋点，APP退出
        evt:6 APP无埋点，页面进入
        evt:16 APP无埋点，页面退出
        evt:7 APP无埋点，页面元素点击
        evt:8 APP无埋点，滑屏
        evt:9 APP无埋点，Push消息到达和点击
        evt>10000 需要申请
        :return:
        """
        ddict = {
            "uicode": uicode,
            "uuid": uuid,
            "ssid": ssid,
            "ucid": ucid,
            "email_prefix": email_prefix,
            "event": event,
            "pid": pid,
            "key": key,
            "evt": evt,
        }
        ddict.update(kwargs)
        print(ddict)
        res = requests.get("%s/c.gif?r=%s&d=%s" % (conf_dict["THIRD"]["dig_host"],
                                                   str(int(time.time())),
                                                   DigTool.urlencode(json.dumps(ddict))), timeout=0.5)
        print(res.content)

    @staticmethod
    def dig_multi_use_post(*dig_list):
        ddict = {
            "list": dig_list
        }
        bodydata = "d=%s" % DigTool.urlencode(json.dumps(ddict))
        print("%s/c.gif?r=%s" % (conf_dict["THIRD"]["dig_host"], str(int(time.time()))))
        res = requests.post("%s/c.gif?r=%s" % (conf_dict["THIRD"]["dig_host"], str(int(time.time()))),
                            headers={"Accept-encoding": "gzip"},
                            data=gzip.compress(bodydata.encode(encoding='utf8')), timeout=0.5)
        print(res.content)


if __name__ == "__main__":
    # paradict = {
    #     "uicode": "rdtest",
    #     "ssid": "BB122A84-4C71-447D-BF17-E4481C0EFBAE",
    #     "ucid": "2000000007141937",
    #     "email_prefix": "wangjiliang001",
    #     "pid": "infra_pc_keones",
    #     "evt": "1,3",
    #     "uuid": "aa229a5a-6124-41ae-8ad9-8351ae9be210"
    # }
    # DigTool.dig_single_use_get(**paradict)
    e1 = {
        "uicode": "rdtest",
        "ssid": "BB122A84-4C71-447D-BF17-E4481C0EFBAE",
        "ucid": "2000000007141937",
        "action":{"email_prefix": "wangjiliang001"},
        "pid": "infra_pc_keones",
        "evt": "1,3",
        "uuid": "aa229a5a-6124-41ae-8ad9-8351ae9be210",
        "event": "p1",
        "key": "http://api.ones.ke.com"
    }
    e2 = {
        "uicode": "rdtest",
        "ssid": "BB122A84-4C71-447D-BF17-E4481C0EFBAE",
        "ucid": "2000000007141937",
        "action":{"email_prefix": "wangjiliang001"},
        "pid": "infra_pc_keones",
        "evt": "1,3",
        "uuid": "aa229a5a-6124-41ae-8ad9-8351ae9be210",
        "event": "p2",
        "key": "http://api.ones.ke.com"
    }
    DigTool.dig_multi_use_post(e1, e2)
