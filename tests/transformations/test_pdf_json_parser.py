#!/usr/bin/env python3
"""
PDF JSON解析器单元测试
测试从JSON数据解析成StandardDomTree并转换为nodes的功能
"""

import json
from unittest.mock import patch, MagicMock

import pytest
from bella_openapi.entity.standard_domtree import StandardDomTree
from llama_index.core.schema import Document

from bella_rag.schema.nodes import TextNode, ImageNode, DocumentNodeRelationship
from bella_rag.transformations.parser.pdf_parser import PdfParser
from bella_rag.utils.schema_util import dom2nodes


class TestPdfJsonParser:
    """PDF JSON解析器测试类"""

    @pytest.fixture
    def sample_json_data(self):
        """测试用的JSON数据"""
        return {
            "source_file": {
                "id": "file-2507311649080024173210-1989906366",
                "name": "【门店上班 就近分配 租房管家_成都_5-8K】谢贤涛_一年以内.pdf",
                "type": "binary",
                "mime_type": "application/octet-stream"
            },
            "summary": "",
            "tokens": 354,
            "path": None,
            "element": None,
            "children": [
                {
                    "source_file": None,
                    "summary": "",
                    "tokens": 31,
                    "path": [1],
                    "element": {
                        "type": "Text",
                        "positions": [{"bbox": [265.8, 4.2, 545.9, 18.0], "page": 0}],
                        "text": "f12e5393a8a6a11c1XB639q0FFFXyo-9UPObWOGhl_TRNBdk"
                    },
                    "children": []
                },
                {
                    "source_file": None,
                    "summary": "",
                    "tokens": 323,
                    "path": [2],
                    "element": {
                        "type": "Title",
                        "positions": [{"bbox": [249.5, 23.6, 316.0, 54.5], "page": 0}],
                        "text": "谢贤涛"
                    },
                    "children": [
                        {
                            "source_file": None,
                            "summary": "",
                            "tokens": 7,
                            "path": [2, 1],
                            "element": {
                                "type": "Figure",
                                "positions": [{"bbox": [235.0, 64.0, 330.5, 77.4], "page": 0}],
                                "text": "[图片OCR内容]\n无文字",
                                "name": "",
                                "description": "",
                                "image": {
                                    "type": "image_url",
                                    "url": "https://img.ljcdn.com/cv-aigc/991f1dc8d32b45578663748032f1d130?ak=Q265N5ELG32TT7UWO8YJ&exp=1753957463&ts=1753953863&sign=b1a799da48eefb5c2c85cc4becdb48d3",
                                    "base64": None,
                                    "file_id": None
                                }
                            },
                            "children": []
                        },
                        {
                            "source_file": None,
                            "summary": "",
                            "tokens": 43,
                            "path": [2, 2],
                            "element": {
                                "type": "Title",
                                "positions": [{"bbox": [134.3, 82.0, 431.2, 95.4], "page": 0}],
                                "text": "2年工作经验 | 求职意向：客服专员 | 期望薪资：4-5K | 期望城市：成都"
                            },
                            "children": []
                        },
                        {
                            "source_file": None,
                            "summary": "",
                            "tokens": 130,
                            "path": [2, 3],
                            "element": {
                                "type": "Title",
                                "positions": [{"bbox": [24.0, 114.0, 83.0, 134.6], "page": 0}],
                                "text": "个人优势"
                            },
                            "children": [
                                {
                                    "source_file": None,
                                    "summary": "",
                                    "tokens": 29,
                                    "path": [2, 3, 1],
                                    "element": {
                                        "type": "Text",
                                        "positions": [{"bbox": [24.0, 150.3, 280.6, 163.6], "page": 0}],
                                        "text": "毕业于服务行业(航空专业我做过的服务员工作;八小时工作制"
                                    },
                                    "children": []
                                },
                                {
                                    "source_file": None,
                                    "summary": "",
                                    "tokens": 46,
                                    "path": [2, 3, 2],
                                    "element": {
                                        "type": "Text",
                                        "positions": [{"bbox": [24.0, 168.3, 404.8, 181.6], "page": 0}],
                                        "text": "我的优势:吃住条件不要求、无纹身、接受过服务员培训、形象良好、点单服务、餐中服务,"
                                    },
                                    "children": []
                                },
                                {
                                    "source_file": None,
                                    "summary": "",
                                    "tokens": 35,
                                    "path": [2, 3, 3],
                                    "element": {
                                        "type": "Text",
                                        "positions": [{"bbox": [24.0, 186.3, 238.8, 199.6], "page": 0}],
                                        "text": "我的性格:有礼貌、成熟稳重、诚恳踏实、吃苦耐劳"
                                    },
                                    "children": []
                                },
                                {
                                    "source_file": None,
                                    "summary": "",
                                    "tokens": 15,
                                    "path": [2, 3, 4],
                                    "element": {
                                        "type": "Text",
                                        "positions": [{"bbox": [24.0, 204.3, 154.0, 217.6], "page": 0}],
                                        "text": "我的经验:店员1营业员6个月。"
                                    },
                                    "children": []
                                }
                            ]
                        }
                    ]
                }
            ]
        }

    @pytest.fixture
    def mock_document(self):
        """模拟文档对象"""
        doc = Document(text="test", metadata={"file_id": "test-file-id"})
        return doc

    def test_create_standard_dom_tree_from_json(self, sample_json_data):
        """测试从JSON创建StandardDomTree"""
        parser = PdfParser()

        # 测试创建StandardDomTree
        standard_dom_tree = parser._create_standard_dom_tree_from_json(sample_json_data)

        # 验证基本结构
        assert isinstance(standard_dom_tree, StandardDomTree)
        assert standard_dom_tree.root is not None
        assert len(standard_dom_tree.root.children) == 2

        # 验证根节点信息
        root = standard_dom_tree.root
        assert root.tokens == 354
        assert root.source_file.id == "file-2507311649080024173210-1989906366"
        assert root.source_file.name == "【门店上班 就近分配 租房管家_成都_5-8K】谢贤涛_一年以内.pdf"

    def test_dom_to_nodes_conversion(self, sample_json_data):
        """测试StandardDomTree到nodes的转换"""
        parser = PdfParser()

        # 创建StandardDomTree
        standard_dom_tree = parser._create_standard_dom_tree_from_json(sample_json_data)

        # 转换为nodes
        nodes = dom2nodes(standard_dom_tree)

        # 验证节点数量和基本信息
        assert len(nodes) > 0
        assert all(hasattr(node, 'order_num_str') for node in nodes)
        assert all(hasattr(node, 'doc_relationships') for node in nodes)

    def test_node_types_and_content(self, sample_json_data):
        """测试节点类型和内容"""
        parser = PdfParser()
        standard_dom_tree = parser._create_standard_dom_tree_from_json(sample_json_data)
        nodes = dom2nodes(standard_dom_tree)

        # 按order_num_str分组测试
        node_by_order = {node.order_num_str: node for node in nodes}

        # 测试Text节点
        text_node = node_by_order.get("1")
        assert isinstance(text_node, TextNode)
        assert text_node.text == "f12e5393a8a6a11c1XB639q0FFFXyo-9UPObWOGhl_TRNBdk"
        assert text_node.token == 31
        assert text_node.metadata["element_type"] == "Text"

        # 测试Title节点
        title_node = node_by_order.get("2")
        assert isinstance(title_node, TextNode)
        assert title_node.text == "谢贤涛"
        assert title_node.token == 323
        assert title_node.metadata["element_type"] == "Title"

        # 测试Figure节点
        figure_node = node_by_order.get("2.1")
        assert isinstance(figure_node, ImageNode)
        assert figure_node.text == "[图片OCR内容]\n无文字"
        assert figure_node.token == 7
        assert figure_node.metadata["element_type"] == "Figure"
        assert "https://img.ljcdn.com" in figure_node.image_url

    def test_node_relationships(self, sample_json_data):
        """测试节点关系"""
        parser = PdfParser()
        standard_dom_tree = parser._create_standard_dom_tree_from_json(sample_json_data)
        nodes = dom2nodes(standard_dom_tree)

        # 找到特定节点测试关系
        node_by_order = {node.order_num_str: node for node in nodes}

        # 测试父子关系
        parent_node = node_by_order.get("2")
        child_node = node_by_order.get("2.1")

        if parent_node and child_node:
            # 验证子节点有父节点引用
            assert DocumentNodeRelationship.PARENT in child_node.doc_relationships
            assert child_node.doc_relationships[DocumentNodeRelationship.PARENT] == parent_node

            # 验证父节点有子节点引用
            assert DocumentNodeRelationship.CHILD in parent_node.doc_relationships
            children = parent_node.doc_relationships[DocumentNodeRelationship.CHILD]
            assert child_node in children

    def test_node_metadata(self, sample_json_data):
        """测试节点元数据"""
        parser = PdfParser()
        standard_dom_tree = parser._create_standard_dom_tree_from_json(sample_json_data)
        nodes = dom2nodes(standard_dom_tree)

        # 测试第一个节点的元数据
        first_node = nodes[0]
        metadata = first_node.metadata

        assert "element_type" in metadata
        assert "positions" in metadata
        assert "summary" in metadata

        # 验证positions信息
        positions = metadata["positions"]
        assert len(positions) > 0
        assert "bbox" in positions[0]
        assert "page" in positions[0]

    @patch('bella_rag.utils.file_api_tool.file_api_client')
    def test_parse_pdf_with_file_id(self, mock_client, sample_json_data, mock_document):
        """测试通过file_id解析PDF"""
        # 模拟FileAPIClient返回
        mock_stream = MagicMock()
        mock_stream.seek.return_value = None
        mock_stream.read.return_value = json.dumps(sample_json_data).encode('utf-8')
        mock_client.domtree_content.return_value = mock_stream

        parser = PdfParser()

        # 测试解析
        result = parser._parse_pdf([mock_document], file_id="test-file-id")

        # 验证结果
        assert isinstance(result, StandardDomTree)
        assert result.root.source_file.id == "file-2507311649080024173210-1989906366"

        # 验证调用
        mock_client.domtree_content.assert_called_once_with("test-file-id")

    @patch('bella_rag.utils.file_api_tool.file_api_client')
    def test_parse_nodes_integration(self, mock_client, sample_json_data, mock_document):
        """测试完整的解析流程"""
        # 模拟FileAPIClient返回
        mock_stream = MagicMock()
        mock_stream.seek.return_value = None
        mock_stream.read.return_value = json.dumps(sample_json_data).encode('utf-8')
        mock_client.domtree_content.return_value = mock_stream

        parser = PdfParser()

        # 测试完整流程
        nodes = parser._parse_nodes([mock_document], file_id="test-file-id")

        # 验证结果
        assert len(nodes) > 0
        assert all(hasattr(node, 'order_num_str') for node in nodes)
        assert all(hasattr(node, 'text') for node in nodes)
        assert all(hasattr(node, 'token') for node in nodes)

        # 验证特定节点
        text_nodes = [n for n in nodes if n.metadata.get("element_type") == "Text"]
        title_nodes = [n for n in nodes if n.metadata.get("element_type") == "Title"]
        figure_nodes = [n for n in nodes if n.metadata.get("element_type") == "Figure"]

        assert len(text_nodes) > 0
        assert len(title_nodes) > 0
        assert len(figure_nodes) > 0

    def test_empty_json_handling(self):
        """测试空JSON处理"""
        parser = PdfParser()

        # 测试空数据
        empty_data = {
            "source_file": None,
            "summary": "",
            "tokens": 0,
            "path": None,
            "element": None,
            "children": []
        }

        standard_dom_tree = parser._create_standard_dom_tree_from_json(empty_data)
        nodes = dom2nodes(standard_dom_tree)

        # 验证空数据处理
        assert isinstance(standard_dom_tree, StandardDomTree)
        assert len(nodes) == 0  # 没有子节点，应该没有生成nodes

    @patch('bella_rag.utils.file_api_tool.file_api_client')
    def test_fallback_to_traditional_parser(self, mock_client, mock_document):
        """测试回退到传统解析器"""
        # 模拟FileAPIClient失败
        mock_client.domtree_content.side_effect = Exception("API Error")

        # 模拟传统解析器
        with patch('bella_rag.transformations.parser.pdf_parser.Converter') as mock_converter:
            mock_dom_tree = MagicMock()
            mock_converter_instance = MagicMock()
            mock_converter_instance.dom_tree_parse.return_value = mock_dom_tree
            mock_converter.return_value = mock_converter_instance

            parser = PdfParser()
            mock_document.stream = b"fake pdf content"

            # 测试回退
            result = parser._parse_pdf([mock_document], file_id="test-file-id")

            # 验证回退到传统方式
            assert result == mock_dom_tree
            mock_converter.assert_called_once()
            mock_converter_instance.dom_tree_parse.assert_called_once()
            mock_converter_instance.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
