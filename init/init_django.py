import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "init.settings")  # project_name 项目名称
django.setup()
print("@@@@@@@@@@@@@@@@@@@@@@@@@ ★★★INIT DJANGO SETTINGS★★★ @@@@@@@@@@@@@@@@@@@@@@@@@")
