import datetime
import json
import math
import random
import re
import time
import traceback

from django.core.serializers.json import DjangoJSONEncoder
from django.db import connection, transaction, connections
from django.db.utils import OperationalError
from django.db.utils import DataError
from common.helper import *

from common.tool.common_func import get_current_time, md5
from init.const import DEFAULT_DB_DATE, DEFAULT_DB_TIME
from init.settings import error_logger, sql_logger
connection_readonly = connections["offline-readonly"]


class BaseOrm(object):
    connection = connection
    connection_readonly = connections["offline-readonly"]
    transaction = transaction

    # 静态公用方法
    @staticmethod
    def escape_string_for_sql(value):
        return str(value).replace('\\', '\\\\').replace('\0', '\\0').replace('\n', '\\n').replace('\r', '\\r') \
            .replace('\032', '\\Z').replace("'", "\\'").replace('"', '\\"')

    @staticmethod
    def escape_string_for_xss(value):
        return value.replace('<', '&lt;').replace('>', '&gt;')

    @staticmethod
    def escape_percent_sign_for_sql(value):
        return str(value).replace('%', '\\%%')

    @staticmethod
    def escape_all_for_sql(value):
        return BaseOrm.escape_string_for_xss(BaseOrm.escape_percent_sign_for_sql(BaseOrm.escape_string_for_sql(value)))

    @staticmethod
    def validate_orderby_injectable(paramstr):
        return re.match(".*insert.*|.*select.*|.*delete.*|.*union.*|.*update.*|.*sleep.*"
                        "|.*\*.*|.*\%.*|.*\;.*|.*\=.*|.*\>.*|.*\<.*|.*\'.*|.*\".*", paramstr)

    @staticmethod
    def escape(value):
        if isinstance(value, int):
            return value
        elif isinstance(value, list):
            return [BaseOrm.escape(v) for v in value]
        elif isinstance(value, dict):
            return {BaseOrm.escape(k): BaseOrm.escape(v) for k, v in value.items()}
        else:
            return BaseOrm.escape_all_for_sql(value)

    @staticmethod
    def log_sql_result(sql_str, attr_list, t_start, tsqlend, t_allend,
                       traceback_str, return_value, log_trace_id=None):
        try:
            if log_trace_id is None:
                log_trace_id = md5(get_current_time() + str(random.randint(0, 1000000000)))
            sql_elapsed_time = tsqlend - t_start
            all_elapsed_time = t_allend - t_start

            max_respones_size = int(1024 * 1024 * 1.5)
            # max_respones_size = 10
            if isinstance(return_value, list):
                output_return_value = []
                if return_value:
                    if len(json.dumps(return_value, cls=DjangoJSONEncoder)) <= max_respones_size:
                        output_return_value = return_value
                    else:
                        output_return_value.append(return_value[0])
            else:
                return_value = str(return_value)
                output_return_value = return_value if len(return_value) <= max_respones_size \
                    else return_value[:max_respones_size]

            sql_res_dict = {
                "type": sql_str.strip().split(" ")[0].upper(),
                "elapsed_range": "",
                "sql_elapsed_time": "%.2f ms" % (sql_elapsed_time * 1000),
                "trace_id": log_trace_id,
                "sql_str": sql_str,
                "attr_list": attr_list,
                "start_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t_start)),
                "sql_end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tsqlend)),
                "final_end_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t_allend)),
                "all_elapsed_time": "%.2f ms" % (all_elapsed_time * 1000),
                "exception": traceback_str,
                "return_value": output_return_value,
                "result": "",
                "sql_elapsed_time_ms": sql_elapsed_time * 1000,
            }
            if traceback_str:
                sql_res_dict["result"] = "EXCEPTION"
                sql_res_dict["elapsed_range"] = "EEEEEE"
            else:
                if all_elapsed_time < 0.1:
                    sql_res_dict["result"] = "PASS"
                    sql_res_dict["elapsed_range"] = "< 100 ms"
                elif all_elapsed_time < 0.3:
                    sql_res_dict["result"] = "PASS"
                    sql_res_dict["elapsed_range"] = "< 300 ms"
                elif all_elapsed_time < 0.6:
                    sql_res_dict["result"] = "WARNING"
                    sql_res_dict["elapsed_range"] = "< 600 ms"
                elif all_elapsed_time < 1:
                    sql_res_dict["result"] = "WARNING"
                    sql_res_dict["elapsed_range"] = "< 1000 ms"
                elif all_elapsed_time < 2:
                    sql_res_dict["result"] = "ERROR"
                    sql_res_dict["elapsed_range"] = "< 2000 ms"
                elif all_elapsed_time < 3:
                    sql_res_dict["result"] = "ERROR"
                    sql_res_dict["elapsed_range"] = "< 3000 ms"
                else:
                    sql_res_dict["result"] = "ERROR"
                    sql_res_dict["elapsed_range"] = ">= 3000 ms"
            sql_res_dict_jsonstr = json.dumps(sql_res_dict, cls=DjangoJSONEncoder)
            sql_logger.info(sql_res_dict_jsonstr)
            # if sql_res_dict["result"] == "ERROR":
            #     error_logger.error("SQL执行时间过长 == %s" % sql_res_dict_jsonstr)
        except:
            error_logger.error("execute_select_sql logging failed: %s" % traceback.format_exc())

    @staticmethod
    def execute_select_sql(sql_str, attr_list=None, return_type='list', check_datetime=False,
                           json_keys=None, json_default='list', keys_func=None,
                           log_trace_id=None, logger_errors=True,
                           json_keys_ignore_errors=False, use_readonly=False):

        t_start, tsqlend = 0, 0
        traceback_str = None
        return_value = None
        try:
            if use_readonly:
                use_connection = connection_readonly
            else:
                use_connection = connection

            if attr_list is None:
                attr_list = []
            try:
                t_start = time.time()
                cursor = use_connection.cursor()
                cursor.execute(sql_str, attr_list)
                tsqlend = time.time()

            except OperationalError as opt_err:
                t_start = time.time()
                cursor = use_connection.cursor()
                cursor.execute(sql_str, attr_list)
                tsqlend = time.time()

            if return_type != "list":
                return_value = cursor
                return cursor

            all_data = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            result = []
            for row_data in all_data:
                obj_dict = {}
                # 把每一行的数据遍历出来放到Dict中
                for col, row in zip(col_names, row_data):
                    # 值为 None
                    if row is None:
                        obj_dict[col] = ''
                        continue
                    # 自定义处理函数
                    if keys_func and col in keys_func:
                        obj_dict[col] = keys_func[col](row)
                        continue
                    # Datetime 类型
                    if type(row) == datetime.datetime:
                        obj_dict[col] = str(row).split(".")[0]
                        if check_datetime and obj_dict[col] == DEFAULT_DB_TIME:
                            obj_dict[col] = ''
                        continue
                    # Date 类型
                    if type(row) == datetime.date:
                        obj_dict[col] = str(row).split(".")[0]
                        if check_datetime and obj_dict[col] == DEFAULT_DB_DATE:
                            obj_dict[col] = ''
                        continue
                    # Time 类型
                    if type(row) == datetime.time:
                        obj_dict[col] = str(row).split(".")[0]
                        continue

                    if isinstance(row, str):
                        if json_keys and col in json_keys:
                            # 如果要进行json处理，自动处理
                            valuedict = None
                            try:
                                if row:
                                    # 如果有值 进行loads
                                    if json_keys_ignore_errors:
                                        try:
                                            valuedict = json.loads(row)
                                        except:
                                            valuedict = row
                                    else:
                                        valuedict = json.loads(row)
                                else:
                                    # 如果没有值，使用默认值
                                    if json_default == "list":
                                        valuedict = []
                                    else:
                                        valuedict = {}
                            except:
                                try:
                                    valuedict = eval(row)
                                except:
                                    pass
                            finally:
                                if json_keys_ignore_errors:
                                    obj_dict[col] = valuedict
                                else:
                                    if valuedict is not None and isinstance(valuedict, (dict, list)):
                                        obj_dict[col] = valuedict
                                    else:
                                        raise ValueError("错误的json key，value是不合法的反序列化数据！")

                        else:
                            obj_dict[col] = row
                    else:
                        obj_dict[col] = row
                result.append(obj_dict)
            return_value = result
            return result
        except Exception as e:
            if logger_errors:
                traceback_str = str(traceback.format_exc())
                error_logger.error("execute_select_sql:【异常_EXCEPTION_错误_ERROR】 | %s | attr_list：(%s) | 异常信息: (%s)"
                                   % (sql_str, attr_list, traceback.format_exc()))
            raise e
        finally:
            BaseOrm.log_sql_result(sql_str, attr_list,
                                   t_start, tsqlend, time.time(), traceback_str,
                                   return_value, log_trace_id=log_trace_id)

    @staticmethod
    def execute_update_sql(sql_str, attr_list=None, autocommit=True, logger_errors=True, log_trace_id=None):
        t_start, tsqlend = 0, 0
        traceback_str = None
        return_value = -1
        try:
            if attr_list is None:
                attr_list = []
            try:
                t_start = time.time()
                cursor = connection.cursor()
                res = cursor.execute(sql_str, attr_list)
                insertid = cursor.lastrowid
            except OperationalError as opt_err:
                t_start = time.time()
                cursor = connection.cursor()
                res = cursor.execute(sql_str, attr_list)
                insertid = cursor.lastrowid
            if autocommit:
                connection.commit()
            tsqlend = time.time()
            if sql_str.strip().lower().startswith("insert "):
                return_value = insertid
                return insertid
            else:
                return_value = res
                return res
        except DataError as data_error:
            error_code_match = re.search("^\((?P<mysql_error_code>\d+),", str(data_error))
            if error_code_match:
                error_code = error_code_match.group('mysql_error_code')
                if int(error_code) == 1406:
                    raise KeonesError('数据库字段超长:%s' % str(data_error))
            if logger_errors:
                traceback_str = str(traceback.format_exc())
                error_logger.error("execute_update_sql:【异常_DATA_ERROR_错误_ERROR】 | %s | attr_list：(%s) | 异常信息 : (%s)"
                                   % (sql_str, attr_list, traceback.format_exc()))
            raise data_error
        except Exception as e:
            if logger_errors:
                traceback_str = str(traceback.format_exc())
                error_logger.error("execute_update_sql:【异常_EXCEPTION_错误_ERROR】 | %s | attr_list：(%s) | 异常信息 : (%s)"
                                   % (sql_str, attr_list, traceback.format_exc()))
            raise e
        finally:
            BaseOrm.log_sql_result(sql_str, attr_list,
                                   t_start, tsqlend, time.time(), traceback_str,
                                   return_value, log_trace_id=log_trace_id)

    @staticmethod
    def commit():
        connection.commit()

    @staticmethod
    def rollback():
        connection.rollback()

    @staticmethod
    def get_select_sql_count(sql_str, attr_list=None):
        if attr_list is None:
            attr_list = []
        try:
            cursor = connection.cursor()
            cursor.execute(sql_str, attr_list)
        except OperationalError as opperr:
            cursor = connection.cursor()
            cursor.execute(sql_str, attr_list)
        return cursor.rowcount

    @staticmethod
    def truncate_table(table_name):
        try:
            cursor = connection.cursor()
            return cursor.execute("TRUNCATE TABLE `%s`" % table_name)
        except OperationalError as opperr:
            cursor = connection.cursor()
            return cursor.execute("TRUNCATE TABLE `%s`" % table_name)

    @staticmethod
    def pagination(sql, page=1, limit=1, attr_list=None, whether_groupby=False, check_datetime=False,
                   json_keys=None, json_default="list", keys_func=None, log_trace_id=None, offset=None,
                   use_readonly=False):
        page, limit = int(page), int(limit)

        if log_trace_id is None:
            log_trace_id = md5(get_current_time() + str(random.randint(0, 1000000000)))
        if attr_list is None:
            attr_list = []

        # 获取总得data列表 获取count
        pattern = re.compile(r'^select\s(.*?)\sfrom\s', re.IGNORECASE)
        count_sql_str = re.sub(pattern, 'SELECT COUNT(*) FROM ', sql.replace("\n", "").strip())
        if whether_groupby:
            cursor = BaseOrm.execute_select_sql(count_sql_str, attr_list,
                                                return_type="cursor", log_trace_id=log_trace_id,
                                                use_readonly=use_readonly)
            all_data = cursor.fetchall()
            count_total_num = 0
            for row in all_data:
                count_total_num += 1
            if count_total_num == 0:
                return {"datalist": [], "page": page, "limit": limit, "pagecount": 0, "totalcount": 0, 'offset': 0}
        else:
            exec_data = BaseOrm.execute_select_sql(count_sql_str.lower(), attr_list,
                                                   log_trace_id=log_trace_id,
                                                   use_readonly=use_readonly)
            if not exec_data:
                return {"datalist": [], "page": page, "limit": limit, "pagecount": 0, "totalcount": 0, 'offset': 0}
            else:
                count_total_num = exec_data[0]['count(*)']

        # 分页处理
        sql += "  LIMIT %s,%s "
        page_count = math.ceil(count_total_num / limit)

        attr_list.append((page * limit - limit) if offset is None else offset)
        attr_list.append(limit)

        # 获取分页查出的data列表
        page_data = BaseOrm.execute_select_sql(sql, attr_list, check_datetime=check_datetime, json_keys=json_keys,
                                               json_default=json_default, keys_func=keys_func, log_trace_id=log_trace_id,
                                               use_readonly=use_readonly)

        return {
            "datalist": page_data,
            "page": page,
            "limit": limit,
            "pagecount": page_count,
            "totalcount": count_total_num,
            'offset': 0 if offset is None else (offset + len(page_data)),
        }

    @staticmethod
    def pagination2(sql, page=1, limit=1, attr_list=None, check_datetime=False,
                    json_keys=None, json_default="list", keys_func=None, log_trace_id=None, offset=None,
                    use_readonly=False):
        if log_trace_id is None:
            log_trace_id = md5(get_current_time() + str(random.randint(0, 1000000000)))
        if attr_list is None:
            attr_list = []

        # 分页处理
        page, limit = int(page), int(limit)
        sql += "  LIMIT %s,%s "

        attr_list.append((page * limit - limit) if offset is None else offset)
        attr_list.append(limit + 1)

        # 获取分页查出的data列表
        page_data = BaseOrm.execute_select_sql(sql, attr_list,
                                               check_datetime=check_datetime,
                                               json_keys=json_keys,
                                               json_default=json_default, keys_func=keys_func,
                                               log_trace_id=log_trace_id,
                                               use_readonly=use_readonly)

        page_data, extra_data = page_data[:limit], page_data[limit:]

        return {
            'datalist': page_data,
            'page': page,
            'limit': limit,
            'left': len(extra_data),
            'offset': 0 if offset is None else (offset + len(page_data)),
        }

    @staticmethod
    def pagination3(queries, page=1, limit=1, offset=None):
        # 分页处理
        page, limit = int(page), int(limit)
        start = (page - 1) * limit if offset is None else offset
        stop = start + limit
        page_data = queries[start:stop]
        total_count = len(queries)
        page_count = math.ceil(total_count / limit)
        return {
            'datalist': page_data,
            'page': page,
            'limit': limit,
            'pagecount': page_count,
            'totalcount': total_count,
            'offset': 0 if offset is None else (offset + len(page_data)),
        }

    @staticmethod
    def pagination4(queries, page=1, limit=1, offset=None):
        # 分页处理
        page, limit = int(page), int(limit)
        start = (page - 1) * limit if offset is None else offset
        stop = start + limit
        page_data, extra_data = queries[start:stop], queries[stop:stop + 1]
        return {
            'datalist': page_data,
            'page': page,
            'limit': limit,
            'left': len(extra_data),
            'offset': 0 if offset is None else (offset + len(page_data)),
        }

    @staticmethod
    def get_condition(condition_dict=None, key=None, table_alias="bug", col_name=None,
                      contype="IN-EQ", value_type="STR", sql_condition="AND", condition_value=None, ignore_zero=True):
        """
        自动生成查询条件
        :param condition_dict: 条件dict
        :param key: 请求中所带的 key 值
        :param table_alias:  表 别名
        :param col_name: 列名
        :param contype: 条件类型，
               枚举值：
               IN-EQ    自动识别，如果list使用IN，如果一个元素使用=
               LIKE-OR  like查询并且OR链接 生成 sql_condition ( xxx LIKE '%%%%Name%%%%' OR xxx LIKE '%%%%ddd%%%%')
               LTE_FORDATE       小于日期
               GTE_FORDATE       大于日期
               LIKE              可以是某一列，传str，
                                 也可以是多列like并且OR连接，主要用户关键字匹配多列，table_alias/col_name要传str
               其他的可以是 > < = >= <= , 其他情况下就是根据contype当做判断符号加入
        :param value_type: 值类型
               NUM 数字类型，不用加引号
               STR 字符串类型，要加引号
        :return:
        """
        value = condition_value or condition_dict.get(key)

        if ignore_zero:
            if not value:
                return ''
        else:
            if not value and value != 0:  # Sprint_id 为 0 时，指过滤需求池
                return ''

        if col_name is None:
            col_name = key
        if value_type == "NUM":
            value_quote = ""
        else:
            value_quote = "'"

        if isinstance(value, str) or isinstance(value, int) or isinstance(value, float):
            # 如果是str，切割
            statuslist = str(value).split(",")
        elif isinstance(value, list):
            # 如果是list 直接复制
            statuslist = value
        else:
            statuslist = []

        if contype.upper() == "IN-EQ":
            if len(statuslist) == 0:
                return ""
            elif len(statuslist) == 1:
                return " %s %s.%s=%s%s%s " % (sql_condition, table_alias, col_name,
                                              value_quote,
                                              BaseOrm.escape_all_for_sql(str(statuslist[0])),
                                              value_quote)
            else:
                incondition = ""
                for tmpstatus in statuslist:
                    if str(tmpstatus).strip() != "":
                        incondition += "%s%s%s," % (value_quote,
                                                    BaseOrm.escape_all_for_sql(str(tmpstatus).strip()),
                                                    value_quote)
                incondition = incondition.strip(",")
                if incondition != "":
                    return " %s %s.%s IN (%s) " % (sql_condition, table_alias, col_name, incondition)
        elif contype.upper() == "NOT-IN-EQ":
            if len(statuslist) == 0:
                return ""
            elif len(statuslist) == 1:
                return " %s %s.%s!=%s%s%s " % (sql_condition, table_alias, col_name,
                                             value_quote,
                                             BaseOrm.escape_all_for_sql(str(statuslist[0])),
                                             value_quote)
            else:
                incondition = ""
                for tmpstatus in statuslist:
                    if str(tmpstatus).strip() != "":
                        incondition += "%s%s%s," % (value_quote,
                                                    BaseOrm.escape_all_for_sql(str(tmpstatus).strip()),
                                                    value_quote)
                incondition = incondition.strip(",")
                if incondition != "":
                    return " %s %s.%s NOT IN (%s) " % (sql_condition, table_alias, col_name, incondition)
        elif contype.upper() == "LIKE-OR":
            if statuslist:
                tmpcondition = " %s (" % sql_condition
                for tmpfollower in statuslist:
                    tmpcondition += " %s.%s LIKE '%%%%%s%%%%' OR" \
                                    % (table_alias,
                                       col_name,
                                       BaseOrm.escape_all_for_sql(str(tmpfollower)))
                tmpcondition = tmpcondition[:-2]
                tmpcondition += ") "
                return tmpcondition
        elif contype.upper() == "LIKE":
            if isinstance(col_name, list):
                tmpcondition = " %s (" % sql_condition
                for tmpcolindex in range(0, len(col_name)):
                    tmpcolname = col_name[tmpcolindex]
                    if isinstance(table_alias, list):
                        tmptablename = table_alias[tmpcolindex]
                    else:
                        tmptablename = str(table_alias)
                    tmpcondition += " %s.%s LIKE '%%%%%s%%%%' OR" \
                                    % (tmptablename,
                                       tmpcolname,
                                       BaseOrm.escape_all_for_sql(str(value)))
                tmpcondition = tmpcondition[:-2]
                tmpcondition += ") "
                return tmpcondition
            elif isinstance(col_name, str):
                return " %s %s.%s LIKE '%%%%%s%%%%' " % (sql_condition, table_alias, col_name,
                                                         BaseOrm.escape_all_for_sql(str(value)))
        elif contype.upper() == "LTE_FORDATE":
            return " %s %s.%s<='%s 23:59:59' " % (sql_condition, table_alias, col_name,
                                                  BaseOrm.escape_all_for_sql(str(value)))
        elif contype.upper() == "GTE_FORDATE":
            return " %s %s.%s>='%s 00:00:00' " % (sql_condition, table_alias, col_name,
                                                  BaseOrm.escape_all_for_sql(str(value)))
        else:
            return " %s %s.%s %s %s%s%s " % (sql_condition, table_alias,
                                             col_name,
                                             contype,
                                             value_quote,
                                             BaseOrm.escape_all_for_sql(str(value)),
                                             value_quote)


if __name__ == "__main__":
    # BaseOrm.execute_select_sql("select * from user_info WHERE id=100", return_type="a")
    # BaseOrm.execute_select_sql("select * from user_info WHERE id=100")
    # BaseOrm.execute_update_sql("insert into demo_people(`name`) VALUES ('tttt')")
    # BaseOrm.execute_update_sql("update demo_people set `name`='wang'")
    # BaseOrm.execute_update_sql("delete from demo_people WHERE `id` = 1")
    #
    # BaseOrm.pagination("select * from user_info ", page=1, limit=10)

    # BaseOrm.execute_update_sql("update demo_people set `namesss`='wang'")
    print(BaseOrm.validate_whether_can_sql_inject(" select * from "))
