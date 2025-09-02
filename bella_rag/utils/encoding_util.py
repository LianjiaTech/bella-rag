def remove_non_utf8_chars(text: str) -> str:
    # 将字符串编码为字节，忽略无法编码的字符
    encoded_bytes = text.encode('utf-8', 'ignore')
    # 将字节解码回字符串
    decoded_text = encoded_bytes.decode('utf-8')
    return decoded_text
