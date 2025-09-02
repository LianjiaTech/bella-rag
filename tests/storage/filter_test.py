from llama_index.core.vector_stores import FilterCondition

from common.helper.exception import CheckError
from bella_rag.vector_stores.types import MetadataFilters, MetadataFilter, FilterOperator


def test_load_filter_from_dicts():
    condition = FilterCondition.AND
    filter_dicts = [
        {
            "key": "name",
            "value": "张三",
            "operator": "=="
        },
        {
            "key": "age",
            "value": 25,
            "operator": ">"
        },
        {
            "condition": "OR",
            "filters": [
                {
                    "key": "city",
                    "value": "北京",
                    "operator": "=="
                },
                {
                    "key": "city",
                    "value": "上海",
                    "operator": "=="
                }
            ]
        }
    ]
    assert len(MetadataFilters.from_dicts(filter_dicts, condition).filters) > 0


def test_single_exclude_filter(self):
    """测试单个EXCLUDE操作符"""
    filters = MetadataFilters(
        filters=[
            MetadataFilter(key="status", value="deleted", operator=FilterOperator.EXClUDE)
        ]
    )
    result = self._build_tencent_filter_string(filters)
    assert result == "Filter.Exclude(key=status, value=['deleted'])"


def test_multiple_filters_and_condition(self):
    """测试多个过滤器的AND条件"""
    filters = MetadataFilters(
        filters=[
            MetadataFilter(key="game_tag", value="Robert", operator=FilterOperator.EQ),
            MetadataFilter(key="video_tag", value="dance", operator=FilterOperator.EQ)
        ],
        condition=FilterCondition.AND
    )
    result = self._build_tencent_filter_string(filters)
    assert result == '(game_tag = "Robert" and video_tag = "dance")'


def test_multiple_filters_or_condition(self):
    """测试多个过滤器的OR条件"""
    filters = MetadataFilters(
        filters=[
            MetadataFilter(key="game_tag", value="1000", operator=FilterOperator.EQ),
            MetadataFilter(key="video_tag", value="dance", operator=FilterOperator.EQ)
        ],
        condition=FilterCondition.OR
    )
    result = self._build_tencent_filter_string(filters)
    assert result == '(game_tag = "1000" or video_tag = "dance")'


def test_nested_filters(self):
    """测试嵌套的过滤器结构"""
    nested_filters = MetadataFilters(
        filters=[
            MetadataFilter(key="game_tag", value="Robert", operator=FilterOperator.EQ),
            MetadataFilters(
                filters=[
                    MetadataFilter(key="video_tag", value="dance", operator=FilterOperator.EQ),
                    MetadataFilter(key="video_tag", value="music", operator=FilterOperator.EQ)
                ],
                condition=FilterCondition.OR
            )
        ],
        condition=FilterCondition.AND
    )
    result = self._build_tencent_filter_string(nested_filters)
    assert result == '(game_tag = "Robert" and (video_tag = "dance" or video_tag = "music"))'


def test_deeply_nested_filters(self):
    """测试深度嵌套的过滤器结构"""
    deeply_nested = MetadataFilters(
        filters=[
            MetadataFilter(key="category", value="game", operator=FilterOperator.EQ),
            MetadataFilters(
                filters=[
                    MetadataFilter(key="genre", value="RPG", operator=FilterOperator.EQ),
                    MetadataFilters(
                        filters=[
                            MetadataFilter(key="year", value="2020", operator=FilterOperator.EQ),
                            MetadataFilter(key="platform", value="PC", operator=FilterOperator.EQ)
                        ],
                        condition=FilterCondition.AND
                    )
                ],
                condition=FilterCondition.OR
            )
        ],
        condition=FilterCondition.AND
    )
    result = self._build_tencent_filter_string(deeply_nested)
    expected = '(category = "game" and (genre = "RPG" or (year = "2020" and platform = "PC")))'
    assert result == expected


def test_mixed_operators(self):
    """测试混合操作符"""
    filters = MetadataFilters(
        filters=[
            MetadataFilter(key="name", value="test", operator=FilterOperator.EQ),
            MetadataFilter(key="tags", value=["action"], operator=FilterOperator.ANY),
            MetadataFilter(key="status", value="active", operator=FilterOperator.NE)
        ],
        condition=FilterCondition.AND
    )
    result = self._build_tencent_filter_string(filters)
    expected = '(name = "test" and Filter.Include(key=tags, value=[\'action\']) and status != "active")'
    assert result == expected


def test_empty_filters(self):
    """测试空的过滤器列表"""
    filters = MetadataFilters(filters=[])
    result = self._build_tencent_filter_string(filters)
    assert result == ""


def test_default_condition(self):
    """测试默认条件（应该是AND）"""
    filters = MetadataFilters(
        filters=[
            MetadataFilter(key="a", value="1", operator=FilterOperator.EQ),
            MetadataFilter(key="b", value="2", operator=FilterOperator.EQ)
        ]
        # 没有指定condition，应该默认为AND
    )
    result = self._build_tencent_filter_string(filters)
    assert result == '(a = "1" and b = "2")'


def test_numeric_values(self):
    """测试数值类型的值"""
    filters = MetadataFilters(
        filters=[
            MetadataFilter(key="score", value=100, operator=FilterOperator.EQ),
            MetadataFilter(key="rating", value=4.5, operator=FilterOperator.NE)
        ],
        condition=FilterCondition.AND
    )
    result = self._build_tencent_filter_string(filters)
    assert result == '(score = "100" and rating != "4.5")'


def test_single_filter_no_parentheses(self):
    """测试单个过滤器不应该有括号"""
    filters = MetadataFilters(
        filters=[
            MetadataFilter(key="single", value="test", operator=FilterOperator.EQ)
        ]
    )
    result = self._build_tencent_filter_string(filters)
    assert result == 'single = "test"'
    # 确保没有括号
    assert not result.startswith('(')
    assert not result.endswith(')')
