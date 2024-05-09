# -*- coding:utf-8 -*-
# @Time: 2024/5/7 11:49
# @Author: dongmenghui
# @Email: dongmenghui001@ke.com
# @File: unstructuredReader.py

from llama_index.readers.web import UnstructuredURLLoader
import unstructured

def unstructuredReader():
    urls = [
        "http://scm.ke.com/api/v1/wiki/confluence/page/content?wikiUrl=https://wiki.lianjia.com/pages/viewpage.action?pageId=1240439072"    ]

    reader = UnstructuredURLLoader(
        urls=urls, continue_on_failure=False, headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"}
    )
    return reader.load_data()

if __name__ == "__main__":
    print(unstructuredReader())