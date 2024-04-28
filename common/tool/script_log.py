import datetime


class ScriptLog(object):
    # singleton_obj = None
    # def __new__(cls, *args, **kwargs):
    #     if cls.singleton_obj is None:
    #         cls.singleton_obj = super().__new__(cls)
    #     return cls.singleton_obj

    def __init__(self, level="DEBUG", max_log_count=100):
        """
        :param level: INFO/DEBUG/WARNING/ERROR
        """
        if level in ["INFO", "DEBUG", "WARNING", "ERROR"]:
            self.level = level
            self.lastest_log_list = []
            self.max_log_count = max_log_count
        else:
            raise Exception("Must be %s" % ["INFO", "DEBUG", "WARNING", "ERROR"])

    def process_log_list(self, logmsg):
        print(logmsg)
        if len(self.lastest_log_list) >= self.max_log_count:
            for i in range(0, len(self.lastest_log_list) - self.max_log_count + 1):
                self.lastest_log_list.pop(i)
        self.lastest_log_list.append(logmsg)

    def parse_latest_log_list_to_str(self):
        return "\n".join(self.lastest_log_list)

    def info(self, msg):
        self.process_log_list("%s INFO   : %s" % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg))

    def debug(self, msg):
        if self.level == "DEBUG":
            self.process_log_list("%s DEBUG  : %s" % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg))

    def warning(self, msg):
        self.process_log_list("%s WARNING: %s" % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg))

    def error(self, msg):
        self.process_log_list("%s ERROR  : %s" % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), msg))

script_logger = ScriptLog("DEBUG")

if __name__ == "__main__":
    a = ScriptLog("INFO", max_log_count=5)
    print(a.level)
    a.info("11")
    a.info("22")
    a.info("33")
    a.info("44")
    a.info("55")
    a.info("66")
    a.info("77")
    a.info("88")
    a.info("99")
    print(a.lastest_log_list)