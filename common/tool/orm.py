import datetime
import json

from django.db import connection

from common.tool.orm_base import BaseOrm


class DORM(BaseOrm):

    # 构造函数 初始化方法
    def __init__(self, table_name, autocommit=True, logger_errors=True, **kwargs):
        # table_name 表名
        # id 表示主键
        self.table_name = table_name
        self.autocommit = autocommit
        self.logger_errors = logger_errors
        self.reset_sql_info()
        self.set_attrs(**kwargs)

    def set(self, name, value):
        setattr(self, name, value)

    def get(self, name):
        return getattr(self, name)

    def set_attrs(self, **kwargs):
        for tmpk, tmpv in kwargs.items():
            self.set(tmpk, tmpv)

    def get_attrs(self, whether_jsonable=False):
        attrdict = {}
        for tmpkey, tmpvalue in self.__dict__.items():
            if tmpkey not in self.except_attr_list():
                if whether_jsonable:
                    if isinstance(tmpvalue, datetime.datetime) or isinstance(tmpvalue, datetime.date):
                        tmpvalue = str(tmpvalue).split(".")[0]
                attrdict[tmpkey] = tmpvalue
        return attrdict

    # 对象内部调用函数
    def reset_sql_info(self):
        self._sql_info = {
            "do": "",
            "where": "",
            "group_by": "",
            "order_by": "",
            "lock": "",
        }

    def validate_saveable(self):
        pass

    def except_attr_list(self):
        return ["table_name", "_sql_info", "autocommit", "logger_errors"]

    def get_condition_str(self, condition_dict):
        wherestr = ""
        for col, value in condition_dict.items():
            collist = DORM.escape_string_for_sql(col).split("__")
            col = collist[0]
            if col in self.except_attr_list():
                continue
            judge_value = "="
            if len(collist) >= 2 and collist[-1] in ["gt", "gte", "lt", "lte", "in", "contains", "ne"]:
                for colindex in range(1, len(collist) - 1):
                    col += "__%s" % collist[colindex]
                if collist[-1] == "gt":
                    judge_value = ">"
                elif collist[-1] == "gte":
                    judge_value = ">="
                elif collist[-1] == "lt":
                    judge_value = "<"
                elif collist[-1] == "lte":
                    judge_value = "<="
                elif collist[-1] == "in":
                    judge_value = "IN"
                elif collist[-1] == "contains":
                    judge_value = "LIKE"
                elif collist[-1] == "ne":
                    judge_value = "!="

            # 拼接value
            if isinstance(value, int) or isinstance(value, float):
                if judge_value in ["IN", "LIKE"]:
                    raise ValueError("值为int类型的条件不可进行IN或者LIKE查询！")
                wherestr += "`%s` %s %s AND " % (col, judge_value, value)
            elif isinstance(value, str):
                if judge_value == "IN":
                    raise ValueError("值为str类型的条件不可进行IN查询！")
                if judge_value == "LIKE":
                    wherestr += "`%s` %s '%%%%%s%%%%' AND " % (col, judge_value,
                                                               DORM.escape_string_for_sql(value).replace("%", "%%"))
                else:
                    wherestr += "`%s` %s '%s' AND " % (col, judge_value,
                                                       DORM.escape_string_for_sql(value).replace("%", "%%"))
            elif isinstance(value, datetime.datetime):
                if judge_value in ["IN", "LIKE"]:
                    raise ValueError("值为datetime类型的条件不可进行IN或者LIKE查询！")
                wherestr += "`%s` %s '%s' AND " % (col, judge_value, value.strftime('%Y-%m-%d %H:%M:%S'))
            elif isinstance(value, datetime.date):
                if judge_value in ["IN", "LIKE"]:
                    raise ValueError("值为date类型的条件不可进行IN或者LIKE查询！")
                wherestr += "`%s` %s '%s' AND " % (col, judge_value, value.strftime('%Y-%m-%d'))
            elif isinstance(value, list):
                if judge_value == "IN":
                    valuestr = ""
                    for tmpvalue in value:
                        if isinstance(tmpvalue, int) or isinstance(tmpvalue, float):
                            valuestr += "%s," % tmpvalue
                        elif isinstance(tmpvalue, str):
                            valuestr += "'%s'," % DORM.escape_string_for_sql(tmpvalue)
                    valuestr = valuestr.strip(",")
                    wherestr += "`%s` %s (%s) AND " % (col, judge_value, valuestr.replace("%", "%%"))
                elif judge_value == "LIKE":
                    wherestr += "`%s` %s '%%%%%s%%%%' AND " % (col, judge_value,
                                                               DORM.escape_string_for_sql(json.dumps(value))
                                                               .replace("%", "%%"))
                else:
                    wherestr += "`%s` %s '%s' AND " % (col, judge_value, DORM.escape_string_for_sql(json.dumps(value))
                                                       .replace("%", "%%"))
            elif isinstance(value, dict):
                if judge_value == "IN":
                    raise ValueError("值为dict类型的条件不可进行IN查询！")
                if judge_value == "LIKE":
                    wherestr += "`%s` %s '%%%%%s%%%%' AND " % (col, judge_value,
                                                               DORM.escape_string_for_sql(json.dumps(value))
                                                               .replace("%", "%%"))
                else:
                    wherestr += "`%s` %s '%s' AND " % (col, judge_value,
                                                       DORM.escape_string_for_sql(json.dumps(value)).replace("%", "%%"))
            else:
                raise ValueError("不支持的值类型(%s)" % type(value))

        wherestr = wherestr[:-4] if wherestr else ""
        self._sql_info["where"] = wherestr if wherestr == "" else "WHERE %s" % wherestr
        return self._sql_info["where"]

    def get_update_str(self, update_dict):
        # 进入where更新
        if not isinstance(update_dict, dict):
            raise ValueError("执行条件更新时update_dict必须是字典！")
        udpatestr = ""
        for col, value in update_dict.items():
            col = DORM.escape_string_for_sql(col)
            if col in self.except_attr_list():
                continue
            # 拼接value
            if isinstance(value, int) or isinstance(value, float):
                udpatestr += "`%s`=%s," % (col, value)
            elif isinstance(value, str):
                udpatestr += "`%s`='%s'," % (col, DORM.escape_string_for_sql(value).replace("%", "%%"))
            elif isinstance(value, datetime.datetime):
                udpatestr += "`%s`='%s'," % (col, value.strftime('%Y-%m-%d %H:%M:%S'))
            elif isinstance(value, datetime.date):
                udpatestr += "`%s`='%s'," % (col, value.strftime('%Y-%m-%d'))
            elif isinstance(value, list) or isinstance(value, dict):
                udpatestr += "`%s`='%s'," % (col, DORM.escape_string_for_sql(json.dumps(value)).replace("%", "%%"))
            elif isinstance(value, None):
                # 应该写空字符串还是数字0，还是不处理？ 暂时不处理
                pass
            else:
                raise ValueError("不支持的值类型(%s)" % type(value))
        udpatestr = udpatestr.strip(",")
        return udpatestr

    def sync_attr_to_self(self, other_orm_model):
        for k, v in other_orm_model.__dict__.items():
            setattr(self, k, v)

    # 各种操作类方法，增删改查的初始化
    def save(self, force_insert=False, force_update=False):
        if force_insert:
            return self.insert()
        if force_update:
            if hasattr(self, "id"):
                return self.update()
            else:
                raise ValueError("force_update时必须有主键id")
        if hasattr(self, "id"):
            return self.update()
        else:
            return self.insert()

    def delete(self):
        self.reset_sql_info()
        self._sql_info["do"] = "DELETE FROM %s" % (self.table_name)
        self._sql_info["where"] = self.get_condition_str(self.__dict__)
        return self

    def query(self):
        """

        :param fetch: list/one/first/last
        :return:
        """
        self.reset_sql_info()
        self._sql_info["do"] = "SELECT * FROM %s" % (self.table_name)
        self._sql_info["where"] = self.get_condition_str(self.__dict__)
        return self

    def queryCount(self, query_column='*'):
        """

        :param fetch: list/one/first/last
        :return:
        """
        self.reset_sql_info()
        self._sql_info["do"] = "SELECT count(%s) AS query_count_result FROM %s" % (query_column,self.table_name)
        self._sql_info["where"] = self.get_condition_str(self.__dict__)
        result = self.execute()
        if len(result) > 0:
            return result[0].get('query_count_result')
        else:
            return 0

    def insert(self):
        self.reset_sql_info()
        self.validate_saveable()
        clostr, valuestr = "", ""
        for col, value in self.__dict__.items():
            if col in self.except_attr_list():
                continue
            # 拼接列
            clostr += "`%s`," % DORM.escape_string_for_sql(col)
            # 拼接value
            if isinstance(value, int) or isinstance(value, float):
                valuestr += "%s," % value
            elif isinstance(value, str):
                valuestr += "'%s'," % DORM.escape_string_for_sql(value).replace("%", "%%")
            elif isinstance(value, datetime.datetime):
                valuestr += "'%s'," % value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, datetime.date):
                valuestr += "'%s'," % value.strftime('%Y-%m-%d')
            elif isinstance(value, list) or isinstance(value, dict):
                valuestr += "'%s'," % DORM.escape_string_for_sql(json.dumps(value)).replace("%", "%%")
            elif isinstance(value, type(None)):
                valuestr += "NULL,"
            else:
                raise ValueError("不支持的值类型(%s)" % type(value))

        clostr = clostr.strip(",")
        valuestr = valuestr.strip(",")
        self._sql_info["do"] = "INSERT INTO %s(%s) VALUES (%s)" % (self.table_name, clostr, valuestr)
        return self

    def update(self, **update_attrs):
        self.reset_sql_info()
        if update_attrs:
            # 此时self.__dict__就是条件
            udpatestr = self.get_update_str(update_attrs)
            self._sql_info["do"] = "UPDATE %s SET %s" % (self.table_name, udpatestr)
            self._sql_info["where"] = self.get_condition_str(self.__dict__)
        else:
            # 进入自动更新
            if not hasattr(self, "id"):
                raise ValueError("自动更新时必须有主键id！")
            udpatestr = self.get_update_str(self.__dict__)
            self._sql_info["do"] = "UPDATE %s SET %s" % (self.table_name, udpatestr)
            self._sql_info["where"] = "WHERE id = %s" % self.id
        return self

    def where(self, **conditions):
        if self._sql_info["do"].startswith("INSERT "):
            raise ValueError("INSERT不需要使用where子句！")
        self._sql_info["where"] = self.get_condition_str(conditions)
        return self

    def group_by(self, group_by=""):
        if not self._sql_info["do"].startswith("SELECT "):
            raise ValueError("只有SELECT的时候才可以使用group_by！")

        self._sql_info["group_by"] = "GROUP BY %s" % group_by if group_by else ""
        return self

    def order_by(self, order_by=""):
        if not self._sql_info["do"].startswith("SELECT "):
            raise ValueError("只有SELECT的时候才可以使用order_by！")
        self._sql_info["order_by"] = "ORDER BY %s" % order_by if order_by else ""
        return self

    def lock_row_for_update(self):
        self._sql_info["lock"] = "for update"
        return self

    def lock_table(self):
        """ Lock table.

        Locks the object model table so that atomic update is possible.
        Simulatenous database access request pend until the lock is unlock()'ed.

        Note: If you need to lock multiple tables, you need to do lock them
        all in one SQL clause and this function is not enough. To avoid
        dead lock, all tables must be locked in the same order.

        See http://dev.mysql.com/doc/refman/5.0/en/lock-tables.html
        """
        cursor = connection.cursor()
        cursor.execute("LOCK TABLES %s WRITE" % self.table_name)
        row = cursor.fetchone()
        return row

    def unlock_table(self):
        """ Unlock the table. """
        cursor = connection.cursor()
        cursor.execute("UNLOCK TABLES")
        row = cursor.fetchone()
        return row

    def get_sql(self, force_execute=False):
        if self._sql_info["do"].startswith("INSERT "):
            # 进入insert执行
            sql = self._sql_info["do"]
        elif self._sql_info["do"].startswith("SELECT "):
            if force_execute is False and self._sql_info["where"] == "":
                raise ValueError("SELECT 必须有where子句，否则请使用force_execute=True强制执行！")
            sql = "%s %s %s %s %s" % (self._sql_info["do"], self._sql_info["where"],
                                      self._sql_info["group_by"], self._sql_info["order_by"],
                                      self._sql_info["lock"])
        elif self._sql_info["do"].startswith("DELETE "):
            if force_execute is False and self._sql_info["where"] == "":
                raise ValueError("DELETE 必须有where子句，否则请使用force_execute=True强制执行！")
            sql = "%s %s" % (self._sql_info["do"], self._sql_info["where"])
        elif self._sql_info["do"].startswith("UPDATE "):
            if force_execute is False and self._sql_info["where"] == "":
                raise ValueError("UPDATE 必须有where子句，否则请使用force_execute=True强制执行！")
            sql = "%s %s" % (self._sql_info["do"], self._sql_info["where"])
        else:
            raise ValueError("不合法的sql！")

        return sql

    def execute(self, fetch="list", force_execute=False, use_readonly=False):
        sql = self.get_sql(force_execute=force_execute)
        if self._sql_info["do"].startswith("SELECT "):
            cursor = DORM.execute_select_sql(sql, return_type="cursor", use_readonly=use_readonly)
            all_data = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            if fetch == "list":
                result = []
                for row in all_data:
                    tmporm = DORM(self.table_name)
                    # 把每一行的数据遍历出来放到Dict中
                    for i in range(0, len(col_names)):
                        setattr(tmporm, col_names[i], row[i])
                    result.append(tmporm)
                return result
            else:
                if all_data:
                    if fetch == "first":
                        rowindex = 0
                    elif fetch == "last":
                        rowindex = -1
                    elif fetch == "one":
                        if len(all_data) == 1:
                            rowindex = 0
                        else:
                            raise ValueError("query fetch one时 返回多个值")
                    else:
                        raise ValueError("query fetch 只能是list/one/first/last")
                    row = all_data[rowindex]
                    tmporm = DORM(self.table_name)
                    for i in range(0, len(col_names)):
                        setattr(tmporm, col_names[i], row[i])
                    self.sync_attr_to_self(tmporm)
                    return self
                else:
                    raise ValueError("query fetch 非list时没有查询到值")

        elif self._sql_info["do"].startswith("UPDATE "):
            return DORM.execute_update_sql(sql, autocommit=self.autocommit, logger_errors=self.logger_errors)
        elif self._sql_info["do"].startswith("DELETE "):
            return DORM.execute_update_sql(sql, autocommit=self.autocommit, logger_errors=self.logger_errors)
        elif self._sql_info["do"].startswith("INSERT "):
            retid = DORM.execute_update_sql(sql, autocommit=self.autocommit, logger_errors=self.logger_errors)
            setattr(self, "id", retid)
            return retid

if __name__ == "__main__":
    # porm = DORM("demo_people")
    # porm.query().where(add_time__gte=datetime.datetime.now(), id=10).group_by("age").order_by("age asc")
    # print(porm.get_sql())

    # retlist = DORM.execute_select_sql("select * from demo_people", json_keys=["display_name"])
    # print(retlist)

    d1 = DORM("demo_people")
    d2 = DORM("demp_pp")
