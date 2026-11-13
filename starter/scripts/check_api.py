"""One real RAG chat smoke check, separate from benchmark questions."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from starter.src.demo import chat
from starter.src.project import write_json,RESULTS,now

question='When does a loop else block run, and what happens if the loop exits with break?'
result=chat(question,'C','Loops')
write_json(RESULTS/'chat_demo.json',{'at':now(),'question':question,**result})
assert result.get('citation_check')=='passed','Chat did not pass source-page citation checks'
print('Real chat completed:',result.get('model'))
print('Answer saved to results/chat_demo.json; source chunks:',len(result['hits']))
print('Usage:',result.get('usage'))
