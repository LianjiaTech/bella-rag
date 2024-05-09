# -*- coding:utf-8 -*-
# @Time    : 2019/8/29 下午7:50
# @Author  : quemingfei001
import os
import time
from io import StringIO, BytesIO

import xlwt
from django.db.models.query import QuerySet
from django.http import HttpResponse, HttpResponseRedirect, StreamingHttpResponse

from common.helper.api import ApiReturn
from common.tool.django_func import urldecode, upload_bytes
from init.settings import conf_dict
import json


def excel_response(data, file_name='data', headers=None, encoding='gb18030', row_limit=10000, only_url=False):
    """
    把data序列化成csv格式的文件返回.

    :param data: 需要序列化的数据. 支持 list[dict] 或者 django.db.models.query.QuerySet
        e.g.1：list[dict]
        data = [
            {'id': 1, 'name': '小明', 'age': 20},
            {'id': 2, 'name': '小张', 'age': 21},
            {'id': 3, 'name': '小红', 'age': 14},
        ]

        e.g.2：django.db.models.query.QuerySet

    :param file_name: 导出文件名称.
    :param headers: 导出的表头，默认是dict[0]的keys值.
        e.g.1：
        headers = ['编号', '姓名', '年龄']

        e.g.2：
        headers = ['编号', 'pipeline名称', 'pipeline描述', 'ext1', 'ext1', 'ext1', 'ext1', 'ext1',
        '创建人', '修改人', '创建时间', '修改时间']

    :param encoding: 编码格式，默认是gb2312.
    :param row_limit: 限制导出行数，默认是1000.
    """
    # 校验数据结构
    valid_data = False
    # ValuesQuerySet 被在Django 1.9移除
    # https://github.com/makinacorpus/django-geojson/issues/66
    # https://docs.djangoproject.com/en/1.9/releases/1.9/#miscellaneous
    # if isinstance(data, ValuesQuerySet):
    #     data = list(data)

    if not isinstance(data, list) and not isinstance(data, QuerySet):
        return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据结构错误！", body="").to_json())
    else:
        if isinstance(data, QuerySet):
            data = list(data.values())
        # 判断数据量
        if len(data) == 0:
            return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据为空，请确认！", body="").to_json())
        elif len(data) > row_limit:
            return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据过多，请筛选过滤！", body="").to_json())
        elif hasattr(data, '__getitem__'):
            if isinstance(data[0], dict):
                # 追加headers，如果没有默认用dict[0].keys()
                if headers is None:
                    headers = list(data[0].keys())
                data = [[row.get(col, "") for col in headers] for row in data]
                # else:
                #     data = [list(row.values()) for row in data]
                # data.insert(0, headers)
            if hasattr(data[0], '__getitem__'):
                valid_data = True
            # assert valid_data is True, "导出数据结构错误"

            output = BytesIO()
            # 序列化csv的内容
            book = xlwt.Workbook(encoding=encoding)
            sheet = book.add_sheet('Sheet 1')

            # Sheet header, first row
            row_num = 0

            font_style = xlwt.XFStyle()
            font_style.font.bold = True
            al = xlwt.Alignment()
            al.horz = 0x02  # 设置水平居中
            al.vert = 0x01  # 设置垂直居中
            font_style.alignment = al

            for col_num in range(len(headers)):
                sheet.write(row_num, col_num, headers[col_num], font_style)

            # Sheet body, remaining rows
            font_style = xlwt.XFStyle()

            for row in data:
                row_num += 1
                for col_num in range(len(row)):
                    if isinstance(row[col_num], list):
                        row[col_num] = json.dumps(row[col_num], ensure_ascii=False)
                    sheet.write(row_num, col_num, row[col_num], font_style)

            book.save(output)
            file_ext = 'xls'
            # 构造response
            output.seek(0)
            content = output.getvalue()
            filename = '/keones/uploads/%s/%s.%s' % (int(time.time() * 1000000), urldecode(file_name), file_ext)
            code, fileurl = upload_bytes(content, filename)
            if code == 200:
                if only_url:
                    return "%s/attachment%s" % (conf_dict["SERVER"]["server_host"], filename)
                print("url:%s" % "%s/attachment%s" % (conf_dict["SERVER"]["server_host"], filename))
                return HttpResponseRedirect("%s/attachment%s" % (conf_dict["SERVER"]["server_host"], filename))
            else:
                return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR_FOR_FE, "上传失败！", body="").to_json())


def list_excel_response(data, file_name='data', headers=None, encoding='gb2312', row_limit=1000, only_url=False):
    """
    把data序列化成csv格式的文件返回.

    :param data: 需要序列化的数据. 支持 list[list]
        e.g.1：list[dict]
        data = [
            ['id', 'name', 'age'],
            ['1', 'a', '10'],
            ['2', 'b', '20'],
        ]


    :param file_name: 导出文件名称.
    :param headers: 导出的表头，默认是dict[0]的keys值.
        e.g.1：
        headers = ['编号', '姓名', '年龄']

    :param encoding: 编码格式，默认是gb2312.
    :param row_limit: 限制导出行数，默认是1000.
    """
    if not isinstance(data, list):
        return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据结构错误！", body="").to_json())
    else:
        # 判断数据量
        if len(data) == 0:
            return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据为空，请确认！", body="").to_json())
        elif len(data) > row_limit:
            return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据过多，请筛选过滤！", body="").to_json())
        elif hasattr(data, '__getitem__'):
            output = BytesIO()
            # 序列化csv的内容
            book = xlwt.Workbook(encoding=encoding)
            sheet = book.add_sheet('Sheet 1')

            # Sheet header, first row
            row_num = 0

            font_style = xlwt.XFStyle()
            font_style.font.bold = True
            al = xlwt.Alignment()
            al.horz = 0x02  # 设置水平居中
            al.vert = 0x01  # 设置垂直居中
            font_style.alignment = al

            for col_num in range(len(headers)):
                sheet.write(row_num, col_num, headers[col_num], font_style)

            # Sheet body, remaining rows
            font_style = xlwt.XFStyle()

            for ri, row in enumerate(data):
                for ci, col in enumerate(row):
                    if isinstance(col, list):
                        col = json.dumps(col, ensure_ascii=False)
                    sheet.write(ri, ci, col, font_style)
            book.save(output)
            file_ext = 'xls'
            # 构造response
            output.seek(0)
            content = output.getvalue()
            filename = '/keones/uploads/%s/%s.%s' % (int(time.time() * 1000000), urldecode(file_name), file_ext)
            code, fileurl = upload_bytes(content, filename)
            if code == 200:
                if only_url:
                    return "%s/attachment%s" % (conf_dict["SERVER"]["server_host"], filename)
                return HttpResponseRedirect("%s/attachment%s" % (conf_dict["SERVER"]["server_host"], filename))
            else:
                return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR_FOR_FE, "上传失败！", body="").to_json())


def multi_sheets_excel_response(data, file_name='data', headers=None, encoding='gb2312', row_limit=1000, sheets=None,
                                only_url=False):
    """
    把data序列化成csv格式的文件返回.

    :param data: 需要序列化的数据. 支持 list[list]
        e.g.1：list[dict]
        data = [
            ['id', 'name', 'age'],
            ['1', 'a', '10'],
            ['2', 'b', '20'],
        ]


    :param file_name: 导出文件名称.
    :param headers: 导出的表头，默认是dict[0]的keys值.
        e.g.1：
        headers = ['编号', '姓名', '年龄']

    :param encoding: 编码格式，默认是gb2312.
    :param row_limit: 限制导出行数，默认是1000.
    """
    import xlsxwriter
    if not isinstance(data, dict):
        return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据结构错误！", body="").to_json())
    else:
        # 判断数据量
        if len(data) == 0:
            return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据为空，请确认！", body="").to_json())
        elif len(data) > row_limit:
            return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据过多，请筛选过滤！", body="").to_json())
        elif hasattr(data, '__getitem__'):
            output = BytesIO()
            # 序列化csv的内容
            book = xlsxwriter.Workbook(output)
            if not sheets:
                sheet = book.add_worksheet('Sheet 1')
                # Sheet header, first row
                row_num = 0
                font_style = xlwt.XFStyle()
                font_style.font.bold = True
                al = xlwt.Alignment()
                al.horz = 0x02  # 设置水平居中
                al.vert = 0x01  # 设置垂直居中
                font_style.alignment = al

                for col_num in range(len(headers)):
                    sheet.write(row_num, col_num, headers[col_num])

                # Sheet body, remaining rows
                font_style = xlwt.XFStyle()
                for ri, row in enumerate(data):
                    for ci, col in enumerate(row):
                        if isinstance(col, list):
                            col = json.dumps(col, ensure_ascii=False)
                        sheet.write(ri, ci, col, font_style)
            else:
                for sheet_name in sheets:
                    if data.get(sheet_name):
                        sheet = book.add_worksheet(sheet_name)
                        # Sheet header, first row
                        row_num = 0
                        font_style = xlwt.XFStyle()
                        font_style.font.bold = True
                        al = xlwt.Alignment()
                        al.horz = 0x02  # 设置水平居中
                        al.vert = 0x01  # 设置垂直居中
                        font_style.alignment = al
                        for col_num in range(len(headers)):
                            sheet.write(row_num, col_num, headers[col_num])
                        # Sheet body, remaining rows
                        font_style = xlwt.XFStyle()
                        for ri, row in enumerate(data[sheet_name]):
                            for ci, col in enumerate(row):
                                if isinstance(col, list):
                                    col = json.dumps(col, ensure_ascii=False)
                                sheet.write(ri, ci, col)
            # book.save(output)
            book.close()
            file_ext = 'xlsx'
            # 构造response
            output.seek(0)
            content = output.getvalue()
            filename = '/keones/uploads/%s/%s.%s' % (int(time.time() * 1000000), urldecode(file_name), file_ext)
            code, fileurl = upload_bytes(content, filename)
            if code == 200:
                if only_url:
                    return "%s/attachment%s" % (conf_dict["SERVER"]["server_host"], filename)
                return HttpResponseRedirect("%s/attachment%s" % (conf_dict["SERVER"]["server_host"], filename))
            else:
                return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR_FOR_FE, "上传失败！", body="").to_json())


def save_excel_file(data, file_name='data', headers=None, encoding='gb2312', row_limit=1000):
    """
    把data序列化成csv格式的文件保存.

    :param data: 需要序列化的数据. 支持 list[dict] 或者 django.db.models.query.QuerySet
        e.g.1：list[dict]
        data = [
            {'id': 1, 'name': '小明', 'age': 20},
            {'id': 2, 'name': '小张', 'age': 21},
            {'id': 3, 'name': '小红', 'age': 14},
        ]

        e.g.2：django.db.models.query.QuerySet

    :param file_name: 导出文件名称.
    :param headers: 导出的表头，默认是dict[0]的keys值.
        e.g.1：
        headers = ['编号', '姓名', '年龄']

        e.g.2：
        headers = ['编号', 'pipeline名称', 'pipeline描述', 'ext1', 'ext1', 'ext1', 'ext1', 'ext1',
        '创建人', '修改人', '创建时间', '修改时间']

    :param encoding: 编码格式，默认是gb2312.
    :param row_limit: 限制导出行数，默认是1000.
    """
    # 校验数据结构
    valid_data = False
    # ValuesQuerySet 被在Django 1.9移除
    # https://github.com/makinacorpus/django-geojson/issues/66
    # https://docs.djangoproject.com/en/1.9/releases/1.9/#miscellaneous
    # if isinstance(data, ValuesQuerySet):
    #     data = list(data)

    if not isinstance(data, list) and not isinstance(data, QuerySet):
        return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据结构错误！", body="").to_json())
    else:
        if isinstance(data, QuerySet):
            data = list(data.values())
        # 判断数据量
        if len(data) == 0:
            return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据为空，请确认！", body="").to_json())
        elif len(data) > row_limit:
            return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据过多，请筛选过滤！", body="").to_json())
        elif hasattr(data, '__getitem__'):
            if isinstance(data[0], dict):
                # 追加headers，如果没有默认用dict[0].keys()
                if headers is None:
                    headers = list(data[0].keys())
                    data = [[row[col] for col in headers] for row in data]
                else:
                    data = [list(row.values()) for row in data]
                # data.insert(0, headers)
            if hasattr(data[0], '__getitem__'):
                valid_data = True
            # assert valid_data is True, "导出数据结构错误"

            # 序列化csv的内容
            book = xlwt.Workbook(encoding=encoding)
            sheet = book.add_sheet('Sheet 1')

            # Sheet header, first row
            row_num = 0

            font_style = xlwt.XFStyle()
            font_style.font.bold = True

            for col_num in range(len(headers)):
                sheet.write(row_num, col_num, headers[col_num], font_style)

            # Sheet body, remaining rows
            font_style = xlwt.XFStyle()

            for row in data:
                row_num += 1
                for col_num in range(len(row)):
                    sheet.write(row_num, col_num, row[col_num], font_style)

            # MATRIX_PRIVDATA_DIR
            env_dist = os.environ
            file_path = env_dist['MATRIX_PRIVDATA_DIR']
            if not os.path.exists(file_path):
                os.mkdir(file_path)
            excel_file = file_path + os.sep + str(int(time.time())) + '.xls'
            book.save(excel_file)
            return excel_file


def save_onlinebug_report(sheet1_data, sheet2_data, sheet3_data,
                          statistics_zone_name='', file_name='data', headers=None, encoding='gb2312', row_limit=1000):
    """
    把data序列化成csv格式的文件保存.

    :param encoding: 编码格式，默认是gb2312.
    :param row_limit: 限制导出行数，默认是1000.
    """
    # 校验数据结构
    valid_data = False

    if not isinstance(sheet1_data, list) and not isinstance(sheet1_data, QuerySet) \
            and not isinstance(sheet2_data, list) and not isinstance(sheet2_data, QuerySet) \
            and not isinstance(sheet3_data, list) and not isinstance(sheet3_data, QuerySet):
        return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据结构错误！", body="").to_json())
    else:
        if isinstance(sheet1_data, QuerySet):
            sheet1_data = list(sheet1_data.values())
        if isinstance(sheet2_data, QuerySet):
            sheet2_data = list(sheet2_data.values())
        if isinstance(sheet3_data, QuerySet):
            sheet3_data = list(sheet3_data.values())
        if hasattr(sheet1_data, '__getitem__'):
            if isinstance(sheet1_data[0], dict):
                sheet1_data = [list(row.values()) for row in sheet1_data]
        if hasattr(sheet2_data, '__getitem__'):
            if len(sheet2_data) == 0:
                headers = []
                sheet2_data = []
            elif isinstance(sheet2_data[0], dict):
                headers = list(sheet2_data[0].keys())
                sheet2_data = [[row[col] for col in headers] for row in sheet2_data]
        if hasattr(sheet3_data, '__getitem__'):
            if len(sheet3_data) == 0:
                headers3 = []
                sheet3_data = []
            elif isinstance(sheet3_data[0], dict):
                headers3 = list(sheet3_data[0].keys())
                sheet3_data = [[row[col] for col in headers3] for row in sheet3_data]

    # 序列化csv的内容
    book = xlwt.Workbook(encoding=encoding)
    sheet1 = book.add_sheet('线上质量简述')
    sheet1.col(0).width = 256 * 15  # Set the column width
    sheet1.col(1).width = 256 * 15  # Set the column width
    sheet1.col(2).width = 256 * 100  # Set the column width

    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    # 居中
    alignment = xlwt.Alignment()
    alignment.horz = xlwt.Alignment.HORZ_CENTER
    alignment.vert = xlwt.Alignment.VERT_CENTER
    font_style.alignment = alignment
    # 背景颜色
    pattern = xlwt.Pattern()  # Create the Pattern
    pattern.pattern = xlwt.Pattern.SOLID_PATTERN  # May be: NO_PATTERN, SOLID_PATTERN, or 0x00 through 0x12
    pattern.pattern_fore_colour = 48  # May be: 8 through 63. 0 = Black, 1 = White, 2 = Red, 3 = Green, 4 = Blue, 5 = Yellow, 6 = Magenta, 7 = Cyan, 16 = Maroon, 17 = Dark Green, 18 = Dark Blue, 19 = Dark Yellow , almost brown), 20 = Dark Magenta, 21 = Teal, 22 = Light Gray, 23 = Dark Gray, the list goes on...
    font_style.pattern = pattern  # Add Pattern to Style
    # Sheet header, first row
    row_num = 0
    sheet1.write_merge(0, 0, 0, 2, statistics_zone_name + '质量周报 数据简述', font_style)

    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    font_style.alignment.wrap = 1
    for row in sheet1_data:
        row_num += 1
        for col_num in range(len(row)):
            sheet1.write(row_num, col_num, row[col_num], font_style)

    sheet2 = book.add_sheet('线上质量')
    sheet3 = book.add_sheet('补录详情')
    font_style2 = xlwt.XFStyle()
    font_style2.font.bold = True
    # 背景颜色
    pattern = xlwt.Pattern()  # Create the Pattern
    pattern.pattern = xlwt.Pattern.SOLID_PATTERN  # May be: NO_PATTERN, SOLID_PATTERN, or 0x00 through 0x12
    pattern.pattern_fore_colour = 48  # May be: 8 through 63. 0 = Black, 1 = White, 2 = Red, 3 = Green, 4 = Blue, 5 = Yellow, 6 = Magenta, 7 = Cyan, 16 = Maroon, 17 = Dark Green, 18 = Dark Blue, 19 = Dark Yellow , almost brown), 20 = Dark Magenta, 21 = Teal, 22 = Light Gray, 23 = Dark Gray, the list goes on...
    font_style2.pattern = pattern  # Add Pattern to Style
    row_num = 0
    back_now_num = 0
    for col_num in range(len(headers)):
        sheet2.write(row_num, col_num, headers[col_num], font_style2)
    for col_num in range(len(headers3)):
        sheet3.write(back_now_num, col_num, headers[col_num], font_style2)

    font_style2 = xlwt.XFStyle()
    for row in sheet2_data:
        row_num += 1
        for col_num in range(len(row)):
            sheet2.write(row_num, col_num, row[col_num], font_style2)

    for row in sheet3_data:
        back_now_num += 1
        for col_num in range(len(row)):
            sheet3.write(back_now_num, col_num, row[col_num], font_style2)

    output = BytesIO()
    book.save(output)
    file_ext = 'xls'
    # 构造response
    output.seek(0)
    content = output.getvalue()
    file_name = '线上质量-' + statistics_zone_name.replace(" 12:00:00", "")
    filename = '/keones/uploads/%s/%s.%s' % (int(time.time() * 1000000), urldecode(file_name), file_ext)
    code, fileurl = upload_bytes(content, filename)
    return "%s/attachment%s" % (conf_dict["SERVER"]["server_host"], filename)


def save_statistics(sheet_data_list,
                    statistics_zone_name='', file_name='data', headers=None, encoding='gb2312', row_limit=10000):
    """
    sheet_list=[{
        "sheet_data":[{k,v}],
        "sheet_name":"sheet页名字",
        "desc":["说明文字"],
    }]
    把data序列化成csv格式的文件保存.

    :param encoding: 编码格式，默认是gb2312.
    :param row_limit: 限制导出行数，默认是10000.
    """
    if len(sheet_data_list) == 0:
        return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据为空!", body="").to_json())
    # 序列化csv的内容
    book = xlwt.Workbook(encoding=encoding)

    # 描述的字段
    # Sheet body, remaining rows
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    # 居中
    alignment = xlwt.Alignment()
    # alignment.horz = xlwt.Alignment.HORZ_CENTER
    # alignment.vert = xlwt.Alignment.VERT_CENTER
    font_style.alignment = alignment

    # 标题的样式
    font_style2 = xlwt.XFStyle()
    font_style2.font.bold = True
    # 背景颜色
    pattern2 = xlwt.Pattern()  # Create the Pattern
    pattern2.pattern = xlwt.Pattern.SOLID_PATTERN  # May be: NO_PATTERN, SOLID_PATTERN, or 0x00 through 0x12
    pattern2.pattern_fore_colour = 48  # May be: 8 through 63. 0 = Black, 1 = White, 2 = Red, 3 = Green, 4 = Blue, 5 = Yellow, 6 = Magenta, 7 = Cyan, 16 = Maroon, 17 = Dark Green, 18 = Dark Blue, 19 = Dark Yellow , almost brown), 20 = Dark Magenta, 21 = Teal, 22 = Light Gray, 23 = Dark Gray, the list goes on...
    font_style2.pattern = pattern2  # Add Pattern to Style
    # 列表的样式
    font_style3 = xlwt.XFStyle()
    for i in range(len(sheet_data_list)):
        sheet_info = sheet_data_list[i]
        sheet_data = sheet_info["sheet_data"]
        if hasattr(sheet_data, '__getitem__'):
            if len(sheet_data) == 0:
                headers = []
                sheet_data = []
            elif isinstance(sheet_data[0], dict):
                headers = list(sheet_data[0].keys())
                sheet_data = [[row[col] for col in headers] for row in sheet_data]
            else:
                HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, "导出数据结构错误！", body="").to_json())
        sheet = book.add_sheet(sheet_info.get("sheet_name", "sheet%s" % i))
        row_num = 0
        for desc in sheet_info.get("desc", []):
            sheet.write_merge(row_num, row_num, 0, 3, desc, font_style)
            row_num += 1
        for col_num in range(len(headers)):
            sheet.write(row_num, col_num, headers[col_num], font_style2)

        for row in sheet_data:
            row_num += 1
            for col_num in range(len(row)):
                sheet.write(row_num, col_num, row[col_num], font_style3)

    output = BytesIO()
    book.save(output)
    file_ext = 'xls'
    # 构造response
    output.seek(0)
    content = output.getvalue()
    # book.save("test.xls")
    filename = '/keones/uploads/%s/%s.%s' % (int(time.time() * 1000000), urldecode(file_name), file_ext)
    code, fileurl = upload_bytes(content, filename)
    if code == 200:
        return "%s/attachment%s" % (conf_dict["SERVER"]["server_host"], filename)
    else:
        return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR_FOR_FE, "上传失败！", body="").to_json())
