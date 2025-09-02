import json
import logging
import os
import threading
import time
from telnetlib import Telnet
from typing import Any, Dict, Optional

import requests

from common.helper.exception import BusinessError


class ApolloClient(object):
    """
    this module is modified from the project: https://github.com/filamoon/pyapollo
    and had commit the merge request to the original repo
    thanks for the contributors
    since the contributors had stopped to commit code to the original repo, please submit issue or commit to https://github.com/BruceWW/pyapollo
    """

    def __new__(cls, *args, **kwargs):
        """
        singleton model
        """
        tmp = {_: kwargs[_] for _ in sorted(kwargs)}
        key = f"{args},{tmp}"
        if hasattr(cls, "_instance"):
            if key not in cls._instance:
                cls._instance[key] = super().__new__(cls)
        else:
            cls._instance = {key: super().__new__(cls)}
        return cls._instance[key]

    def __init__(
            self,
            app_id: str,
            cluster: str = "default",
            config_server_url: str = "http://localhost:8090",
            portal_server_url: str = "http://localhost:8090",
            env: str = "DEV",
            # namespaces: List[str] = None,
            ip: str = None,
            timeout: int = 60,
            cycle_time: int = 300,
            cache_file_path: str = None,
            authorization: str = None
            # request_model: Optional[Any] = None,
    ):
        """
        init method
        :param app_id: application id
        :param cluster: cluster name, default value is 'default'
        :param config_server_url: with the format 'http://localhost:80080'
        :param env: environment, default value is 'DEV'
        :param timeout: http request timeout seconds, default value is 60 seconds
        :param ip: the deploy ip for grey release, default value is the local ip
        :param cycle_time: the cycle time to update configuration content from server
        :param cache_file_path: local cache file store path
        """
        self.config_server_url = config_server_url
        self.portal_server_url = portal_server_url
        self.app_id = app_id
        self.cluster = cluster
        self.timeout = timeout
        self.stopped = False
        self._env = env
        self.ip = self.init_ip(ip)
        remote = self.config_server_url.split(":")
        self.host = f"{remote[0]}:{remote[1]}"
        if len(remote) == 1:
            self.port = 8090
        else:
            self.port = int(remote[2])
        self._authorization = authorization

        self._request_model = None
        self._cache: Dict = {}
        self._notification_map: Dict = {}
        self._cycle_time = cycle_time
        self._hash: Dict = {}
        if cache_file_path is None:
            self._cache_file_path = os.path.join(
                os.path.abspath(os.path.dirname(__file__)), ""
            )
        else:
            self._cache_file_path = cache_file_path
        self._path_checker()

        self._update_thread = None
        # for http request extension
        self.start()

    def _get_clusters(self) -> dict:
        """
        get clusters by app id
        :return :
        """
        url = f"{self.portal_server_url}/openapi/v1/envs/{self._env}/apps/{self.app_id}/clusters"

        r = self._http_get(url)
        if r.status_code == 200:
            return r.json()
        else:
            return {}

    def _get_namespaces(self) -> dict:
        """
        get namespaces by app id and cluster
        :return :
        """
        url = f"{self.portal_server_url}/openapi/v1/envs/{self._env}/apps/{self.app_id}/clusters/{self.cluster}/namespaces"

        r = self._http_get(url)
        if r.status_code == 200:
            namespaces = r.json()
            return {_.get("namespaceName"): _.get("id") for _ in namespaces}
        else:
            return {"application": -1}

    @staticmethod
    def init_ip(ip: Optional[str]) -> str:
        """
        for grey release
        :param ip:
        :return:
        """
        if ip is None:
            try:
                import socket

                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 53))
                ip = s.getsockname()[0]
                s.close()
            except BaseException:
                return "127.0.0.1"
        return ip

    def get_value(self, key: str, default_val: str = None, namespace: str = "application") -> Any:
        try:
            if not (self._update_thread and self._update_thread.is_alive()):
                self.start()

            # check the namespace is existed or not
            if namespace in self._cache:
                return self._cache[namespace].get(key, default_val)
            return default_val
        except BusinessError:
            return default_val

    def start(self) -> None:
        """
        Start the long polling loop.
        :return:
        """
        if len(self._cache) == 0:
            self._long_poll()
        self._update_thread = threading.Thread(target=self._listener)
        self._update_thread.daemon = True
        self._update_thread.start()

    def _http_get(self, url: str, params: Dict = None) -> requests.Response:
        """
        handle http request with get method
        :param url:
        :return:
        """
        if self._request_model is None:
            return self._request_get(url, params=params)
        else:
            return self._request_model(url)

    def _request_get(self, url: str, params: Dict = None) -> requests.Response:
        """

        :param url:
        :param params:
        :return:
        """
        try:
            if self._authorization:
                return requests.get(
                    url=url,
                    params=params,
                    timeout=self.timeout // 2,
                    headers={"Authorization": self._authorization},
                )
            else:
                return requests.get(url=url, params=params, timeout=self.timeout // 2)

        except requests.exceptions.ReadTimeout:
            # if read timeout, check the server is alive or not
            try:
                tn = Telnet(host=self.host, port=self.port, timeout=self.timeout // 2)
                tn.close()
                # if connect server succeed, raise the exception that namespace not found
                raise BusinessError("namespace not found")
            except ConnectionRefusedError:
                # if connection refused, raise server not response error
                raise BusinessError(f"server: {self.config_server_url} not response")

    def _path_checker(self) -> None:
        """
        create configuration cache file directory if not exits
        :return:
        """
        if not os.path.isdir(self._cache_file_path):
            os.mkdir(self._cache_file_path)

    def _update_local_cache(
            self, release_key: str, data: str, namespace: str = "application"
    ) -> None:
        """
        if local cache file exits, update the content
        if local cache file not exits, create a version
        :param release_key:
        :param data: new configuration content
        :param namespace::s
        :return:
        """
        # trans the config map to md5 string, and check it's been updated or not
        if self._hash.get(namespace) != release_key:
            # if it's updated, update the local cache file
            with open(
                    os.path.join(
                        self._cache_file_path,
                        "%s_configuration_%s.txt" % (self.app_id, namespace),
                    ),
                    "w",
            ) as f:
                new_string = json.dumps(data)
                f.write(new_string)
            self._hash[namespace] = release_key

    def _get_local_cache(self, namespace: str = "application") -> Dict:
        """
        get configuration from local cache file
        if local cache file not exits than return empty dict
        :param namespace:
        :return:
        """
        cache_file_path = os.path.join(
            self._cache_file_path, "%s_configuration_%s.txt" % (self.app_id, namespace)
        )
        if os.path.isfile(cache_file_path):
            with open(cache_file_path, "r") as f:
                result = json.loads(f.readline())
            return result
        return {}

    def _get_config_by_namespace(self, namespace: str = "application") -> None:
        """

        :param namespace:
        :return:
        """
        url = f"{self.host}:{self.port}/configs/{self.app_id}/{self.cluster}/{namespace}"

        try:
            r = self._http_get(url)
            if r.status_code == 200:
                data = r.json()
                self._cache[namespace] = data.get("configurations", {})
                self._update_local_cache(
                    data.get("releaseKey", str(time.time())),
                    data.get("configurations", {}),
                    namespace,
                )
            else:
                data = self._get_local_cache(namespace)
                self._cache[namespace] = data
        except BaseException as e:
            logging.getLogger(__name__).warning(str(e))
            data = self._get_local_cache(namespace)
            self._cache[namespace] = data

    def _long_poll(self) -> None:
        try:
            self._notification_map = self._get_namespaces()
            for namespace in self._notification_map.keys():
                self._get_config_by_namespace(namespace)
        except requests.exceptions.ReadTimeout as e:
            logging.getLogger(__name__).warning(str(e))
        except requests.exceptions.ConnectionError as e:
            logging.getLogger(__name__).warning(str(e))
            self._load_local_cache_file()

    def _load_local_cache_file(self) -> bool:
        """
        load all cached files from local path
        is only used while apollo server is unreachable
        :return:
        """
        for file_name in os.listdir(self._cache_file_path):
            file_path = os.path.join(self._cache_file_path, file_name)
            if os.path.isfile(file_path):
                file_simple_name, file_ext_name = os.path.splitext(file_name)
                if file_ext_name == ".swp":
                    continue
                namespace = file_simple_name.split("_")[-1]
                with open(file_path) as f:
                    self._cache[namespace] = json.loads(f.read())["configurations"]
        return True

    def _listener(self) -> None:
        """

        :return:
        """
        while True:
            self._long_poll()
            try:
                cycle_time = float(self._cycle_time)
            except ValueError:
                logging.getLogger(__name__).error(f"Invalid cycle time: {self._cycle_time}")
                break

            time.sleep(cycle_time)

apollo_client = None

def get_apollo_client():
    """获取Apollo客户端实例，如果配置不存在则返回None"""
    global apollo_client
    if apollo_client is None:
        try:
            from init.settings import APOLLO
            if APOLLO and all(APOLLO.get(key) for key in ['APP_ID', 'CONFIG_SERVER_URL']):
                apollo_client = ApolloClient(
                    app_id=APOLLO['APP_ID'],
                    portal_server_url=APOLLO.get('PORTAL_SERVER_URL', 'http://localhost:8090'),
                    config_server_url=APOLLO.get('CONFIG_SERVER_URL', 'http://localhost:8090'),
                    authorization=APOLLO.get('AUTHORIZATION', ''),
                    env=APOLLO.get('ENV', 'DEV'),
                    cycle_time=int(APOLLO.get('CYCLE_TIME', 300))
                )
            else:
                print("Apollo配置未启用或配置不完整，跳过Apollo客户端初始化")
        except (ImportError, KeyError, TypeError) as e:
            print(f"Apollo配置初始化失败，跳过Apollo客户端初始化: {e}")
    return apollo_client

def get_apollo_config(key: str, default_val: str = None, namespace: str = "application"):
    """获取Apollo配置值"""
    client = get_apollo_client()
    if client:
        return client.get_value(key, default_val, namespace)
    return default_val
