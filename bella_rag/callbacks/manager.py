import threading

thread_local = threading.local()


def init_callbacks(callbacks):
    if not hasattr(thread_local, 'callbacks'):
        thread_local.callbacks = []
    thread_local.callbacks = callbacks if callbacks else []


def register_callback(callback):
    if not hasattr(thread_local, 'callbacks'):
        thread_local.callbacks = []
    thread_local.callbacks.append(callback)


def get_callbacks():
    if not hasattr(thread_local, 'callbacks'):
        return []
    return thread_local.callbacks


def clear_callbacks():
    if hasattr(thread_local, 'callbacks'):
        del thread_local.callbacks
