import json
import time
import os
import sys

rootpath = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))).replace("\\", "/")
print("rootpath:%s" % rootpath)
syspath = sys.path
sys.path = []
sys.path.append(rootpath)  # 指定搜索路径绝对目录
sys.path.extend([rootpath + i for i in os.listdir(rootpath) if i[0] != "."])  # 将工程目录下的一级目录添加到python搜索路径中
sys.path.extend(syspath)
from init.init_django import *
from init.settings import redis_handle, redis_keones_logging_elapsed_logs_key
import traceback
from common.tool.common_func import *
from common.tool.script_log import ScriptLog
logger = ScriptLog()
BASE_DIR = "%s/tmplog" % rootpath

if __name__ == "__main__":
    logger.info("开始从redis获取日志...")
    count = 0
    sys.stdout.flush()
    file_handle = None
    try:
        applog_root = os.getenv("MATRIX_APPLOGS_DIR", BASE_DIR)
        log_date = get_current_date()  # 当前日志的日期
        log_name = "django_elapsed.log"
        # 创建文件写句柄
        file = "%s/%s.%s" % (applog_root, log_name, log_date)
        file_handle = open(file, 'a+')
        logger.info(str(count) + "====> 初始创建filehadler %s" % file)
        while True:
            try:
                msg = redis_handle.brpop(redis_keones_logging_elapsed_logs_key)
                if msg is None:
                    continue
                count += 1
                logger.info(str(count) + "====>" + str(get_current_time()))
                logger.info(str(count) + "====>" + str(msg))
                logmsg = msg
                logger.info(str(count) + "====>" + str(type(logmsg)))
                logger.info(str(count) + "====>" + str(logmsg))
                curdate = get_current_date()  # 消费到日志的日期
                if curdate != log_date:
                    # 已经不是当前日期了，需要新建文件写入，并且重置logdate为curdate
                    log_date = curdate
                    if file_handle:
                        file_handle.close()
                        file_handle = None
                    # 重新打开新的文件
                    file = "%s/%s.%s" % (applog_root, log_name, log_date)
                    file_handle = open(file, 'a+')
                    logger.info(str(count) + "====> 重新创建filehadler %s" % file)
                if file_handle is None:
                    file = "%s/%s.%s" % (applog_root, log_name, log_date)
                    file_handle = open(file, 'a+')
                    logger.info(str(count) + "====> 异常后创建filehadler %s" % file)
                if file_handle:
                    file_handle.write(logmsg + "\n")
                    file_handle.flush()
                else:
                    logger.error(str(count) + "====>无法写日志！！！！！")

            except:
                logger.info(str(count) + "====>" + ("发生异常:%s" % traceback.format_exc()))
            finally:
                logger.info(str(count) + "====>" + ("消费了%s个" % count))
                logger.info(str(count) + "====>" + ("####[%s]####本次异步执行结束！############" % count))
                sys.stdout.flush()
    except:
        logger.error(traceback.format_exc())
    finally:
        if file_handle:
            file_handle.close()
    str_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    logger.info(str_time)
    logger.info("结束消费")
