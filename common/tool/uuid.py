# -*- coding: utf-8 -*-#
# -------------------------------------------------------------------------------
# Name:         uuid
# Description:  
# Author:       zhuyikun002
# Email:       zhuyikun002@ke.com
# Date:         2020/3/5
# -------------------------------------------------------------------------------
import time, socket, struct

CLUSTER_NUM = 3


def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def ip2int(ip):
    return socket.ntohl(struct.unpack("I", socket.inet_aton(str(ip)))[0])


def int2ip(int_ip):
    return socket.inet_ntoa(struct.pack("!I", int_ip))


def get_uuid():
    now = int(time.time() * 1000)
    ip = ip2int(get_ip_address())
    ip_d = ip % CLUSTER_NUM
    s = 1
    return now << 20 | ip_d << 16 | ip_d << 12 | s


if __name__ == "__main__":
    uuid = get_uuid()
    print(len(str(uuid)), uuid, uuid.bit_length())
