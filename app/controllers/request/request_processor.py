from bella_rag.utils.file_api_tool import file_api_client
from typing import List
from common.helper.exception import CheckError

def extract_file_ids_from_scope(scope: List[dict]) -> List[str]:
    """
    根据scope配置提取所有相关的file_ids
    """
    file_ids = []

    for scope_item in scope:
        scope_type = scope_item.get('type')
        scope_ids = scope_item.get('ids', [])

        if scope_type == 'file':
            # 直接添加file_ids
            file_ids.extend(scope_ids)
        elif scope_type == 'space':
            # 通过space获取该空间下所有file_ids
            for space_id in scope_ids:
                try:
                    space_file_ids = file_api_client.get_file_ids_by_space(space_id)
                    file_ids.extend(space_file_ids)
                except Exception as e:
                    raise CheckError(f"获取空间 {space_id} 下的文件失败: {str(e)}")

    # 去重并返回
    return list(set(file_ids))
