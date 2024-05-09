import datetime
import hashlib
import platform
from decimal import Decimal


def is_windows():
    return 'Windows' in platform.system()


def is_linux():
    return 'Linux' in platform.system()


def get_sub_string(params, start, end):
    find_start_tag = start
    find_end_tag = end
    if find_start_tag == "":
        spos = 0
    else:
        spos = params.find(find_start_tag)

    if spos == -1:  # 没有发现关键字 SQL_SELECT()
        return ''

    if find_end_tag == "":
        epos = len(params)
    else:
        epos = params.find(find_end_tag, spos + len(find_start_tag))

    if epos == -1:  # 没有发现关键字 find_end_tag
        return ''

    return params[spos + len(find_start_tag):epos]


def get_current_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_current_date():
    return datetime.datetime.now().strftime('%Y-%m-%d')


def get_n_day_time(n=0, time_format="%Y-%m-%d %H:%M:%S"):
    return (datetime.date.today() + datetime.timedelta(days=n)).strftime(time_format)


def get_n_day(n=0, time_format="%Y-%m-%d"):
    return (datetime.date.today() + datetime.timedelta(days=n)).strftime(time_format)


def change_date_format(datetime_str):
    datetime_str = datetime_str.split(' ')
    return datetime_str[0] + "T" + datetime_str[1] + ".000+0800"

def get_belong_thursday(time_str):
    time_str = time_str[:10]
    if time_str == "1970-01-02":
        return time_str
    time_date = datetime.datetime.strptime(time_str, "%Y-%m-%d")
    time_week = time_date.strftime("%Y-%U-%w")
    if time_week[-1] in ["5", "6"]:
        time_date = time_date + datetime.timedelta(days=7)
        time_week = time_date.strftime("%Y-%U-%w")
    return datetime.datetime.strptime(time_week[:-1] + "4", '%Y-%U-%w').strftime("%Y-%m-%d")

def md5(basestr, case="lower"):
    """
    求字符串的md5值，默认是小写，如果是大写第二个参数传递upper等。
    """
    md = hashlib.md5()  # 创建md5对象
    md.update(basestr.encode(encoding='utf-8'))
    if case == "lower":
        return md.hexdigest().lower()
    else:
        return md.hexdigest().upper()


def process_mongodb_name(base_name):
    return base_name.replace("-", "_").replace(".", "_").lower()

def get_quarter(tmpdate):
    tmpdate = tmpdate.split(" ")[0]
    datesplit_list = tmpdate.split("-")
    if int(datesplit_list[1]) <= 3:
        q = 1
    elif int(datesplit_list[1]) <= 6:
        q = 2
    elif int(datesplit_list[1]) <= 9:
        q = 3
    elif int(datesplit_list[1]) <= 12:
        q = 4
    else:
        raise ValueError("ERROR: %s" % datesplit_list)
    appenddate = "%sQ%s" % (datesplit_list[0], q)
    return appenddate


def get_month(tmpdate):
    datesplit_list = tmpdate.split("-")
    appenddate = "%s-%s" % (datesplit_list[0], datesplit_list[1])
    return appenddate


def time_interval(begin_time, end_time):
    # 时间间隔，单位秒
    end_time = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    begin_time = datetime.datetime.strptime(begin_time, "%Y-%m-%d %H:%M:%S")
    period = Decimal(str((end_time - begin_time).total_seconds())).quantize(Decimal('0.00'))
    return str(period)

if __name__ == "__main__":
    print(get_belong_thursday("2020-04-05"))
