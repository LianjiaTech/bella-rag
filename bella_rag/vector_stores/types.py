from enum import Enum
from typing import List, Union, Dict, Optional

from llama_index.core.vector_stores import MetadataFilters as OriginalMetadataFilters, MetadataFilter
from llama_index_client import FilterCondition

from common.helper.exception import CheckError


class FilterOperator(str, Enum):
    """Vector store filter operator."""

    EQ = "=="  # default operator (string, int, float)
    GT = ">"  # greater than (int, float)
    LT = "<"  # less than (int, float)
    NE = "!="  # not equal to (string, int, float)
    GTE = ">="  # greater than or equal to (int, float)
    LTE = "<="  # less than or equal to (int, float)
    IN = "in"  # In array (string or number)
    NIN = "nin"  # Not in array (string or number)
    ANY = "any"  # Contains any (array of strings)
    ALL = "all"  # Contains all (array of strings)
    TEXT_MATCH = "text_match"  # full text match (allows you to search for a specific substring, token or phrase within the text field)
    CONTAINS = "include"  # metadata array contains value (string or number)
    EXClUDE = "exclude"  # 不包含某个元素

    @staticmethod
    def get_operator_by_value(value: str):
        return FilterOperator._value2member_map_[value]


condition_mapping = {
    FilterCondition.AND.value: FilterCondition.AND,
    FilterCondition.OR.value: FilterCondition.OR,
}


class MetadataFilter(MetadataFilter):
    operator: Union[FilterOperator] = FilterOperator.EQ

    @classmethod
    def from_dict(
            cls,
            filter_dict: Dict,
    ) -> "MetadataFilter":
        return MetadataFilter.parse_obj(filter_dict)


class MetadataFilters(OriginalMetadataFilters):
    """
    默认支持所有类型，在_to_vdb_filter判断是否真的支持了，不在这抛出异常
    """
    filters: List[Union["MetadataFilters", MetadataFilter]]

    def legacy_filters(self) -> List:
        """Convert MetadataFilters to legacy ExactMatchFilters."""
        filters = []

        for f in self.filters:
            if isinstance(f, MetadataFilters):
                filters.extend(f.legacy_filters())
            elif isinstance(f, MetadataFilter):
                filters.append(f)
        return filters

    @classmethod
    def from_dicts(
            cls,
            filter_dicts: List[Dict],
            condition: Optional[FilterCondition] = FilterCondition.AND,
    ) -> "MetadataFilters":
        filters = []

        for f in filter_dicts:
            if "condition" in f.keys() and "filters" in f.keys():
                condition_value = f.get("condition").lower()
                nested_filters = f.get("filters", [])

                if condition_value in condition_mapping:
                    nested_condition = condition_mapping.get(condition_value, None)
                    if not nested_condition:
                        raise ValueError(f"not supported condition: {condition_value}")

                    filters.append(
                        cls.from_dicts(
                            filter_dicts=nested_filters,
                            condition=nested_condition
                        )
                    )
            else:
                filters.append(MetadataFilter.from_dict(f))
        return cls(
            filters=filters,
            condition=condition,
        )


    @classmethod
    def from_dict(cls, filter_dict: Dict) -> "MetadataFilters":
        """Create MetadataFilters from json."""
        if "condition" in filter_dict.keys() and "filters" in filter_dict.keys():
            condition_value = filter_dict.get("condition")
            nested_filters = filter_dict.get("filters", [])

            if condition_value in condition_mapping:
                nested_condition = condition_mapping.get(condition_value, None)
                if not nested_condition:
                    raise ValueError(f"not supported condition: {condition_value}")

                return cls.from_dicts(
                    filter_dicts=nested_filters,
                    condition=nested_condition
                )
        return cls.from_dicts(filter_dicts=[])
