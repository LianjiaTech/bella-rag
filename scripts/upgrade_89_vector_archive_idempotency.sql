-- Issue #89: 文件向量归档状态表升级脚本
-- 本脚本不支持归档任务运行中的滚动迁移：
-- 1. 暂停定时归档以及手动归档/恢复入口；
-- 2. 确认没有正在执行的归档/恢复任务；
-- 3. 执行并验证本脚本；
-- 4. 部署新版本所有实例，保持归档入口关闭；
-- 5. POST /api/vector/archive/backfill 启动回填；
-- 6. GET /api/vector/archive/backfill 观察 completed 并校验数据；
-- 7. 校验通过后恢复归档入口，再执行 dry-run 验证候选范围。

CREATE TABLE IF NOT EXISTS `file_vector_index_state` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `file_id` varchar(128) NOT NULL COMMENT '文件id',
  `status` smallint(6) NOT NULL DEFAULT '1' COMMENT '0=索引中, 1=可用, 2=归档中, 3=已归档',
  `last_indexed_at` datetime(6) NOT NULL DEFAULT '1970-01-01 00:00:00.000000' COMMENT '最近一次主chunk索引完成时间',
  `archive_started_at` datetime(6) NOT NULL DEFAULT '1970-01-01 00:00:00.000000' COMMENT '最近归档开始时间',
  `archived_at` datetime(6) NOT NULL DEFAULT '1970-01-01 00:00:00.000000' COMMENT '归档完成时间',
  `create_time` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  `update_time` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_vector_state_file_id` (`file_id`),
  KEY `idx_vector_state_scan` (`status`, `last_indexed_at`, `file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='文件向量索引状态';

-- 发布人员必须确认索引存在后，才能恢复归档入口。
SELECT `index_name`, `non_unique`, `seq_in_index`, `column_name`
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'file_vector_index_state'
  AND index_name IN ('uk_vector_state_file_id', 'idx_vector_state_scan')
ORDER BY `seq_in_index`;
