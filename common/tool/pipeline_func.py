import json
from init.settings import kafka_handle
from common.tool.script_log import ScriptLog
logger = ScriptLog()


def sync_execute_info_to_ke_ones(recv_dict, execute_status, result_dict):
    logger.debug("start sync_execute_info_to_ke_ones[%s-%s]"
                 % (recv_dict["execute_id"], execute_status))
    recv_dict["execute_status"] = execute_status
    recv_dict["result_dict"] = result_dict
    kafka_handle.send_producer_msg(json.dumps(recv_dict).encode("utf8"))
    logger.debug("end sync_execute_info_to_ke_ones[%s-%s]"
                 % (recv_dict["execute_id"], execute_status))
    return recv_dict


def sync_finished_autorun_signal_to_ke_ones(recv_dict):
    logger.debug("start sync_finished_autorun_signal_to_ke_ones[%s-%s]"
                 % (recv_dict["execute_id"], json.dumps(recv_dict)))
    recv_dict["do"] = "pipeline_finished_check_autorun"
    kafka_handle.send_producer_msg(json.dumps(recv_dict).encode("utf8"))
    logger.debug("end sync_finished_autorun_signal_to_ke_ones[%s-%s]"
                 % (recv_dict["execute_id"], json.dumps(recv_dict)))
    return recv_dict

if __name__ == "__main__":
    print(0 is not None)
