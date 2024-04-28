import time
from datetime import datetime
import calendar
from decimal import Decimal


class TimeTool(object):

    @staticmethod
    def get_current_time():
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def get_current_date():
        return datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def get_current_timestamp():
        return time.time()

    @staticmethod
    def timestamp_to_datestr(stamps, frmt='%Y-%m-%d %H:%M:%S'):
        # 时间戳转时间字符串（timestamp to datetimeStr）
        #     return time.strftime(frmt, time.localtime(stamps))
        return datetime.fromtimestamp(stamps).strftime(frmt)

    @staticmethod
    def datestr_to_timestamp(str_, frmt='%Y-%m-%d %H:%M:%S'):
        # 时间字符串转时间戳（datetimeStr to timestamp）
        #     return time.mktime(datetime.strptime(str_, frmt).timetuple())
        return time.mktime(time.strptime(str_, frmt))

    @staticmethod
    def datestr_to_date(str_, frmt='%Y-%m-%d %H:%M:%S'):
        # 时间字符串转时间（datetimeStr to datetime）
        return datetime.strptime(str_, frmt)

    @staticmethod
    def date_to_datestr(date_, frmt='%Y-%m-%d %H:%M:%S'):
        # 时间转时间字符串（datetime to datetimeStr）
        return date_.strftime(frmt)

    @staticmethod
    def timestamp_to_date(stamps):
        # 时间戳转时间（datetime to timestamp）
        return datetime.fromtimestamp(stamps)

    @staticmethod
    def date_to_timestamp(date_):
        # 时间转时间戳（timestamp to datetime）
        return time.mktime(date_.timetuple())

    @staticmethod
    def time_interval(begin_time, end_time):
        # 时间间隔，单位天
        end_time = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        begin_time = datetime.strptime(begin_time, "%Y-%m-%d %H:%M:%S")
        pe = (end_time - begin_time).days
        return pe


if __name__ == "__main__":
    timestamp = TimeTool.datestr_to_timestamp("2020-01-02 12:00:00")
    print(timestamp)
    datestr = TimeTool.timestamp_to_datestr(timestamp)
    print(datestr)