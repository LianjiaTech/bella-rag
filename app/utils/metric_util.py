import os
import re
from collections import defaultdict

import resource

if os.name == 'nt':  # 如果是Windows系统
    resource.getpagesize = lambda: 4096  # 设置页面大小为4096字节

from prometheus_client import Histogram, Counter, REGISTRY

counters = defaultdict(lambda: None)


def format_metric_name(name):
    # 将无效字符替换为下划线
    return re.sub(r'[^a-zA-Z0-9_:]', '_', name)


def histogram_with_buckets(key, buckets, labels):
    key = format_metric_name(key)
    histogram = Histogram(key, key, labelnames=labels, buckets=buckets, registry=REGISTRY)
    return histogram


def get_counter(key, labelnames=None):
    key = format_metric_name(key)
    if counters[key] is None:
        if labelnames:
            counters[key] = Counter(key, key, labelnames=labelnames, registry=REGISTRY)
        else:
            counters[key] = Counter(key, key, registry=REGISTRY)
    return counters[key]


def increment_counter_with_tag(key, tag_key, tag_value):
    counter = get_counter(key, labelnames=[tag_key])
    counter.labels(tag_value).inc()


def increment_counter(key):
    counter = get_counter(key)
    counter.inc()
