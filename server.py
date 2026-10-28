import os, json, sqlite3, secrets, hashlib, hmac, time, base64, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
ROOT=Path(__file__).parent
DATA=Path(os.environ.get('PREPLAN_DATA', ROOT/'data')); DATA.mkdir(exist_ok=True); (DATA/'assets').mkdir(exist_ok=True)
def db():
 c=sqlite3.connect(DATA/'preplan.db'); c.row_factory=sqlite3.Row; return c
with db() as c:
 c.executescript('''CREATE TABLE IF NOT EXISTS departments(id TEXT PRIMARY KEY,name TEXT,seat_limit INTEGER,subscription_status TEXT DEFAULT 'development');
 CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE,name TEXT,password TEXT,department_id TEXT,role TEXT,status TEXT DEFAULT 'active');
 CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT,expires REAL);
 CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,owner_id TEXT,department_id TEXT,title TEXT,state TEXT,updated REAL);
 CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,owner_id TEXT,mime TEXT);''')
def password(p,salt=None):
 salt=salt or secrets.token_hex(16); return salt+':'+hashlib.pbkdf2_hmac('sha256',p.encode(),salt.encode(),600000).hex()
def public(u): return {k:u[k] for k in ['id','email','name','department_id','role','status']}
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def respond(self,status,obj,mime='application/json',headers=None):
  raw=json.dumps(obj).encode() if mime=='application/json' and not isinstance(obj,bytes) else obj
  self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Content-Length',str(len(raw))); self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Cache-Control','no-store')
  for k,v in (headers or {}).items(): self.send_header(k,v)
  self.end_headers(); self.wfile.write(raw)
 def do_GET(self): self.handle_request('GET')
 def do_POST(self): self.handle_request('POST')
 def do_PUT(self): self.handle_request('PUT')
 def handle_request(self,method):
  try: self.route(method)
  except (ValueError,KeyError,TypeError,json.JSONDecodeError): self.respond(400,{'error':'Invalid request.'})
  except Exception as e:
   print(type(e).__name__,str(e)); self.respond(500,{'error':'Server error.'})
 def route(self,method):
  path=self.path.split('?')[0]
  if method=='GET' and path in ['/','/app.js','/style.css']:
   name={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]; return self.respond(200,(ROOT/'static'/name).read_bytes(),{'index.html':'text/html','app.js':'application/javascript','style.css':'text/css'}[name])
  if method=='GET' and re.fullmatch(r'/symbols/[a-z0-9-]+\.(svg|html|json)',path):
   asset=ROOT/'static'/path.lstrip('/')
   if asset.is_file(): return self.respond(200,asset.read_bytes(),{'.svg':'image/svg+xml','.html':'text/html','.json':'application/json'}[asset.suffix])
  if not path.startswith('/api/'): return self.respond(404,{'error':'Not found'})
  if method!='GET':
   origin=self.headers.get('Origin')
   if origin and origin not in ['http://'+self.headers.get('Host',''),'https://'+self.headers.get('Host','')]: return self.respond(403,{'error':'Origin denied'})
  length=int(self.headers.get('Content-Length','0'))
  if length>16*1024*1024: return self.respond(413,{'error':'Upload must be under 10 MB.'})
  body=json.loads(self.rfile.read(length)) if length else {}
  with db() as c:
   if path in ['/api/register','/api/login'] and method=='POST':
    email=body['email'].strip().lower(); pw=body['password']; u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
    if path.endswith('register'):
     if u or len(pw)<10 or '@' not in email or not body.get('name','').strip(): return self.respond(400,{'error':'Use a new email, a name, and a password of at least 10 characters.'})
     uid=secrets.token_hex(16); did=secrets.token_hex(16)
     # Serialize first-user role assignment across simultaneous registrations.
     c.execute('BEGIN IMMEDIATE'); role='admin' if c.execute('SELECT count(*) FROM users').fetchone()[0]==0 else 'member'
     c.execute('INSERT INTO departments(id,name) VALUES(?,?)',(did,body.get('department','My department')))
     c.execute('INSERT INTO users(id,email,name,password,department_id,role) VALUES(?,?,?,?,?,?)',(uid,email,body['name'],password(pw),did,role)); u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    elif not u or not hmac.compare_digest(password(pw,u['password'].split(':')[0]),u['password']): return self.respond(401,{'error':'Email or password is incorrect.'})
    if u['status']!='active': return self.respond(403,{'error':'Account suspended.'})
    token=secrets.token_urlsafe(32); c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],time.time()+86400))
    return self.respond(200,public(u),headers={'Set-Cookie':f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400'})
   cookies=dict(x.strip().split('=',1) for x in self.headers.get('Cookie','').split(';') if '=' in x); token=hashlib.sha256(cookies.get('session','').encode()).hexdigest()
   u=c.execute('SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id WHERE s.token=? AND s.expires>? AND u.status=?',(token,time.time(),'active')).fetchone()
   if not u: return self.respond(401,{'error':'Please sign in.'})
   if path=='/api/me': return self.respond(200,public(u))
   if path=='/api/logout':
    c.execute('DELETE FROM sessions WHERE token=?',(token,)); return self.respond(200,{},headers={'Set-Cookie':'session=; Max-Age=0; Path=/'})
   if path=='/api/users':
    if u['role']!='admin': return self.respond(403,{'error':'Administrator access required.'})
    if method=='PUT':
     if body['id']==u['id'] or body['status'] not in ['active','suspended']: return self.respond(400,{'error':'Cannot suspend your own account.'})
     c.execute('UPDATE users SET status=? WHERE id=?',(body['status'],body['id']))
    return self.respond(200,[public(x) for x in c.execute('SELECT * FROM users')])
   if path=='/api/assets' and method=='POST':
    raw=base64.b64decode(body['data'],validate=True); mime=body['mime']
    if len(raw)>10*1024*1024 or not ((mime=='image/png' and raw.startswith(b'\x89PNG\r\n\x1a\n')) or (mime=='image/jpeg' and raw.startswith(b'\xff\xd8\xff'))): return self.respond(400,{'error':'Upload a PNG or JPEG under 10 MB.'})
    aid=secrets.token_hex(16); (DATA/'assets'/aid).write_bytes(raw); c.execute('INSERT INTO assets VALUES(?,?,?)',(aid,u['id'],mime)); return self.respond(200,{'id':aid})
   if path.startswith('/api/assets/') and method=='GET':
    aid=path.rsplit('/',1)[1]; a=c.execute('SELECT * FROM assets WHERE id=? AND owner_id=?',(aid,u['id'])).fetchone()
    if not a: return self.respond(404,{'error':'Asset not found.'})
    return self.respond(200,(DATA/'assets'/aid).read_bytes(),a['mime'])
   if path=='/api/projects':
    if method=='GET': return self.respond(200,[dict(x) for x in c.execute('SELECT id,title,updated FROM projects WHERE owner_id=? ORDER BY updated DESC',(u['id'],))])
    state=body['state']; aid=state.get('asset')
    if aid and not c.execute('SELECT id FROM assets WHERE id=? AND owner_id=?',(aid,u['id'])).fetchone(): return self.respond(403,{'error':'Invalid base image ownership.'})
    pid=body.get('id') or secrets.token_hex(16); existing=c.execute('SELECT owner_id FROM projects WHERE id=?',(pid,)).fetchone()
    if existing and existing['owner_id']!=u['id']: return self.respond(404,{'error':'Project not found.'})
    c.execute('INSERT INTO projects VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,state=excluded.state,updated=excluded.updated',(pid,u['id'],u['department_id'],body['title'][:120],json.dumps(state),time.time())); return self.respond(200,{'id':pid})
   if path.startswith('/api/projects/') and method=='GET':
    p=c.execute('SELECT * FROM projects WHERE id=? AND owner_id=?',(path.rsplit('/',1)[1],u['id'])).fetchone()
    if not p: return self.respond(404,{'error':'Project not found.'})
    return self.respond(200,{'id':p['id'],'title':p['title'],'state':json.loads(p['state'])})
   self.respond(404,{'error':'Not found.'})
if __name__=='__main__':
 print('Preplan running at http://127.0.0.1:8765',flush=True); ThreadingHTTPServer(('127.0.0.1',int(os.environ.get('PORT','8765'))),Handler).serve_forever()
