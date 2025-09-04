#!/bin/bash

# 以下为fast采集规则，勿删
FLUENT_LOGS_ENABLED=${FAST_ENABLED:=false}
if [ -n "${SERVICE_ID}" ] && [ -n "${SERVICE_GROUP}" ] && [ -n "${POD_NAME}" ] && [ -n "${POD_NAMESPACE}" ] && [ -n "${CONTAINER_NAME}" ] && [ "${FLUENT_LOGS_ENABLED}" == "true"  ];then
  echo "开启天眼日志采集..."
  export FLUENT_APPLOGS_DIR=/applogs/${SERVICE_ID}_${SERVICE_GROUP}_${POD_NAME}_${POD_NAMESPACE}_${CONTAINER_NAME}
  export FLUENT_ACCESSLOGS_DIR=/accesslogs/${SERVICE_ID}_${SERVICE_GROUP}_${POD_NAME}_${POD_NAMESPACE}_${CONTAINER_NAME}
  mkdir -p ${FLUENT_APPLOGS_DIR}
  mkdir -p ${FLUENT_ACCESSLOGS_DIR}
  mkdir -p /data0/www
  ln -s ${FLUENT_APPLOGS_DIR} /data0/www/applogs
  ln -s ${FLUENT_ACCESSLOGS_DIR} /data0/www/logs
fi
# 以上为fast采集规则，勿删

# 启动Django服务
echo "启动Django服务..."
if ! python manage.py runserver 0.0.0.0:8080 --noreload; then
  echo "Django服务启动失败，异常信息如下："
fi