# -*- coding:UTF-8 -*-
from init.init_django import *
import time
import hmac
import hashlib
import json
import traceback
import requests
from common.helper.api import ApiReturn

from init.settings import conf_dict

BPM_KEY = conf_dict['BPM']['key']
BPM_SECRET = conf_dict['BPM']['secret']
BPM_SERVER = conf_dict['BPM']['server']


###签名及组装请求部分
def send_post(url, post_data):
    headers = {'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'}
    r = requests.post(url, data=post_data, headers=headers)
    resp_result = r.text
    return resp_result


def openapi_client(method, params):
    args = dict()
    args['timestamp'] = get_millisecond()
    args['cmd'] = method
    args['format'] = "json"
    args['access_key'] = BPM_KEY
    args['sig_method'] = "HmacMD5"
    post_data = dict(args, **params)
    sig = make_sign(post_data, BPM_SECRET)
    post_data['sig'] = sig
    return send_post(BPM_SERVER, post_data)


def make_sign(post_data, secret):
    keys_sorted = sorted(post_data.keys())
    sig_str = secret
    for key in keys_sorted:
        sig_str = sig_str + "%s%s" % (key, post_data[key])
    return hmac_md5(sig_str.encode(encoding="utf-8"), secret.encode(encoding="utf-8"))


def hmac_md5(query, secret):
    enc_res = hmac.new(secret, query, hashlib.md5).hexdigest()
    return enc_res.upper()


def get_millisecond():
    timestamp = int(round(time.time() * 1000))
    return timestamp


### 以下为封装api

def get_processIns_status(processInstId=''):
    method = "process.inst.get"
    params = {'processInstId': processInstId}
    res = json.loads(openapi_client(method, params))
    if 'data' in res:
        return res['data']['controlState']
    return ''


# 终止流程
def terminate_process_by_insId(processInstId='', uid=''):
    method = "process.terminate"
    params = {'processInstId': processInstId, 'uid': uid}
    res = json.loads(openapi_client(method, params))
    if 'errorCode' in res:
        return ApiReturn(code=ApiReturn.CODE_ERROR, message=res['msg']).to_json()
    return ApiReturn(code=ApiReturn.CODE_OK, message='terminate process ok').to_json()


# 创建流程并发起提单操作
def create_process_and_start(processBusinessKey='', uid='', data=None):
    if data is None or data == {} or data == '':
        return ApiReturn(code=ApiReturn.CODE_ERROR, message='body不能为空').to_json()
    params = {}
    if processBusinessKey.startswith('emer_publish') and data:
        params = generate_emer_publish_data(processBusinessKey, uid, data)
    if processBusinessKey.startswith('app_release') and data:
        params = generate_app_release_data(processBusinessKey, uid, data)
    if processBusinessKey.startswith('small_program') and data:
        params = generate_small_program_data(processBusinessKey, uid, data)
    if processBusinessKey.startswith('regular_online') and data:
        params = generate_regular_online_data(processBusinessKey, uid, data)

    try:
        create_res = json.loads(openapi_client('ke.process.createAndStart', params))
        print("[创建流程实例返回结果：]%s" % (create_res))
        if 'errorCode' in create_res:
            return ApiReturn(code=ApiReturn.CODE_ERROR, message=create_res['msg'], body={}).to_json()
        else:
            print('完成任务并自动转下一节点,并生成审核记录')
            print(process_to_next(create_res['data']['taskInstId'], uid))
            return ApiReturn(code=ApiReturn.CODE_OK, message='ok', body=create_res['data']).to_json()
    except Exception as e:
        return ApiReturn(code=ApiReturn.CODE_ERROR, message=traceback.format_exc()).to_json()


# 创建流程并发起提单操作
def create_process(processBusinessKey='', uid='', data=None):
    if data is None or data == {} or data == '':
        return ApiReturn(code=ApiReturn.CODE_ERROR, message='body不能为空').to_json()
    params = {}
    if processBusinessKey.startswith('emer_publish') and data:
        params = generate_emer_publish_data(processBusinessKey, uid, data)
    if processBusinessKey.startswith('app_release') and data:
        params = generate_app_release_data(processBusinessKey, uid, data)
    if processBusinessKey.startswith('small_program') and data:
        params = generate_small_program_data(processBusinessKey, uid, data)
    if processBusinessKey.startswith('small_program') and data:
        params = generate_regular_online_data(processBusinessKey, uid, data)
    try:
        create_res = json.loads(openapi_client('ke.process.createAndStart', params))
        print("[创建流程实例返回结果：]%s" % (create_res))
        if 'errorCode' in create_res:
            return ApiReturn(code=ApiReturn.CODE_ERROR, message=create_res['msg'], body={}).to_json()
        else:
            print('流程已创建成功')
            print('完成任务并自动转下一节点,并生成审核记录')
            print(process_to_next(create_res['data']['taskInstId'], uid))
            return ApiReturn(code=ApiReturn.CODE_OK, message='ok', body=create_res['data']).to_json()
    except Exception as e:
        return ApiReturn(code=ApiReturn.CODE_ERROR, message=traceback.format_exc()).to_json()


def generate_emer_publish_data(processBusinessKey='', uid='', data=None):
    if data is None:
        data = {}
    params = {}
    params['recordData'] = json.dumps(data)
    params['uid'], params['processBusinessKey'] = uid, processBusinessKey
    params['processDefId'] = conf_dict['BPM']['emer_pub_pro_defid']
    params['boName'] = conf_dict['BPM']['emer_pub_pro_boname']
    print(params)
    return params


def generate_app_release_data(processBusinessKey='', uid='', data=None):
    if data is None:
        data = {}
    params = dict()
    params['recordData'] = json.dumps(data)
    params['uid'], params['processBusinessKey'] = uid, processBusinessKey
    params['processDefId'] = conf_dict['BPM']['app_release_pro_defid']
    params['boName'] = conf_dict['BPM']['app_release_pro_boname']
    return params


def generate_small_program_data(processBusinessKey='', uid='', data=None):
    if data is None:
        data = {}
    params = dict()
    params['recordData'] = json.dumps(data)
    params['uid'], params['processBusinessKey'] = uid, processBusinessKey
    params['processDefId'] = conf_dict['BPM']['small_program_pro_defid']
    params['boName'] = conf_dict['BPM']['small_program_pro_boname']
    return params


def generate_regular_online_data(processBusinessKey='', uid='', data=None):
    if data is None:
        data = {}
    params = dict()
    params['recordData'] = json.dumps(data)
    params['uid'], params['processBusinessKey'] = uid, processBusinessKey
    params['processDefId'] = conf_dict['BPM']['regular_online_pro_defid']
    params['boName'] = conf_dict['BPM']['regular_online_pro_boname']
    return params

# 根据流程实例id查询审批记录，直接返回响应报文
def get_process_comments_by_insId(processInstid=''):
    method = "process.comments.get"
    params = {'processInstId': processInstid}
    return openapi_client(method, params)


def get_process_comments_by_busikey(processBusinessKey=''):
    method = "process.comments.get.businessKey"
    params = {'processInstId': processBusinessKey}
    return openapi_client(method, params)


def process_to_next(taskInstId='', uid=''):
    method = "ke.process.completeTaskAndNext"
    params = {'taskInstId': taskInstId, 'uid': uid}
    print(openapi_client(method, params))


# 获取最后一条审批意见为同意的记录,返回：['同意', '第二环节']
def get_last_ok_comment(processInsId=''):
    if processInsId:
        comments = json.loads(get_process_comments_by_insId(processInsId))
        print(comments)
        if 'data' in comments and comments['data']:
            for i in range(len(comments['data']) - 1, -1, -1):
                com_dict = comments['data'][i]
                if 'actionName' in com_dict.keys() and com_dict['actionName'] == '同意':
                    return com_dict['actionName'], com_dict['activityName'], com_dict['createUser']
        return ''
    else:
        return ''


# 查询是否有驳回操作
def is_denied(processInsId=''):
    flag = False
    deny_user = ''
    if processInsId:
        comments = json.loads(get_process_comments_by_insId(processInsId))
        if 'data' in comments and comments['data']:
            for i in range(len(comments['data'])):
                com_dict = comments['data'][i]
                if 'actionName' in com_dict.keys() and com_dict['actionName'] == '驳回':
                    flag = True
                    deny_user = com_dict['createUser']
        return flag, deny_user
    else:
        return flag, deny_user


def get_ins_by_bizkey(processBusinessKey=''):
    params = {"processBusinessKey": processBusinessKey}
    method = "process.inst.get.businessKey"
    return openapi_client(method, params)


def get_approve_url_by_process_inst_id(process_inst_id, target_user_code):
    params = {'processInstIds': json.dumps([process_inst_id])}
    resp = json.loads(openapi_client("ke.task.query.active", params))
    task_id = ''
    for item in resp['data']:
        if item['TARGET'] == target_user_code:
            task_id = item['ID']
    if task_id:
        approve_url = '%s?cmd=CLIENT_BPM_FORM_MAIN_PAGE_OPEN&processInstId=%s&taskInstId=%s&openState=1' % \
                      (conf_dict['BPM']['approve_server'], process_inst_id, task_id)
    else:
        approve_url = '%s?cmd=CLIENT_BPM_FORM_MAIN_PAGE_OPEN&processInstId=%s&openState=1' % \
                      (conf_dict['BPM']['approve_server'], process_inst_id)
    print(approve_url)
    return approve_url


def main():
    app_data = {
        "CLIENT": "贝壳找房",
        "SYS_TYPE": "IOS",
        "APPLY_TYPE": "紧急发版",
        "TITLE": "贝壳找房IOS端V10.0.0版本紧急发版",
        "VERSION": "V10.0.0",
        "APPLY_REASON": "紧急需求",
        "BUG_IMPACT": "10个用户无法登陆",
        "BUG_DETAIL": "一个线上BUG导致，已紧急修复",
        "BUG_PATH": "...",
        "COM_OP": "二手房C端",
        "COM_INFO": "Lianjia_Beike_XXX(10.0.0)",
        "TREATMENT": "改了BUG,测试通过，可以上线",
        "UPGRADE_METHOD": "紧急发版",
        "RELEASE_TIME": "2019-08-02 15:15:42",
        "MANAGER": "20358235",
        "DIRECTOR": "26023080",
        "SPECIAL": "26531394",
    }
    # res = create_process_and_start('app_release_0027','26531394',app_data)
    # print(res)
    # processinsId = json.loads(res)['body']['processInstId']
    # #
    emer_data = {
        "APPLY_TYPE": "紧急需求线上测试",
        "APPLY_REASON": "紧急需求线上测试",
        "BUG_IMPACT": "十万人不能登录",
        "BUG_DETAIL": "一个恐怖的线上bug",
        "EXPECTED_ONLINE_TIME": "2019-08-08 15:15:42",
        "SYSTEM": "贝壳",
        "SUB_SYSTEM": "基础平台中心/工程效率组",
        "SCOPE": "仅前端",
        "MANAGER": "26033077 20358235",
        "DIRECTOR": "26023080 23093953",
        "SPECIAL": "26531394",
    }
    res = create_process_and_start('emer_publish_abc002x', '26531394', emer_data)
    print(res)


# 查询
# print('comments res:\n %s' % (get_process_comments_by_insId(processinsId)))
# print('comments res:\n %s' % (get_process_comments_by_insId('2b20d78d-0578-499a-b792-f08b65c52f7c')))
# 根据业务id获取流程实例对象
# print(get_ins_by_bizkey("app_release_0026"))
# 	终止流程
# 	print('terminate res:\n %s' % terminate_process_by_insId('d30b8d68-9893-4129-bb54-2de20d7f386a','26531394'))
# 	查询流程实例的状态
# 	print('status res:\n %s' % get_processIns_status(processinsId))
# 	print('status res:\n %s' % get_processIns_status('d30b8d68-9893-4129-bb54-2de20d7f386a'))
# 	print(is_denied('8513d8c3-f3d9-4a42-b420-57a68581ba51'))
if __name__ == '__main__':
    # main()
    # params = dict()
    # print(get_process_comments_by_insId('a1c2bf6f-bdb7-4c13-89f9-a9063455050b'))
    small_program = {
        'PRODUCT': '贝壳1',
        'CHANNEL': '微信1',
        'VERSION': '1.0.1',
        'APPLY_TYPE': '紧急小程序申请',
        'TITLE': '测试发版',
        'APPLY_REASON': '测试原因',
        'BUG_IMPACT': 'BUG影响',
        'BUG_DETAIL': 'BUG详情',
        'BUG_PATH': '问题路径',
        'COM_OP': '测试小程序',
        'TREATMENT': '处理111',
        'RELEASE_TIME': '2019-11-11 15:15:42',
        'MANAGER': '23093953 26033077',
        'DIRECTOR': '20383112 20358235'
    }
    res = create_process('small_program_abc002x_04', '26023080', small_program)
    print(res)
# params = {'processInstIds': json.dumps(['106af7bd-6695-429c-9862-6cc2d827ff64'])}
# get_last_ok_comment('')
# get_last_ok_comment('106af7bd-6695-429c-9862-6cc2d827ff64')
# # params['processInstIds'] = ['a003b087-ed36-4835-8a8a-8f848593a8c5']
# # params['processDefId'] = conf_dict['BPM']['emer_pub_pro_defid']
# params['boName'] = conf_dict['BPM']['emer_pub_pro_boname']
# print(openapi_client("ke.task.query.active", params))
#
# params = dict()
# params = {'taskInstId':'4959e0db-1a87-4687-af79-2531e51bfa2e','uid':'26023080'}
# print(openapi_client('ke.process.completeTaskAndNext', params))
