from init.settings import RERANK
from bella_rag.llm.openapi import Rerank

rerank = Rerank(api_base=RERANK['URL'], model=RERANK['MODEL']) if RERANK.get('URL') and RERANK.get('MODEL') else None
