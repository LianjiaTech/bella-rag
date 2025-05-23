# coding:utf-8

import configparser


class MyConfig(configparser.ConfigParser):
    def __init__(self, defaults=None):
        configparser.ConfigParser.__init__(self, defaults=None)

    def optionxform(self, optionstr):
        return optionstr


class Config(object):
    """
    配置文件处理类，传入配置文件，生成配置dict。
    """

    @staticmethod
    def get_conf_dict_by_file(conf_file, encodeing = "utf-8"):
        cf = MyConfig()
        cf.read(conf_file, encoding=encodeing)
        conf_dict = {}
        sections = cf.sections()
        for section in sections:
            items = cf.items(section)
            conf_dict[section] = {}
            for item in items:
                conf_dict[section][item[0]] = item[1]
        return conf_dict

    @staticmethod
    def get_conf_dict_by_str(conf_str, case_sensitive=False):
        if case_sensitive:
            # cf = configparser.ConfigParser()
            cf = MyConfig()

        else:
            cf = configparser.ConfigParser()
            # cf = MyConfig()
        cf.read_string(conf_str)
        conf_dict = {}
        sections = cf.sections()
        for section in sections:
            items = cf.items(section)
            conf_dict[section] = {}
            for item in items:
                conf_dict[section][item[0]] = item[1]
        return conf_dict
