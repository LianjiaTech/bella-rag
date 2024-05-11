# -*- coding:utf-8 -*-
# @Time: 2024/4/30 15:39
# @Author: dongmenghui
# @Email: dongmenghui001@ke.com
# @File: base.py.py

from llama_index.core.node_parser import SimpleFileNodeParser
from llama_index.readers.file import FlatReader
from pathlib import Path

def simple_file_reader():
    reader = FlatReader()
    files_content = {
        "html_file": reader.load_data(Path("/Users/dongmenghui/Desktop/test/test.html")),
        "md_file": reader.load_data(Path("/Users/dongmenghui/Desktop/test/test-md.md"))
    }
    for key, value in files_content.items():
        print(value[0].metadata)
        print(value[0])
        print("----")
    return files_content

def simple_file_node_parser():
    files_content = simple_file_reader()
    md_file = files_content["md_file"]
    print(md_file[0].metadata)
    print(md_file[0])
    html_file = files_content["html_file"]
    print(html_file[0].metadata)
    print(html_file[0])
    parser = SimpleFileNodeParser()
    md_nodes = parser.get_nodes_from_documents(md_file)
    html_nodes = parser.get_nodes_from_documents(html_file)
    for node in md_nodes:
        print("md_node",node.metadata)
        print("md_node",node.text)
        print("----")
    print("--------------------------")
    for node in html_nodes:
        print("html_node",node.metadata)
        print("html_node",node.text)
        print("----")


'''
md_node {'Header_2': '背景', 'filename': 'test-md.md', 'extension': '.md'}
md_node 背景

贝壳一直处于高速发展阶段，每天产出大量需求，需要快速迭代，但测试环境的搭建和维护成本非常巨大，严重阻碍了产品的迭代速度。主要问题：

1. 测试应用部署运维比较传统和多样化，不同团队开发自己的环境管理系统或没有自己的系统，下层对接SRE提供的虚拟机混布应用，还有一些业务线是自运维的，大量的工单和人工审批流程浪费了SRE、rd、qa很多时间，测试资源成本持续上涨。
2. 缺乏统一的构建部署标准、用户需要自己完成应用的构建和部署，Jenkins变得非常臃肿。
3. 缺乏一个功能强大的环境管理系统，从更上一层解决用户的环境问题，而不是一味的扩展新环境。
4. 部分团队开始探索和落地容器技术，但对容器理念的理解还比较浅，无法完成大面积接入，SRE人力有限且对测试场景不熟悉，无暇支持超细粒度的测试环境建设需求。
----
md_node {'Header_2': '平台简介', 'filename': 'test-md.md', 'extension': '.md'}
md_node 平台简介

立足云原生，发挥容器技术优势，以简单、高效为目标，采用基础设施即代码的设计理念，通过用户自定义的环境模板实现环境的快速扩展，同时结合贝壳多样的测试场景，提供大量特性功能，如环境复制、配置复制、测试任务智能调度等，全方位为研发测试提效之路保驾护航。
----
md_node {'Header_2': '平台定位', 'filename': 'test-md.md', 'extension': '.md'}
md_node 平台定位

做为DevOps底层环境能力，提供统一的环境治理能力，结合容器化技术，提供科学的环境管理手段，在编译构建，配置管理，测试数据管理及环境扩展等方面提升开发测试效能。
----
--------------------------
html_node {'tag': 'h2', 'filename': 'test.html', 'extension': '.html'}
html_node 背景：
----
html_node {'tag': 'p', 'filename': 'test.html', 'extension': '.html'}
html_node 贝壳一直处于高速发展阶段，每天产出大量需求，需要快速迭代，但测试环境的搭建和维护成本非常巨大，严重阻碍了产品的迭代速度。主要问题：

1. 测试应用部署运维比较传统和多样化，不同团队开发自己的环境管理系统或没有自己的系统，下层对接SRE提供的虚拟机混布应用，还有一些业务线是自运维的，大量的工单和人工审批流程浪费了SRE、rd、qa很多时间，测试资源成本持续上涨。

2. 缺乏统一的构建部署标准、用户需要自己完成应用的构建和部署，Jenkins变得非常臃肿。

3. 缺乏一个功能强大的环境管理系统，从更上一层解决用户的环境问题，而不是一味的扩展新环境。

4. 部分团队开始探索和落地容器技术，但对容器理念的理解还比较浅，无法完成大面积接入，SRE人力有限且对测试场景不熟悉，无暇支持超细粒度的测试环境建设需求。
----
html_node {'tag': 'h2', 'filename': 'test.html', 'extension': '.html'}
html_node 平台简介
----
html_node {'tag': 'p', 'filename': 'test.html', 'extension': '.html'}
html_node 立足云原生，发挥容器技术优势，以简单、高效为目标，采用基础设施即代码的设计理念，通过用户自定义的环境模板实现环境的快速扩展，同时结合贝壳多样的测试场景，提供大量特性功能，如环境复制、配置复制、测试任务智能调度等，全方位为研发测试提效之路保驾护航。
----
html_node {'tag': 'h2', 'filename': 'test.html', 'extension': '.html'}
html_node 平台定位
----
html_node {'tag': 'p', 'filename': 'test.html', 'extension': '.html'}
html_node 做为DevOps底层环境能力，提供统一的环境治理能力，结合容器化技术，提供科学的环境管理手段，在编译构建，配置管理，测试数据管理及环境扩展等方面提升开发测试效能。
----
'''




def simple_file_node_parser2():
    reader = FlatReader()
    html_file = reader.load_data(Path("/Users/dongmenghui/Desktop/test/test.html"))
    print(html_file[0].metadata)
    print(html_file[0])
    print("----")

    parser = SimpleFileNodeParser()
    html_nodes = parser.get_nodes_from_documents(html_file)
    print("----")
    for node in html_nodes:
        print(node.metadata)
        print(node.text)
        print("----")

if __name__ == "__main__":
    simple_file_node_parser()
    # simple_file_node_parser2()