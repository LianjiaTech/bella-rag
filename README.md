# 项目简介

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
