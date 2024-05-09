import os
import shutil
import sys

if __name__ == "__main__":
    if len(sys.argv) == 3:
        opration = sys.argv[1].lower()
        if opration not in ["create", "delete"]:
            raise Exception("操作参数不合法，应该是create/delete。")
        app_name = sys.argv[2].lower()
        if not app_name.startswith("app_"):
            raise Exception("不符合命名规范，请使用app_开头。")
    else:
        raise Exception("参数错误，参数1是create/delete，参数2是app名称(例如app_demo)。")

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    print("当前目录：%s" % BASE_DIR)

    appFolder = "%s/%s" % (BASE_DIR, app_name)
    tempFolder = "%s/template/%s" % (BASE_DIR, app_name)
    urlFile = "%s/init/urls.py" % (BASE_DIR)
    # settingsFile = "%s/init/settings.py" % (BASE_DIR)

    if opration == "create":
        if os.path.exists(appFolder):
            raise Exception("已经存在app %s" % app_name)

        if os.path.exists(tempFolder):
            raise Exception("已经存在模板目录 %s" % tempFolder)

        # 创建app根目录
        os.mkdir(appFolder)
        # 创建app根目录的__init__.py
        with open("%s/__init__.py" % (appFolder), 'w', encoding="utf8") as f:
            pass

        # 创建services根目录
        servicesFolder = "%s/services" % (appFolder)
        os.mkdir(servicesFolder)
        # 创建migrations根目录的__init__.py
        with open("%s/__init__.py" % (servicesFolder), 'w', encoding="utf8") as f:
            pass

        # 创建views根目录
        viewsFolder = "%s/views" % (appFolder)
        os.mkdir(viewsFolder)
        # 创建migrations根目录的__init__.py
        with open("%s/__init__.py" % (viewsFolder), 'w', encoding="utf8") as f:
            pass
        with open("%s/main.py" % (viewsFolder), 'w', encoding="utf8") as f:
            f.write("""from django.shortcuts import HttpResponse
from django.shortcuts import render


# Create your views here.
def index(request):
    return render(request, "%s/index.html", context={})
""" % app_name)

        with open("%s/urls.py" % (appFolder), 'w', encoding="utf8") as f:
            f.write("""from django.conf.urls import url
from %s.views import main

urlpatterns = [
    url(r'^$', main.index, name="index"),
]
""" % app_name)

        # 创建app根目录
        os.mkdir(tempFolder)
        # 创建app根目录的__init__.py
        with open("%s/index.html" % (tempFolder), 'w', encoding="utf8") as f:
            f.write("""%s index.html templates.""" % app_name)

        with open(urlFile, "r+", encoding="utf8") as f:
            read_data = f.read()
            f.seek(0)
            f.truncate()  # 清空文件
            f.write(read_data.replace('\n]', """\n    url(r'^%s/', include(("%s.urls", '%s'), namespace='%s')),\n]""" % (
                app_name[4:].lower(), app_name, app_name, app_name)))

        # with open(settingsFile, "r+", encoding="utf8") as f:
        #     read_data = f.read()
        #     tobeReplaced = get_sub_string(read_data, "INSTALLED_APPS = [", "]")
        #     replaceToStr = "%s    '%s',\n" % (tobeReplaced, app_name)
        #     f.seek(0)
        #     f.truncate()  # 清空文件
        #     f.write(read_data.replace(tobeReplaced, replaceToStr))

    elif opration == "delete":
        confirm_char = input("确认删除app[%s](y/N)：" % app_name)
        if confirm_char != "y":
            print("app[%s]未删除" % app_name)
            sys.exit(0)
        shutil.rmtree(appFolder)
        shutil.rmtree(tempFolder)

        with open(urlFile, "r+", encoding="utf8") as f:
            read_data = f.read()
            f.seek(0)
            f.truncate()  # 清空文件
            f.write(read_data.replace("""\n    url(r'^%s/', include(("%s.urls", '%s'), namespace='%s')),""" % (
                app_name[4:].lower(), app_name, app_name, app_name), ""))
