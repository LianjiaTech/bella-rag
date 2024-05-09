import os
import sys
import traceback

from common.tool.config import Config
from common.tool.common_func import *

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
print("BASE_DIR: %s" % BASE_DIR)

# 这里必须填写，用于判断是否是release环境，不同项目要设置不同的值！！！
# 如果启动脚本没有设置响应的值，修改默认值为自己的项目appid即可
# IMPORTANT: 线上appid，导入环境变量，用来自动判断是否是线上环境
# 当前op判定线上环境的准则是 ENVTYPE 没有这个环境变量就是线上环境，
# 容易出现误判，所以使用设置线上appid或者线上域名的方式来确定，
# release_appid的值应该设置为线上目录的最后一级目录的名称
# 例如线上的 MATRIX_CODE_DIR=/data0/www/htdocs/api.ones.ke.com，
# 那么 release_appid="api.ones.ke.com"
default_release_appid = "api.ones.ke.com"
RELEASE_DIR = "/data0/www/htdocs/%s" % os.getenv("release_appid", default_release_appid)
print("线上路径：%s" % RELEASE_DIR)

isRelease = False
if BASE_DIR == RELEASE_DIR:
    isRelease = True
print("线上环境：%s" % isRelease)

conf_dict = {}
if isRelease:
    # 线上环境
    conf_dict = Config().get_conf_dict_by_file("%s/conf/config_release.ini" % BASE_DIR)  # 初始化配置文件
    print("读取配置文件：config_release.ini")
elif os.getenv("CONFIG_FILE"):
    # 指定了CONFIG FILE
    conf_dict = Config().get_conf_dict_by_file("%s/conf/%s" % (BASE_DIR, os.getenv("CONFIG_FILE")))  # 初始化配置文件
    print("读取配置文件：%s" % os.getenv("CONFIG_FILE"))
elif is_linux():
    # 测试环境 linux电脑
    conf_dict = Config().get_conf_dict_by_file("%s/conf/config_test.ini" % BASE_DIR)  # 初始化配置文件
    print("读取配置文件：config_test.ini")
elif is_windows():
    # 测试环境 windows 电脑 配置文件
    conf_dict = Config().get_conf_dict_by_file("%s/conf/config_local.ini" % BASE_DIR)  # 初始化配置文件
    print("读取配置文件：config_local.ini")
else:
    # 测试环境 mac电脑 读取配置文件
    conf_dict = Config().get_conf_dict_by_file("%s/conf/config_local_mac.ini" % BASE_DIR)  # 初始化配置文件
    print("读取配置文件：config_local_mac.ini")

print("配置：conf_dict: \n%s" % conf_dict)
print("################################################################################################")
print("##########################################是否线上：%s#######################################" % isRelease)
print("################################################################################################")
