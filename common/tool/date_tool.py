# -*- coding: utf-8 -*-#
# -------------------------------------------------------------------------------
# Name:         date_tool
# Description:  
# Author:       zhuyikun002
# Email:       zhuyikun002@ke.com
# Date:         2019/12/20
# -------------------------------------------------------------------------------

import time, datetime, calendar


def get_between_day(begin_date):
    date_list = []
    begin_date = datetime.datetime.strptime(begin_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(time.strftime('%Y-%m-%d', time.localtime(time.time())), "%Y-%m-%d")
    while begin_date <= end_date:
        date_str = begin_date.strftime("%Y-%m-%d")
        date_list.append(date_str)
        begin_date += datetime.timedelta(days=1)
    return date_list


def get_between_month_by_begin(begin_date):
    date_list = []
    begin_date = datetime.datetime.strptime(begin_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(time.strftime('%Y-%m-%d', time.localtime(time.time())), "%Y-%m-%d")
    while begin_date <= end_date:
        date_str = begin_date.strftime("%Y%m")
        date_list.append(date_str)
        begin_date = add_months(begin_date, 1)
    return date_list


def add_months(dt, months):
    # 返回dt隔months个月后的日期，months相当于步长
    month = dt.month - 1 + months
    year = int(dt.year + month / 12)
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def get_between_month(begin_date, end_date, default_return=list):
    # 返回所有月份，以及每月的起始日期、结束日期，字典格式
    date_list = {}
    begin_date = datetime.datetime.strptime(begin_date, "%Y-%m-%d")
    end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    while begin_date <= end_date:
        date_str = begin_date.strftime("%Y-%m")
        date_list[date_str] = [begin_date.strftime('%Y-%m-01'),
                               begin_date.strftime('%Y-%m-01')[:8] + str(
                                   calendar.monthrange(begin_date.year, begin_date.month)[1])]
        begin_date = add_months(begin_date, 1)
    if default_return == list:
        date_keys = list(date_list.keys())
        date_values = list(date_list.values())
        if len(date_values) > 0:
            date_values[-1][1] = end_date.strftime("%Y-%m-%d")
        return date_keys, date_values
    else:
        return date_list


def get_between_quarter_by_begin(begin_date):
    quarter_list = []
    month_list = get_between_month_by_begin(begin_date)
    for value in month_list:
        tempvalue = value.split("-")
        if tempvalue[1] in ['01', '02', '03']:
            quarter_list.append(tempvalue[0] + "Q1")
        elif tempvalue[1] in ['04', '05', '06']:
            quarter_list.append(tempvalue[0] + "Q2")
        elif tempvalue[1] in ['07', '08', '09']:
            quarter_list.append(tempvalue[0] + "Q3")
        elif tempvalue[1] in ['10', '11', '12']:
            quarter_list.append(tempvalue[0] + "Q4")
    quarter_set = set(quarter_list)
    quarter_list = list(quarter_set)
    quarter_list.sort()
    return quarter_list


def get_between_quarter(begin_date, end_date, default_return=list):
    # 加上每季度的起始日期、结束日期
    quarter_list = {}
    month_list, _ = get_between_month(begin_date, end_date)
    for value in month_list:
        tempvalue = value.split("-")
        year = tempvalue[0]
        if tempvalue[1] in ['01', '02', '03']:
            quarter_list[year + "Q1"] = ['%s-01-01' % year, '%s-03-31' % year]
        elif tempvalue[1] in ['04', '05', '06']:
            quarter_list[year + "Q2"] = ['%s-04-01' % year, '%s-06-30' % year]
        elif tempvalue[1] in ['07', '08', '09']:
            quarter_list[year + "Q3"] = ['%s-07-01' % year, '%s-09-30' % year]
        elif tempvalue[1] in ['10', '11', '12']:
            quarter_list[year + "Q4"] = ['%s-10-01' % year, '%s-12-31' % year]
    if default_return == list:
        quarter_keys = list(quarter_list.keys())
        quarter_values = list(quarter_list.values())
        if len(quarter_values) > 0:
            quarter_values[-1][1] = end_date
        return quarter_keys, quarter_values
    else:
        return quarter_list


def time_format(time_value, time_type='d'):
    if time_type == 'd':
        return round(time_value / (60 * 60 * 24), 2)
    elif time_type == 'w':
        return round(time_value / (60 * 60 * 24 * 7), 2)
    elif time_type == 'm':
        return round(time_value / (60 * 60 * 24 * 7 * 30), 2)
    elif time_type == 'y':
        return round(time_value / (60 * 60 * 24 * 7 * 30 * 365), 2)
    else:
        return time_value


def get_last_week_days(end_time):
    week = 5
    end_time_stptime = datetime.datetime.strptime(end_time, "%Y-%m-%d")
    today_week = end_time_stptime.weekday() + 1
    if today_week >= week:
        return today_week - week
    else:
        return today_week + 7 - week


if __name__ == "__main__":
    print(get_between_month("2019-06-01", datetime.datetime.now().strftime("%Y-%m-%d")))
