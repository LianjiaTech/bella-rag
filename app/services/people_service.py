from common.tool.orm import DORM


class DemoPeopleService(object):
    """
    一个处理人员的类
    """

    @staticmethod
    def add_people():
        """
        添加一个人的函数。
        :return: bool 是否添加成功
        """
        DORM(table_name="demo_people", name="wangjiliang").save().execute()
        return True
