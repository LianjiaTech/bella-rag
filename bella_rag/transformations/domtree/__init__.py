"""
Pipeline components for specialized file processing workflows
"""
from bella_rag.transformations.domtree.domtree_transformation import DomTreeParser
from bella_rag.transformations.domtree.domtree_transformation import DomTreeParser
from bella_openapi import StandardNode, StandardTableElement, StandardRow, Cell
from bella_rag.utils.openapi_util import count_tokens
import base64
from bella_rag.providers import image_storage_provider
from init.settings import user_logger

domtree_parser = DomTreeParser()

def format_domtree(tree:StandardNode) -> StandardNode:

        """
        将StandardNode转换为StandardNode，递归处理子节点并计算tokens

        Args:
            tree: StandardNode对象
        Returns:
            StandardNode
        """
        # 递归处理子节点，确保所有子节点都是 StandardNode 类型
        if tree.tokens:
            return tree
        children = []
        if tree.children:
            for child in tree.children:
                # 递归转换子节点
                child_node = format_domtree(child)
                children.append(child_node)

        # 计算当前节点的tokens
        tokens = 0
        if tree.element:
            if tree.element.type == "Figure":
                # 处理图片节点
                image_url = ""
                if tree.element.image and tree.element.image.type == 'image_base64' and tree.element.image.base64:
                    image_url = upload_base64_image(tree.element.image.base64)
                    # 将图片的base64 转为url
                    if image_url:  # 如果转换成功
                        tree.element.image.url = image_url
                        tree.element.image.type = "image_url"
                        # 删除原来的base64字段
                        delattr(tree.element.image, 'base64')

                if tree.element.text:
                    tokens += count_tokens(tree.element.text)

            elif tree.element.type == "Table":
                # 处理表格节点
                tree = complete_table_extra_info(tree)
                tokens += tree.tokens
            else:
                # 处理其他类型节点
                tokens += count_tokens(tree.element.text) if tree.element.text else 0

        # 递归处理子节点的tokens并累加
        if children:
            for child in children:
                tokens += child.tokens or 0


        # 创建StandardNode，确保所有子节点都是 StandardNode 类型
        node = StandardNode(
            source_file=tree.source_file,
            summary=tree.summary or "",
            tokens=tokens,
            path=tree.path or [],
            element=None,
            children=children,
        )
        node.element = tree.element

        return node

def complete_table_extra_info(table_node: StandardNode) -> StandardNode:

    new_rows = []
    cell_tokens = []
    for row in table_node.element.rows:
        new_cells = []
        for cell in row.cells:

            cell_path = cell.path
            cell_text = cell.text
            cell_token = count_tokens(cell_text)
            element_data = {"type": "Text", "text": cell_text, "positions": None}
            nodes = [StandardNode(summary="", tokens=cell_token, path=[1], children=[], element=element_data)]
            new_cell = Cell(path=cell.path,text=cell.text,nodes=nodes)
            cell_tokens.append(cell_token)
            new_cells.append(new_cell)
        new_row = StandardRow(cells=new_cells)
        new_rows.append(new_row)

    element = StandardTableElement(type="Table",rows=new_rows,name=table_node.element.name,description=table_node.element.description)
    new_table_node = StandardNode(summary=table_node.summary,tokens=sum(cell_tokens),path=table_node.path,children=[],element=element)


    return new_table_node

# 上传base64图片
def upload_base64_image(base64_data: str) -> str:
    """上传base64编码的图片"""
    try:
        # 处理带前缀的base64数据: data:image/jpeg;base64,xxxxx
        base64_value = base64_data.split(',')[1]

        # 解码base64
        image_bytes = base64.b64decode(base64_value)

        # 上传并获取文件名
        file_name = image_storage_provider.upload(image_bytes)

        # 获取访问URL
        image_url = image_storage_provider.download(file_name)

        return image_url
    except Exception as e:
        user_logger.info(f"图片上传失败: {e}")
        return None

