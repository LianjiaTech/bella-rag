import json
import re

from init.const import ONLINECHECK_STATUS


# 描述
def fdesc(s):
    if not s:
        return ''
    try:
        return str(json.loads(s))
    except:
        return s


# PM
def __pm_split(pm):
    splits = re.split(r'[()（）]', pm.strip())
    if len(splits) >= 3:
        displayName, name = splits[0], splits[1]
    elif len(splits) == 2:
        displayName, name = splits
    else:
        displayName, name = splits[0], ''
    return {
        'name': name,
        'displayName': displayName,
    }


def __pm_split1(pm):
    splits = re.split(r'[()（）]', pm.strip())
    if len(splits) >= 3:
        displayName, name = splits[0], splits[1]
    elif len(splits) == 2:
        displayName, name = splits
    else:
        displayName, name = splits[0], ''
    return {
        'value': name,
        'text': displayName,
        'name': name,
        'displayName': displayName,
    }


def fpm(s):
    s = s.strip()
    if not s:
        return []
    try:
        pms = json.loads(s)
    except:
        pms = s.split(',')
    return [pm.strip() for pm in pms if pm.strip()]


def fpm0(s):
    s = s.strip()
    if not s:
        return []
    try:
        pms = json.loads(s)
    except:
        pms = s.split(',')
    return [__pm_split(pm) for pm in pms if pm.strip()]


def fpm1(s):
    s = s.strip()
    if not s:
        return []
    try:
        pms = json.loads(s)
    except:
        pms = s.split(',')
    return [__pm_split1(pm) for pm in pms if pm.strip()]


def fpm2(s):
    s = s.strip()
    if not s:
        return ''
    try:
        pms = json.loads(s)
    except:
        pms = [s]
    return ','.join(pms)


def fcreator(s):
    s = s.strip()
    if not s:
        return {}
    return __pm_split1(s)


# 验收状态
def fonlinecheck_status(s):
    return ONLINECHECK_STATUS.get(s, '')


# 相关角色
def frelate_role(s):
    s = s.strip()
    if not s:
        return []
    try:
        roles = json.loads(s)
    except:
        roles = []
    return roles


def frelate_role2(s):
    s = s.strip()
    if not s:
        return []
    try:
        roles = json.loads(s)
    except:
        roles = []
    return [role['value'] for role in roles]


# 埋点需求
def frequest_approver(s):
    s = s.strip()
    if not s:
        return []
    try:
        approvers = json.loads(s)
    except:
        approvers = []
    return approvers
