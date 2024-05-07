# -*- coding:utf-8 -*-
# @Time: 2024/5/7 11:49
# @Author: dongmenghui
# @Email: dongmenghui001@ke.com
# @File: unstructuredReader.py

from llama_index.readers.web import UnstructuredURLLoader

def unstructuredReader():
    urls = [
        "https://www.understandingwar.org/backgrounder/russian-offensive-campaign-assessment-february-8-2023",
        "https://www.understandingwar.org/backgrounder/russian-offensive-campaign-assessment-february-9-2023",
    ]

    loader = UnstructuredURLLoader(
        urls=urls, continue_on_failure=False, headers={"User-Agent": "value"}
    )
    loader.load_data()

if __name__ == "__main__":
    unstructuredReader()