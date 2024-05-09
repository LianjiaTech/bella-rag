# 🗂️ LlamaIndex 🦙

[![PyPI - Downloads](https://img.shields.io/pypi/dm/llama-index)](https://pypi.org/project/llama-index/)
[![GitHub contributors](https://img.shields.io/github/contributors/jerryjliu/llama_index)](https://github.com/jerryjliu/llama_index/graphs/contributors)
[![Discord](https://img.shields.io/discord/1059199217496772688)](https://discord.gg/dGcwcsnxhU)
[![Ask AI](https://img.shields.io/badge/Phorm-Ask_AI-%23F2777A.svg?&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNSIgaGVpZ2h0PSI0IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgogIDxwYXRoIGQ9Ik00LjQzIDEuODgyYTEuNDQgMS40NCAwIDAgMS0uMDk4LjQyNmMtLjA1LjEyMy0uMTE1LjIzLS4xOTIuMzIyLS4wNzUuMDktLjE2LjE2NS0uMjU1LjIyNmExLjM1MyAxLjM1MyAwIDAgMS0uNTk1LjIxMmMtLjA5OS4wMTItLjE5Mi4wMTQtLjI3OS4wMDZsLTEuNTkzLS4xNHYtLjQwNmgxLjY1OGMuMDkuMDAxLjE3LS4xNjkuMjQ2LS4xOTFhLjYwMy42MDMgMCAwIDAgLjItLjEwNi41MjkuNTI5IDAgMCAwIC4xMzgtLjE3LjY1NC42NTQgMCAwIDAgLjA2NS0uMjRsLjAyOC0uMzJhLjkzLjkzIDAgMCAwLS4wMzYtLjI0OS41NjcuNTY3IDAgMCAwLS4xMDMtLjIuNTAyLjUwMiAwIDAgMC0uMTY4LS4xMzguNjA4LjYwOCAwIDAgMC0uMjQtLjA2N0wyLjQzNy43MjkgMS42MjUuNjcxYS4zMjIuMzIyIDAgMCAwLS4yMzIuMDU4LjM3NS4zNzUgMCAwIDAtLjExNi4yMzJsLS4xMTYgMS40NS0uMDU4LjY5Ny0uMDU4Ljc1NEwuNzA1IDRsLS4zNTctLjA3OUwuNjAyLjkwNkMuNjE3LjcyNi42NjMuNTc0LjczOS40NTRhLjk1OC45NTggMCAwIDEgLjI3NC0uMjg1Ljk3MS45NzEgMCAwIDEgLjMzNy0uMTRjLjExOS0uMDI2LjIyNy0uMDM0LjMyNS0uMDI2TDMuMjMyLjE2Yy4xNTkuMDE0LjMzNi4wMy40NTkuMDgyYTEuMTczIDEuMTczIDAgMCAxIC41NDUuNDQ3Yy4wNi4wOTQuMTA5LjE5Mi4xNDQuMjkzYTEuMzkyIDEuMzkyIDAgMCAxIC4wNzguNThsLS4wMjkuMzJaIiBmaWxsPSIjRjI3NzdBIi8+CiAgPHBhdGggZD0iTTQuMDgyIDIuMDA3YTEuNDU1IDEuNDU1IDAgMCAxLS4wOTguNDI3Yy0uMDUuMTI0LS4xMTQuMjMyLS4xOTIuMzI0YTEuMTMgMS4xMyAwIDAgMS0uMjU0LjIyNyAxLjM1MyAxLjM1MyAwIDAgMS0uNTk1LjIxNGMtLjEuMDEyLS4xOTMuMDE0LS4yOC4wMDZsLTEuNTYtLjEwOC4wMzQtLjQwNi4wMy0uMzQ4IDEuNTU5LjE1NGMuMDkgMCAuMTczLS4wMS4yNDgtLjAzM2EuNjAzLjYwMyAwIDAgMCAuMi0uMTA2LjUzMi41MzIgMCAwIDAgLjEzOS0uMTcyLjY2LjY2IDAgMCAwIC4wNjQtLjI0MWwuMDI5LS4zMjFhLjk0Ljk0IDAgMCAwLS4wMzYtLjI1LjU3LjU3IDAgMCAwLS4xMDMtLjIwMi41MDIuNTAyIDAgMCAwLS4xNjgtLjEzOC42MDUuNjA1IDAgMCAwLS4yNC0uMDY3TDEuMjczLjgyN2MtLjA5NC0uMDA4LS4xNjguMDEtLjIyMS4wNTUtLjA1My4wNDUtLjA4NC4xMTQtLjA5Mi4yMDZMLjcwNSA0IDAgMy45MzhsLjI1NS0yLjkxMUExLjAxIDEuMDEgMCAwIDEgLjM5My41NzIuOTYyLjk2MiAwIDAgMSAuNjY2LjI4NmEuOTcuOTcgMCAwIDEgLjMzOC0uMTRDMS4xMjIuMTIgMS4yMy4xMSAxLjMyOC4xMTlsMS41OTMuMTRjLjE2LjAxNC4zLjA0Ny40MjMuMWExLjE3IDEuMTcgMCAwIDEgLjU0NS40NDhjLjA2MS4wOTUuMTA5LjE5My4xNDQuMjk1YTEuNDA2IDEuNDA2IDAgMCAxIC4wNzcuNTgzbC0uMDI4LjMyMloiIGZpbGw9IndoaXRlIi8+CiAgPHBhdGggZD0iTTQuMDgyIDIuMDA3YTEuNDU1IDEuNDU1IDAgMCAxLS4wOTguNDI3Yy0uMDUuMTI0LS4xMTQuMjMyLS4xOTIuMzI0YTEuMTMgMS4xMyAwIDAgMS0uMjU0LjIyNyAxLjM1MyAxLjM1MyAwIDAgMS0uNTk1LjIxNGMtLjEuMDEyLS4xOTMuMDE0LS4yOC4wMDZsLTEuNTYtLjEwOC4wMzQtLjQwNi4wMy0uMzQ4IDEuNTU5LjE1NGMuMDkgMCAuMTczLS4wMS4yNDgtLjAzM2EuNjAzLjYwMyAwIDAgMCAuMi0uMTA2LjUzMi41MzIgMCAwIDAgLjEzOS0uMTcyLjY2LjY2IDAgMCAwIC4wNjQtLjI0MWwuMDI5LS4zMjFhLjk0Ljk0IDAgMCAwLS4wMzYtLjI1LjU3LjU3IDAgMCAwLS4xMDMtLjIwMi41MDIuNTAyIDAgMCAwLS4xNjgtLjEzOC42MDUuNjA1IDAgMCAwLS4yNC0uMDY3TDEuMjczLjgyN2MtLjA5NC0uMDA4LS4xNjguMDEtLjIyMS4wNTUtLjA1My4wNDUtLjA4NC4xMTQtLjA5Mi4yMDZMLjcwNSA0IDAgMy45MzhsLjI1NS0yLjkxMUExLjAxIDEuMDEgMCAwIDEgLjM5My41NzIuOTYyLjk2MiAwIDAgMSAuNjY2LjI4NmEuOTcuOTcgMCAwIDEgLjMzOC0uMTRDMS4xMjIuMTIgMS4yMy4xMSAxLjMyOC4xMTlsMS41OTMuMTRjLjE2LjAxNC4zLjA0Ny40MjMuMWExLjE3IDEuMTcgMCAwIDEgLjU0NS40NDhjLjA2MS4wOTUuMTA5LjE5My4xNDQuMjk1YTEuNDA2IDEuNDA2IDAgMCAxIC4wNzcuNTgzbC0uMDI4LjMyMloiIGZpbGw9IndoaXRlIi8+Cjwvc3ZnPgo=)](https://www.phorm.ai/query?projectId=c5863b56-6703-4a5d-87b6-7e6031bf16b6)

LlamaIndex (GPT Index) is a data framework for your LLM application. Building with LlamaIndex typically involves working with LlamaIndex core and a chosen set of integrations (or plugins). There are two ways to start building with LlamaIndex in
Python:

# python包管理
## 新建
新建子包，选择创建readers或者index下的子包，子包名称为demo_package，里面包含一个demo_package文件和一个__init__.py文件
并会在tests目录下对应的readers或者index下，新建一个test_demo_package.py文件
```sh
python bin/packageManage.py create index demo_package
python bin/packageManage.py create readers demo_package

2. **Customized**: `llama-index-core` (https://pypi.org/project/llama-index-core/). Install core LlamaIndex and add your chosen LlamaIndex integration packages ([temporary registry](https://pretty-sodium-5e0.notion.site/ce81b247649a44e4b6b35dfb24af28a6?v=53b3c2ced7bb4c9996b81b83c9f01139))
   that are required for your application. There are over 300 LlamaIndex integration
   packages that work seamlessly with core, allowing you to build with your preferred
   LLM, embedding, and vector store providers.

The LlamaIndex Python library is namespaced such that import statements which
include `core` imply that the core package is being used. In contrast, those
statements without `core` imply that an integration package is being used.

```python
# typical pattern
from llama_index.core.xxx import ClassABC  # core submodule xxx
from llama_index.xxx.yyy import (
    SubclassABC,
)  # integration yyy for submodule xxx

# concrete example
from llama_index.core.llms import LLM
from llama_index.llms.openai import OpenAI
```

## 删除
删除子模块，选择删除readers或者index下的子包，子包名称为demo_package，会将子包及其测试文件进行删除
```sh
python bin/packageManage.py delete index demo_package
python bin/packageManage.py delete readers demo_package

LlamaIndex.TS (Typescript/Javascript): https://github.com/run-llama/LlamaIndexTS.

Documentation: https://docs.llamaindex.ai/en/stable/.

Twitter: https://twitter.com/llama_index.

Discord: https://discord.gg/dGcwcsnxhU.

### Ecosystem

- LlamaHub (community library of data loaders): https://llamahub.ai.
- LlamaLab (cutting-edge AGI projects using LlamaIndex): https://github.com/run-llama/llama-lab.

## 🚀 Overview

**NOTE**: This README is not updated as frequently as the documentation. Please check out the documentation above for the latest updates!

### Context

- LLMs are a phenomenal piece of technology for knowledge generation and reasoning. They are pre-trained on large amounts of publicly available data.
- How do we best augment LLMs with our own private data?

We need a comprehensive toolkit to help perform this data augmentation for LLMs.

### Proposed Solution

That's where **LlamaIndex** comes in. LlamaIndex is a "data framework" to help you build LLM apps. It provides the following tools:

- Offers **data connectors** to ingest your existing data sources and data formats (APIs, PDFs, docs, SQL, etc.).
- Provides ways to **structure your data** (indices, graphs) so that this data can be easily used with LLMs.
- Provides an **advanced retrieval/query interface over your data**: Feed in any LLM input prompt, get back retrieved context and knowledge-augmented output.
- Allows easy integrations with your outer application framework (e.g. with LangChain, Flask, Docker, ChatGPT, anything else).

LlamaIndex provides tools for both beginner users and advanced users. Our high-level API allows beginner users to use LlamaIndex to ingest and query their data in
5 lines of code. Our lower-level APIs allow advanced users to customize and extend any module (data connectors, indices, retrievers, query engines, reranking modules),
to fit their needs.

## 💡 Contributing

Interested in contributing? Contributions to LlamaIndex core as well as contributing
integrations that build on the core are both accepted and highly encouraged! See our [Contribution Guide](CONTRIBUTING.md) for more details.

## 📄 Documentation

Full documentation can be found here: https://docs.llamaindex.ai/en/latest/.

Please check it out for the most up-to-date tutorials, how-to guides, references, and other resources!

## 💻 Example Usage

```sh
# custom selection of integrations to work with core
pip install llama-index-core
pip install llama-index-llms-openai
pip install llama-index-llms-replicate
pip install llama-index-embeddings-huggingface
```

Examples are in the `docs/examples` folder. Indices are in the `indices` folder (see list of indices below).

# http服务

> 一个django的基础使用模板，集成了日志和基本的django服务 <br>
> 示例已服务地址  http://127.0.0.1:8008  为例

# 如何使用此框架

## 设置release的目录
>打开init.config.py, 设置 RELEASE_DIR，正确设置后，启动时会根据文件目录BASE_DIR来确定是否是线上环境。
>修改run.sh中的 release_appid 为指定线上的appid（即部署目录）

## 配置mysql和redis
>进入conf目录配置对应的配置文件，具体配置说明详见配置文件注释
>配置文件说明如下：
config_release.ini :    线上执行的配置文件
非线上环境，并且不指定环境变量 CONFIG_FILE 的时候，默认如下规则：
config_test.ini :       在linux系统中加载此配置文件
config_local_mac.ini :  Mac系统默认加载此配置文件
config_local.ini :      windows系统默认加载此配置文件
非线上环境，如果指定了环境变量 CONFIG_FILE，那么就加载CONFIG_FILE指定的配置文件。

## 使用app.py文件创建和删除APP
### 命令

```
# 创建app
python3 app.py create app_test
```
> 执行成功后，启动django，浏览器输入ip:port/test，成功输出 即可。<br>
> PS：test的意思是app_test去掉app_后的小写。

### 结果
>执行后将生成目录app_test  template/app_test两个目录，分别是app的目录和模板的目录。<br>
>urls.py 和 settings.py 中也加入app对应的配置。

### 如果要删除APP
```
# 删除app
python3 app.py delete app_test
```
>PS：<br>
>*若要删除一个已经创建过db的APP，还要手动把相关的数据库信息删除掉。<br>
>*命名要符合规范app开头 <br>
>*app创建之前，先merge下master到自己的分支，app创建后，最好第一时间能够merge到master，但是可以不开放入口给用户，避免多人都创建app导致代码冲突。

## 重启Django查看效果
>访问  http://127.0.0.1:8008/test <br>
>输出app_test index.html templates.的话，相关的模板和app已创建成功。

## 关于db相关的操作
>由于公司的建表限制，使用系统自带的model可能会引起db与model不同步的问题，所以不推荐使用django自带的model操作数据库。<br>
>推荐使用系统内置的 common.tool.orm.DORM，语法类似，但是可解决model与dbmodel不同步的时候的会报错的问题。

## run.sh使用说明
> sh bin/run.sh run : 环境创建、安装包依赖、启动redis_logging、启动django服务
> sh bin/run.sh stop : 停止服务
> sh bin/run.sh start : 仅后台启动django服务
> sh bin/run.sh install : 环境创建、安装包依赖
