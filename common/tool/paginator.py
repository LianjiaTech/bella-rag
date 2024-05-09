def pagination(lists, page, limit, ret='dict'):
    page, limit = int(page), int(limit)
    start, stop = limit * (page - 1), limit * page
    rets = lists[start: stop]
    if ret == 'list':
        return rets, page, limit, len(rets), len(lists)
    return {
        'datalist': rets,
        'page': page,
        'limit': limit,
        'pagecount': len(rets),
        'totalcount': len(lists),
    }
