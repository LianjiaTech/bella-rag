import json
import time


class ConvertTool(object):

    @staticmethod
    def force_convert_to_obj(basejsonstr):
        try:
            res = json.loads(basejsonstr)
            return res
        except:
            res = eval(basejsonstr)
            return res