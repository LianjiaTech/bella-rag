import telnetlib
import traceback
import time
import json
from telnetlib import DEBUGLEVEL, TELNET_PORT
import socket


class MyTelnet(telnetlib.Telnet):
    def __init__(self, host=None, port=0, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, local_host=None, local_port=0):
        self.debuglevel = DEBUGLEVEL
        self.host = host
        self.port = port
        self.timeout = timeout
        self.local_host = local_host
        self.local_port = local_port
        self.sock = None
        self.rawq = b''
        self.irawq = 0
        self.cookedq = b''
        self.eof = 0
        self.iacseq = b''  # Buffer for IAC sequence.
        self.sb = 0  # flag for SB and SE sequence.
        self.sbdataq = b''
        self.option_callback = None
        if host is not None:
            self.open(host, port, timeout, local_host, local_port)

    def open(self, host, port=0, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, local_host=None, local_port=0):
        self.eof = 0
        if not port:
            port = TELNET_PORT
        self.host = host
        self.port = port
        self.timeout = timeout
        if local_host is not None and local_port != 0:
            self.sock = socket.create_connection((host, port), timeout, source_address=(local_host, local_port))
        else:
            self.sock = socket.create_connection((host, port), timeout)


class TelnetTool(object):
    def __init__(self, host, port, timeout=10, encoding="gbk", finish=b'dubbo>', local_host=None, local_port=0):
        self.host = host
        self.port = int(port)
        self.timeout = int(timeout)
        self.encoding = encoding
        self.finish = finish
        self.local_host = local_host
        self.local_port = local_port
        self.tn = None

    def connect(self):
        try:
            self.tn = MyTelnet(self.host, self.port, timeout=self.timeout,
                               local_host=self.local_host, local_port=self.local_port)
            self.tn.set_debuglevel(0)  # 设置debug输出级别  0位不输出，越高输出越多
            return True
        except:
            # print(traceback.format_exc())
            self.tn = None
            return False

    def close(self):
        if self.tn is not None:
            self.tn.close()

    def send_cmd(self, command, finish=None, timeout=0):
        """执行telnet命令
            :param host:
            :param port:
            :param finish:
            :param command:
            :return:
            """
        # 连接Telnet服务器
        try:
            thistimeout = timeout if timeout else self.timeout
            thisfinish = finish if finish else self.finish
            if self.tn is None and self.connect() is False:
                return "<ERROR: DUBBO未连接成功，检查地址%s:%s！>" % (self.host, self.port)

            self.tn.write(b'%s\r\n' % command.encode(self.encoding))
            # 执行完毕后，终止Telnet连接（或输入exit退出）
            return_msg_bytes = self.tn.read_until(thisfinish, timeout=thistimeout)
            try:
                return_msg = return_msg_bytes.decode(self.encoding)
            except:
                return_msg = str(return_msg_bytes)

            if len(return_msg) == 0:
                return "<ERROR: DUBBO请求%s秒内没有返回，请求超时！>" % thistimeout
            else:
                return return_msg
        except Exception as e:
            return "<ERROR: Telnet请求时发生网络问题或者接口错误，请确认。%s>" % traceback.format_exc()
        finally:
            self.close()

    def do_dubbo_invoke(self, class_name, method_name, params=""):
        invokestr = "invoke %s.%s(%s)" % (class_name, method_name, params)
        starttime = time.time()
        ret_all = self.send_cmd(invokestr)
        endtime = time.time()
        ret_all = ret_all.strip(self.finish.decode(self.encoding))
        ret_list = ret_all.split("elapsed: ")
        if len(ret_list) == 2:
            # 正确情况
            return ret_list[0].strip(), int(ret_list[1].replace(" ms.", "").strip())
        elif len(ret_list) == 1:
            # 没有找到elapsed:
            return ret_list[0], int((endtime - starttime) * 1000)
        else:
            return ret_all, int((endtime - starttime) * 1000)

    def do_dubbo_exinvoke(self, class_name, method_name, params_list=[], attachments_dict={}):
        exinvoke_dict = {
            "service": class_name,
            "method": method_name,
            "args": params_list,
            "attachments": attachments_dict
        }
        invokestr = 'exinvoke ' + json.dumps(exinvoke_dict)
        print(invokestr)
        starttime = time.time()
        ret_all = self.send_cmd(invokestr)
        endtime = time.time()
        ret_all = ret_all.strip(self.finish.decode(self.encoding))
        print("%s:%s" % (attachments_dict, ret_all))
        ret_list = ret_all.split("elapsed: ")
        if len(ret_list) == 2:
            # 正确情况
            return ret_list[0].strip(), int(ret_list[1].replace(" ms.", "").strip())
        elif len(ret_list) == 1:
            # 没有找到elapsed:
            return ret_list[0], int((endtime - starttime) * 1000)
        else:
            return ret_all, int((endtime - starttime) * 1000)
