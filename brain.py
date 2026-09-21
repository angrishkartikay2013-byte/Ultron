import requests

MODEL="qwen3:8b"
URL="http://127.0.0.1:11434/api/chat"

history=[{"role":"system","content":"You are ULTRON GENESIS. Call the user Founder."}]

def ask(prompt):
    history.append({"role":"user","content":prompt})
    r=requests.post(URL,json={"model":MODEL,"messages":history,"stream":False,"think":False},timeout=180)
    r.raise_for_status()
    reply=r.json()["message"]["content"]
    history.append({"role":"assistant","content":reply})
    return reply
