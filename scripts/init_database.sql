-- ke-RAG 数据库初始化脚本
-- 执行前请确保已经安装了MySQL >= 5.7

-- 创建数据库
CREATE DATABASE IF NOT EXISTS bella_rag CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE bella_rag;

-- 创建向量化索引信息表
CREATE TABLE IF NOT EXISTS `chunk_content_attached` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `source_id` varchar(128) NOT NULL COMMENT '来源的id，文件为fileId',
  `chunk_id` varchar(128) DEFAULT '' COMMENT 'chunk_id node_id',
  `content_title` text COMMENT '标题',
  `content_data` longtext COMMENT '内容',
  `token` int(11) DEFAULT '-911' COMMENT '节点及子节点token总量',
  `chunk_pos` int(11) NOT NULL COMMENT '切片的位置',
  `chunk_status` int(11) DEFAULT '1' COMMENT '切片状态',
  `order_num` varchar(128) DEFAULT '' COMMENT '切片层级信息',
  `context_id` varchar(128) DEFAULT '' COMMENT '切片管理上下文id',
  `create_time` datetime(6) DEFAULT NULL COMMENT '创建时间',
  `update_time` datetime(6) DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_chunk_id` (`chunk_id`),
  KEY `idx_chunk_status` (`chunk_status`),
  KEY `idx_context_id` (`context_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='向量化索引信息保存';

-- 创建QA问答索引表
CREATE TABLE IF NOT EXISTS `question_answer_index_attached` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `source_id` varchar(128) NOT NULL COMMENT '来源的id，文件为fileId',
  `group_id` varchar(128) NOT NULL COMMENT '问题组的概念',
  `question` text NOT NULL COMMENT '问题',
  `answer` text NOT NULL COMMENT '答案',
  `business_metadata` text COMMENT '业务元数据字段',
  `del_status` int(11) DEFAULT '0' COMMENT '删除状态',
  `ctime` datetime(6) DEFAULT NULL COMMENT '创建时间',
  `mtime` datetime(6) DEFAULT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_source_id` (`source_id`),
  KEY `idx_group_id` (`group_id`),
  KEY `idx_del_status` (`del_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='QA类型问题向量化索引信息';

-- 创建知识文件元数据表
CREATE TABLE IF NOT EXISTS `knowledge_file_meta` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `file_id` varchar(64) DEFAULT '' COMMENT '文件ID',
  `summary_question` text COMMENT '文件总结',
  `tag` text COMMENT '业务标签',
  PRIMARY KEY (`id`),
  KEY `idx_file_id` (`file_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识文件维度的元数据';

-- 创建系统配置表（可选）
CREATE TABLE IF NOT EXISTS `system_config` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `config_key` varchar(128) NOT NULL COMMENT '配置键',
  `config_value` text COMMENT '配置值',
  `description` varchar(255) DEFAULT '' COMMENT '配置描述',
  `create_time` datetime(6) DEFAULT CURRENT_TIMESTAMP(6) COMMENT '创建时间',
  `update_time` datetime(6) DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6) COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- 插入默认配置
INSERT INTO `system_config` (`config_key`, `config_value`, `description`) VALUES
('system.version', '1.0.0', '系统版本'),
('system.initialized', '1', '系统初始化状态'),
('rag.default_chunk_size', '1000', '默认分块大小'),
('rag.default_overlap', '200', '默认重叠大小')
ON DUPLICATE KEY UPDATE 
  `config_value` = VALUES(`config_value`),
  `update_time` = CURRENT_TIMESTAMP(6);

-- 输出初始化完成信息
SELECT 'Database bella_rag initialized successfully!' as status;
SELECT 'Tables created:' as info;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'bella_rag';