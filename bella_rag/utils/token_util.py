import hashlib
import os


def init_tiktoken():
    # 读取缓存目录 /resources/tiktoken_files
    TIKTOKEN_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../resources/tiktoken_files")

    # 重命名缓存文件
    HTTP_URL = "https://openaipublic.blob.core.windows.net/encodings/"
    path = os.listdir(TIKTOKEN_CACHE_DIR)
    tiktoken_vocabs = [p for p in path if os.path.isfile(f"{TIKTOKEN_CACHE_DIR}/{p}") and p.endswith(".tiktoken")]
    for vocab in tiktoken_vocabs:
        with open(os.path.join(TIKTOKEN_CACHE_DIR, vocab), "rb") as rf:
            with open(os.path.join(TIKTOKEN_CACHE_DIR, hashlib.sha1(f"{HTTP_URL}{vocab}".encode()).hexdigest()),
                      "wb") as wf:
                wf.write(rf.read())
    print(f'init tiktokens:{path}')