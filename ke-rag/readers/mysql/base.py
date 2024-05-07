# -*- coding:utf-8 -*-
# @Time: 2024/5/7 12:26
# @Author: dongmenghui
# @Email: dongmenghui001@ke.com
# @File: base.py
# https://llamahub.ai/l/readers/llama-index-readers-database?from=readers
# https://github.com/run-llama/llama_index/tree/main/llama-index-integrations/readers/llama-index-readers-database

from llama_index.core.schema import Document
from llama_index.readers.database import DatabaseReader


def load_data():
    # Initialize DatabaseReader with the SQL database connection details
    reader = DatabaseReader(
        scheme="mysql+pymysql",  # Optional: Scheme
        host="m12020.mars.test.mysql.ljnode.com",  # Optional: Host
        port="12020",  # Optional: Port
        user="root",  # Optional: Username
        password="123456",  # Optional: Password
        dbname="risk_manager",  # Optional: Database Name
    )

    # Load data from the database using a query
    documents = reader.load_data(
        query="SELECT question, answer FROM `risk_manager`.`knowledge_qa_pair_record` WHERE `file_name` <> '' AND `id` BETWEEN 304 AND 305;"
        # SQL query parameter to filter tables and rows
    )

    return documents


###
#数据结果
[Document(id_='af50def3-e208-4ef6-9cca-f211cf9b24a7', embedding=None, metadata={}, excluded_embed_metadata_keys=[],
          excluded_llm_metadata_keys=[], relationships={},
          text='question: 未按规定办理年度汇算影响是什么？, answer: 纳税人如未依法如实办理综合所得年度汇算的，可能面临税务行政处罚，并记入个人纳税信用档案； 不如实报送专项附加扣除信息，除承担上述不如实申报的法律后果外，还可能对您享受专项附加扣除造成一定影响。如果纳税人填报的专项附加扣除信息存在明显错误，经税务机关通知，拒不更正也不说明情况，税务机关可暂停其享受专项附加扣除。待纳税人按规定更正相关信息或者说明情况后，可继续专项附加扣除，以前月份未享受扣除的，可按规定追补扣除； 根据税收征管法第六十二条： 纳税人未按照规定期限办理纳税申报和报送纳税资料的，由税务机关责令限期改正，可以处 2000 元以下的罚款；情节严重的，可以处 2000 元以上 1 万元以下的罚款，并追缴税款、加征滞纳金； 根据税收征管法第六十三条规定： 如纳税人偷税的，由税务机关追缴其不缴或者少缴的税款、滞纳金，并处不缴或者少缴的税款百分之五十以上五倍以下的罚款；构成犯罪的，依法追究刑事责任； 根据税收征管法第六十四条： 纳税人编造虚假计税依据的，由税务机关责令限期改正，并处五万元以下的罚款；纳税人不进行纳税申报，不缴或者少缴应纳税款的，由税务机关追缴其不缴或者少缴的税款、滞纳金，并处不缴或者少缴的税款百分之五十以上五倍以下的罚款。 对于年度汇算需补税的纳税人，如在年度汇算期结束后未申报并补缴税款，税务部门将依法加收滞纳金，并在其《个人所得税纳税记录》中予以标注。对于涉税金额较大的，税务部门将进行提示提醒，对提醒后未改正或者改正不到位的进行督促整改，对仍不改正或者改正不到位的进行约谈警示，约谈警示后仍不配合整改的依法立案稽查，对立案案件选择部分情节严重、影响恶劣的进行公开曝光。\n',
          start_char_idx=None, end_char_idx=None, text_template='{metadata_str}\n\n{content}',
          metadata_template='{key}: {value}', metadata_seperator='\n'),
 Document(id_='53ec5e96-4a82-4a45-8572-7cc7c412ae50', embedding=None, metadata={}, excluded_embed_metadata_keys=[],
          excluded_llm_metadata_keys=[], relationships={},
          text='question: 什么是预录入?, answer: 预录入环节是加盟商现在平台系统外，将手里的房源信息（包括不限于业主、地址、电话、备件、钥匙等）预先录入到预录入系统中，预录入结束后进行融合/并网环节，将加盟商房源与平台内房源信息比较： ①如房源地址/电话与平台内房源一致，则认定为重复房源，可获取一定的重复角色，成交后按规则获取业绩； ② 如房源地址一致，电话不一致，加盟商可走申诉流程，说明新录入号码也为业主号码，CA审核通过之后，再认定为重复房源，获取重复角色； ③如系统内无相关房源，则认定为新房源，与平台内普通新录房源同样管理，需要进行验真，之后按ACN规则获取房源角色。 预录入阶段非正式系统，不参与正式系统的作业（查看房源、房客作业等），融合之后进入正式系统，开始作业。\n',
          start_char_idx=None, end_char_idx=None, text_template='{metadata_str}\n\n{content}',
          metadata_template='{key}: {value}', metadata_seperator='\n')]
###

if __name__ == "__main__":
    print(load_data())
