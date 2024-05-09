# -*- coding:utf-8 -*-
# @Time: 2024/5/7 11:14
# @Author: dongmenghui
# @Email: dongmenghui001@ke.com
# @File: base.py

# https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/readers/llama-index-readers-openapi

from llama_index.readers.openapi import OpenAPIReader

def openapi_reader():
    openapi_reader = OpenAPIReader(discard=["info", "servers"])
    openapi_reader.load_data("path/to/openapi.json")
    return openapi_reader

if __name__ == "__main__":
    print(openapi_reader())