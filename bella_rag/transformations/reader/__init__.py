def read_all(stream) -> bytes:
    buff = bytearray()
    while True:
        data = stream.read(4096)
        if not data:
            break
        buff.extend(data)
    return bytes(buff)
