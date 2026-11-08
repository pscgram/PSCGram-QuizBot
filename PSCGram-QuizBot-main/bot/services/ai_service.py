import json
from openai import OpenAI
from bot.config import OPENAI_API_KEY,OPENAI_MODEL

def make_questions(source,count=8):
    if not OPENAI_API_KEY: raise RuntimeError("OPENAI_API_KEY is missing.")
    client=OpenAI(api_key=OPENAI_API_KEY)
    prompt=f'''Generate up to {count} exam MCQs strictly grounded in the source below.
Return JSON: {{"questions":[{{"question":"...","options":["A","B","C","D"],"correct_answer":0,
"explanation":"...","subject":"...","topic":"...","difficulty":"easy|medium|hard",
"source_reference":"PDF page reference"}}]}}.
Rules: exactly four options, one unambiguous correct answer, no invented facts, no duplicates,
preserve Malayalam when source is Malayalam, source_reference must cite the supplied PDF page marker.
SOURCE:
{source}'''
    r=client.chat.completions.create(model=OPENAI_MODEL,temperature=0.1,
      response_format={"type":"json_object"},
      messages=[{"role":"system","content":"You are a careful PSC exam question writer. Never use outside facts."},
                {"role":"user","content":prompt}])
    obj=json.loads(r.choices[0].message.content or "{}"); clean=[]; seen=set()
    for x in obj.get("questions",[]):
        q=x.get("question"); opts=x.get("options"); ans=x.get("correct_answer")
        if not isinstance(q,str) or q.casefold().strip() in seen: continue
        if not isinstance(opts,list) or len(opts)!=4 or not all(isinstance(o,str) and o.strip() for o in opts): continue
        if not isinstance(ans,int) or isinstance(ans,bool) or ans not in range(4): continue
        seen.add(q.casefold().strip())
        clean.append({"question":q.strip(),"options":opts,"answer":ans,"explanation":str(x.get("explanation","")),
          "subject":str(x.get("subject","General")),"topic":str(x.get("topic","General")),
          "difficulty":str(x.get("difficulty","medium")),"source":str(x.get("source_reference",""))})
    return clean
