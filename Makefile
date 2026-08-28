pip_install:
	pip install -U -r requirements.txt -i https://pypi.douban.com/simple --trusted-host pypi.douban.com --default-timeout=100
start:
	chmod 755 bin/run.sh
	bin/run.sh

