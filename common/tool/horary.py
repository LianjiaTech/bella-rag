def time_split(t):
    return (t.split('T')[0] if 'T' in t else t.split(' ')[0]) if not t.startswith('1970') else ''


def time_joint(t1, t2):
    t = '{}/{}'.format(t1, t2)
    return '' if t == '/' or t == '-/-' else t


def is_time_gt(t1, t2):
    if len(t1) == 10:
        return t1 > t2
    return t1 > t2 + ' 23:59:59'


def is_time_lt(t1, t2):
    if len(t1) == 10:
        return t1 < t2
    return t1 < t2 + ' 00:00:00'
