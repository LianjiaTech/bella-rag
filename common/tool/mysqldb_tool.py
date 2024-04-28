import os
import sys
import pymysql
import logging
import traceback

rootpath = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
syspath = sys.path
sys.path = []
sys.path.append(rootpath)  # 指定搜索路径绝对目录
sys.path.extend([rootpath + i for i in os.listdir(rootpath) if i[0] != "."])  # 将工程目录下的一级目录添加到python搜索路径中
sys.path.extend(syspath)


class DBTool(object):
    """数据库处理类
    处理数据库相关操作
    """

    def __init__(self, host='', port=3306, username='', password='', db='', is_dict_cursor=True,
                 max_effect_rows_count=100):
        self.__open = False

        self.__host = host
        self.__port = port
        self.__username = username
        self.__password = password
        self.__db = db
        self.__isDictCursor = is_dict_cursor
        self.errMsg = ""
        self.max_effect_rows_count = max_effect_rows_count

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.release()

    def set_cursor_dict(self, state=True):
        self.__isDictCursor = state

    def connect(self):
        if self.__open:
            try:
                self.__conn.ping()
                return True
            except:
                # 连接出现异常了，重新连接
                pass
        try:
            if self.__db == '':
                # 打开数据库连接
                self.__conn = pymysql.connect(host=self.__host, user=self.__username,
                                              password=self.__password, port=self.__port)
            else:
                self.__conn = pymysql.connect(host=self.__host, user=self.__username,
                                              password=self.__password, port=self.__port, db=self.__db)
            self.__conn.set_charset('utf8')
            self.__open = True
            return True
            # logging.debug( u"DBTool.py: connect: 数据库连接成功。")
        except Exception as e:
            logging.error(traceback.format_exc())
            self.errMsg = "数据库连接异常！\n%s" % traceback.format_exc()
            return False

    def release(self):
        if self.__open:
            try:
                self.__conn.close()
            except Exception as e:
                logging.error(traceback.format_exc())
            finally:
                self.__open = False
                # if self.__open == False:
                #     logging.debug( u"DBTool.py: release: 数据库连接连接断开。")

    def flush(self):
        self.release()
        self.connect()

    def execute_sql(self, sql, auto_release=False):
        """执行sql语句
        :param sql: excel传入的sql.
        :return: 返回成功失败,只有所有的都成功才返回成功
        """
        try:
            self.connect()
            # logging.debug ("DBTool.py: execute_sql: 执行SQL：%s " % sql)
            if self.__isDictCursor:
                cursor = self.__conn.cursor(pymysql.cursors.DictCursor)
            else:
                cursor = self.__conn.cursor()
            cursor.execute('SET NAMES utf8;')
            cursor.execute('SET CHARACTER SET utf8;')
            cursor.execute('SET character_set_connection=utf8;')
            cursor.execute(sql)
            self.__conn.commit()
            data = cursor.fetchall()
            # 关闭数据库连接
            return data
        except Exception as e:
            logging.error(traceback.format_exc())
            logging.debug("DBTool.py: execute_sql : 发生异常：%s, 异常类型%s." % (e, type(e)))
            return False
        finally:
            if auto_release:
                self.release()

    def execute_update_sql(self, sql, auto_release=False):
        """执行sql语句
        :param sql: excel传入的sql.
        :return: 返回成功失败,只有所有的都成功才返回成功
        """
        try:
            self.connect()
            # logging.debug ("DBTool.py: execute_sql: 执行SQL：%s " % sql)
            if self.__isDictCursor:
                cursor = self.__conn.cursor(pymysql.cursors.DictCursor)
            else:
                cursor = self.__conn.cursor()
            cursor.execute('SET NAMES utf8;')
            cursor.execute('SET CHARACTER SET utf8;')
            cursor.execute('SET character_set_connection=utf8;')
            res = cursor.execute(sql)
            self.__conn.commit()
            # 关闭数据库连接
            return res
        except Exception as e:
            logging.error(traceback.format_exc())
            print(traceback.format_exc())
            logging.debug("DBTool.py: execute_sql : 发生异常：%s, 异常类型%s." % (e, type(e)))
            return False
        finally:
            if auto_release:
                self.release()

    def get_effected_rows_count(self, sql, auto_release=False):
        """执行sql语句

        :param sql: excel传入的sql.
        :return: 返回成功失败,只有所有的都成功才返回成功
        """
        sql = sql.strip()
        sql_lower = sql.lower()
        try:
            self.connect()
            cursor = self.__conn.cursor()
            cursor.execute('SET NAMES utf8;')
            cursor.execute('SET CHARACTER SET utf8;')
            cursor.execute('SET character_set_connection=utf8;')
            curd_judge_string = sql_lower[0:6]
            # logging.debug(u"DBTool.py:get_effected_rows_count:curd_judge_string:[%s]" % curd_judge_string)
            if curd_judge_string == "select":
                # logging.debug(u"DBTool.py:get_effected_rows_count:INTO select.")
                cursor.execute(sql)
                # logging.debug(u"DBTool.py:get_effected_rows_count: SELECT影响行数：%d" % cursor.rowcount)
                return cursor.rowcount
            elif curd_judge_string == 'update':
                sql_lower = sql.lower().strip()
                where_loc = sql_lower.find('where')
                set_loc = sql_lower.find('set')
                table_name = sql[6:set_loc].strip()
                where_str = sql[where_loc + 5:].strip()
                if where_loc == -1:
                    return self.max_effect_rows_count + 1
                new_sql = "select * from %s where %s" % (table_name, where_str)
                cursor.execute(new_sql)
                return cursor.rowcount
            elif curd_judge_string == 'delete':
                # delete from tablename where where cb = 2  to select * from tablename where xxxxxx
                sql_lower = sql.lower().strip()
                from_loc = sql_lower.find('from')
                where_loc = sql_lower.find('where')
                table_name = sql[from_loc + 4:where_loc == -1 and len(sql) or where_loc + 1]
                where_str = sql[where_loc + 5:].strip()
                if where_loc == -1:
                    return self.max_effect_rows_count + 1
                new_sql = "select * from %s where %s" % (table_name, where_str)
                cursor.execute(new_sql)
                return cursor.rowcount
            elif curd_judge_string == 'insert':
                return 1
            else:
                return -1
        # 关闭数据库连接
        except Exception as e:
            logging.error(traceback.format_exc())
            return -1
        finally:
            if auto_release:
                self.release()
