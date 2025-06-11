# 🗂️ LlamaIndex 🦙

[![PyPI - Downloads](https://img.shields.io/pypi/dm/llama-index)](https://pypi.org/project/llama-index/)
[![GitHub contributors](https://img.shields.io/github/contributors/jerryjliu/llama_index)](https://github.com/jerryjliu/llama_index/graphs/contributors)
[![Discord](https://img.shields.io/discord/1059199217496772688)](https://discord.gg/dGcwcsnxhU)
[![Ask AI](https://img.shields.io/badge/Phorm-Ask_AI-%23F2777A.svg?&logo=data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNSIgaGVpZ2h0PSI0IiBmaWxsPSJub25lIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgogIDxwYXRoIGQ9Ik00LjQzIDEuODgyYTEuNDQgMS40NCAwIDAgMS0uMDk4LjQyNmMtLjA1LjEyMy0uMTE1LjIzLS4xOTIuMzIyLS4wNzUuMDktLjE2LjE2NS0uMjU1LjIyNmExLjM1MyAxLjM1MyAwIDAgMS0uNTk1LjIxMmMtLjA5OS4wMTItLjE5Mi4wMTQtLjI3OS4wMDZsLTEuNTkzLS4xNHYtLjQwNmgxLjY1OGMuMDkuMDAxLjE3LS4xNjkuMjQ2LS4xOTFhLjYwMy42MDMgMCAwIDAgLjItLjEwNi41MjkuNTI5IDAgMCAwIC4xMzgtLjE3LjY1NC42NTQgMCAwIDAgLjA2NS0uMjRsLjAyOC0uMzJhLjkzLjkzIDAgMCAwLS4wMzYtLjI0OS41NjcuNTY3IDAgMCAwLS4xMDMtLjIuNTAyLjUwMiAwIDAgMC0uMTY4LS4xMzguNjA4LjYwOCAwIDAgMC0uMjQtLjA2N0wyLjQzNy43MjkgMS42MjUuNjcxYS4zMjIuMzIyIDAgMCAwLS4yMzIuMDU4LjM3NS4zNzUgMCAwIDAtLjExNi4yMzJsLS4xMTYgMS40NS0uMDU4LjY5Ny0uMDU4Ljc1NEwuNzA1IDRsLS4zNTctLjA3OUwuNjAyLjkwNkMuNjE3LjcyNi42NjMuNTc0LjczOS40NTRhLjk1OC45NTggMCAwIDEgLjI3NC0uMjg1Ljk3MS45NzEgMCAwIDEgLjMzNy0uMTRjLjExOS0uMDI2LjIyNy0uMDM0LjMyNS0uMDI2TDMuMjMyLjE2Yy4xNTkuMDE0LjMzNi4wMy40NTkuMDgyYTEuMTczIDEuMTczIDAgMCAxIC41NDUuNDQ3Yy4wNi4wOTQuMTA5LjE5Mi4xNDQuMjkzYTEuMzkyIDEuMzkyIDAgMCAxIC4wNzguNThsLS4wMjkuMzJaIiBmaWxsPSIjRjI3NzdBIi8+CiAgPHBhdGggZD0iTTQuMDgyIDIuMDA3YTEuNDU1IDEuNDU1IDAgMCAxLS4wOTguNDI3Yy0uMDUuMTI0LS4xMTQuMjMyLS4xOTIuMzI0YTEuMTMgMS4xMyAwIDAgMS0uMjU0LjIyNyAxLjM1MyAxLjM1MyAwIDAgMS0uNTk1LjIxNGMtLjEuMDEyLS4xOTMuMDE0LS4yOC4wMDZsLTEuNTYtLjEwOC4wMzQtLjQwNi4wMy0uMzQ4IDEuNTU5LjE1NGMuMDkgMCAuMTczLS4wMS4yNDgtLjAzM2EuNjAzLjYwMyAwIDAgMCAuMi0uMTA2LjUzMi41MzIgMCAwIDAgLjEzOS0uMTcyLjY2LjY2IDAgMCAwIC4wNjQtLjI0MWwuMDI5LS4zMjFhLjk0Ljk0IDAgMCAwLS4wMzYtLjI1LjU3LjU3IDAgMCAwLS4xMDMtLjIwMi41MDIuNTAyIDAgMCAwLS4xNjgtLjEzOC42MDUuNjA1IDAgMCAwLS4yNC0uMDY3TDEuMjczLjgyN2MtLjA5NC0uMDA4LS4xNjguMDEtLjIyMS4wNTUtLjA1My4wNDUtLjA4NC4xMTQtLjA5Mi4yMDZMLjcwNSA0IDAgMy45MzhsLjI1NS0yLjkxMUExLjAxIDEuMDEgMCAwIDEgLjM5My41NzIuOTYyLjk2MiAwIDAgMSAuNjY2LjI4NmEuOTcuOTcgMCAwIDEgLjMzOC0uMTRDMS4xMjIuMTIgMS4yMy4xMSAxLjMyOC4xMTlsMS41OTMuMTRjLjE2LjAxNC4zLjA0Ny40MjMuMWExLjE3IDEuMTcgMCAwIDEgLjU0NS40NDhjLjA2MS4wOTUuMTA5LjE5My4xNDQuMjk1YTEuNDA2IDEuNDA2IDAgMCAxIC4wNzcuNTgzbC0uMDI4LjMyMloiIGZpbGw9IndoaXRlIi8+CiAgPHBhdGggZD0iTTQuMDgyIDIuMDA3YTEuNDU1IDEuNDU1IDAgMCAxLS4wOTguNDI3Yy0uMDUuMTI0LS4xMTQuMjMyLS4xOTIuMzI0YTEuMTMgMS4xMyAwIDAgMS0uMjU0LjIyNyAxLjM1MyAxLjM1MyAwIDAgMS0uNTk1LjIxNGMtLjEuMDEyLS4xOTMuMDE0LS4yOC4wMDZsLTEuNTYtLjEwOC4wMzQtLjQwNi4wMy0uMzQ4IDEuNTU5LjE1NGMuMDkgMCAuMTczLS4wMS4yNDgtLjAzM2EuNjAzLjYwMyAwIDAgMCAuMi0uMTA2LjUzMi41MzIgMCAwIDAgLjEzOS0uMTcyLjY2LjY2IDAgMCAwIC4wNjQtLjI0MWwuMDI5LS4zMjFhLjk0Ljk0IDAgMCAwLS4wMzYtLjI1LjU3LjU3IDAgMCAwLS4xMDMtLjIwMi41MDIuNTAyIDAgMCAwLS4xNjgtLjEzOC42MDUuNjA1IDAgMCAwLS4yNC0uMDY3TDEuMjczLjgyN2MtLjA5NC0uMDA4LS4xNjguMDEtLjIyMS4wNTUtLjA1My4wNDUtLjA4NC4xMTQtLjA5Mi4yMDZMLjcwNSA0IDAgMy45MzhsLjI1NS0yLjkxMUExLjAxIDEuMDEgMCAwIDEgLjM5My41NzIuOTYyLjk2MiAwIDAgMSAuNjY2LjI4NmEuOTcuOTcgMCAwIDEgLjMzOC0uMTRDMS4xMjIuMTIgMS4yMy4xMSAxLjMyOC4xMTlsMS41OTMuMTRjLjE2LjAxNC4zLjA0Ny40MjMuMWExLjE3IDEuMTcgMCAwIDEgLjU0NS40NDhjLjA2MS4wOTUuMTA5LjE5My4xNDQuMjk1YTEuNDA2IDEuNDA2IDAgMCAxIC4wNzcuNTgzbC0uMDI4LjMyMloiIGZpbGw9IndoaXRlIi8+Cjwvc3ZnPgo=)](https://www.phorm.ai/query?projectId=c5863b56-6703-4a5d-87b6-7e6031bf16b6)

# 依赖安装
编辑$HOME/.pip/pip.conf
```angular2html
extra-index-url=http://artifactory.intra.ke.com/artifactory/api/pypi/pypi-virtual/simple

trusted-host=artifactory.intra.ke.com
```
执行pip install -r requirements.txt

# 环境要求
python>=3.8
dockerfile-ke中的依赖

# python包管理
> readers:数据连接器,从各种来源和格式摄取数据，并将其转换为由文本和基本元数据组成的简化文档表示形式。<br>
> parser:
> 将文档处理为节点，节点是更细粒度的数据实体，表示源文档的“块”，可以是文本块、图像或其他类型的数据。它们还携带元数据和与其他节点的关系信息，这有助于构建更加结构化和关系型的索引。<br>
> indexer:结构化索引,在被摄取的数据上构建结构化索引，这些数据表示为文档或节点。这种索引有助于对数据进行有效的查询。<br>



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
 
## mac系统启动mysql连接问题

> mac系统部分内置了mysql 非8.x的版本，在django启动的时候会报如下错：
>
> django.db.utils.OperationalError: (2059, "Authentication plugin 'mysql_native_password' cannot be loaded: dlopen(/opt/homebrew/Cellar/mysql/9.1.0_1/lib/plugin/mysql_native_password.so, 0x0002): tried: '/opt/homebrew/Cellar/mysql/9.1.0_1/lib/plugin/mysql_native_password.so' (no such file), 

> 解决方式参考：https://github.com/Homebrew/homebrew-core/issues/180498
> 需将mysql版本切换至8.x

```
brew install mysql-client@8.4
brew unlink mysql
brew link mysql-client@8.4
```