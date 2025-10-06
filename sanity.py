# sanity.py — απόλυτος έλεγχος κλειδιών & σύνδεσης
import os, re, requests
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI

def mask(s): 
    return (s[:8]+'…'+s[-6:]) if s and len(s)>16 else ('EMPTY' if not s else 'SHORT')

def bad_chars(s):
    return [(i, repr(c), hex(ord(c))) for i,c in enumerate(s) if not re.match(r'[A-Za-z0-9_-]', c)]

# 1) Φόρτωσε .env και μετά .env.override (override τελευταίο)
dotenv_main = find_dotenv(usecwd=True)
if dotenv_main:
    load_dotenv(dotenv_main, override=False)
if os.path.exists('.env.override'):
    load_dotenv('.env.override', override=True)

okey = os.getenv('OPENAI_API_KEY','')
gkey = os.getenv('GOOGLE_CSE_KEY','')
cx   = os.getenv('GOOGLE_CSE_ID','')

print('OPENAI:', mask(okey))
print('  len =', len(okey), '| startswith sk-proj- =', okey.startswith('sk-proj-'))
print('  bad  =', bad_chars(okey))

print('CSE KEY:', mask(gkey), 'CX:', mask(cx))

# 2) OpenAI test
if not okey:
    print('OpenAI: MISSING KEY')
else:
    try:
        c = OpenAI(api_key=okey)
        n = len(list(c.models.list()))
        print('OpenAI: OK models =', n)
    except Exception as e:
        print('OpenAI: ERROR:', e)

# 3) CSE test (light)
if gkey and cx:
    try:
        r = requests.get('https://www.googleapis.com/customsearch/v1',
                         params={'key':gkey,'cx':cx,'q':'sneakers','num':1,'searchType':'image'}, timeout=15)
        j = r.json()
        print('CSE: status', r.status_code, '| items:', len(j.get('items',[])))
    except Exception as e:
        print('CSE: ERROR:', e)
else:
    print('CSE: missing key/cx')
