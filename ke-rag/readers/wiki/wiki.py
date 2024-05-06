# -*- coding:utf-8 -*-
# @Time: 2024/5/6 19:22
# @Author: dongmenghui
# @Email: dongmenghui001@ke.com
# @File: wiki.py
# @Description:获取wiki数据
from pathlib import Path

import html2text
from llama_index.core import SimpleDirectoryReader
from llama_index.readers.file import HTMLTagReader
from bs4 import BeautifulSoup
from htmlReader import HTMLReader

def html_tag_reader(file_path):
    file_path = Path(file_path)
    # 创建HTMLTagReader实例，使用通配符选择器匹配所有标签
    reader = HTMLTagReader(True)

    # 使用load_data方法读取HTML文件内容
    documents = reader.load_data(file=file_path)

    # 打印提取的内容
    for doc in documents:
        print(doc.text)


def text_reader(file_path):
    file_path = Path(file_path)
    reader = HTMLReader()
    # 使用load_data方法读取HTML文件内容
    documents = reader.load_data(file=file_path)

    # 打印提取的内容
    for doc in documents:
        print(doc.text)





if __name__ == "__main__":
    file_path = "/Users/dongmenghui/Desktop/test/test.html"
    # html_tag_reader(file_path)
    text_reader(file_path)



