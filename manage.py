import os
import sys

if __name__ == "__main__":
    print("start manage.py")
    if sys.argv[-1] == "--ignore":
        sys.argv.remove(sys.argv[-1])
    elif sys.argv[1] in ["makemigrations", "migrate"]:
        if len(sys.argv) < 3:
            raise ValueError("进行数据库操作时，必须指定APP。")
        if not sys.argv[2].startswith("app_"):
            raise ValueError("APP不合法!")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "init.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError:
        # The above import may fail for some other reason. Ensure that the
        # issue is really that Django is missing to avoid masking other
        # exceptions on Python 2.
        try:
            import django
        except ImportError:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            )
        raise
    execute_from_command_line(sys.argv)
