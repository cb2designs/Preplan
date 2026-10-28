import unittest, tempfile, os, threading, json, urllib.request, urllib.error, http.cookiejar, base64
os.environ['PREPLAN_DATA']=tempfile.mkdtemp(prefix='preplan-tests-')
import server
class API(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler); threading.Thread(target=cls.http.serve_forever,daemon=True).start(); cls.url='http://127.0.0.1:'+str(cls.http.server_port)
 @classmethod
 def tearDownClass(cls): cls.http.shutdown(); cls.http.server_close()
 def client(self): return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def req(self,c,path,body=None,method=None,origin=None):
  r=urllib.request.Request(self.url+'/api/'+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers={'Content-Type':'application/json',**({'Origin':origin} if origin else {})})
  try:
   with c.open(r) as response:
    raw=response.read(); return response.status,json.loads(raw) if response.headers.get_content_type()=='application/json' else raw
  except urllib.error.HTTPError as e: return e.code,json.loads(e.read())
 def test_public_symbol_assets(self):
  for path,mime in [('review.html','text/html'),('fdc-2.svg','image/svg+xml'),('catalog.json','application/json')]:
   with urllib.request.urlopen(self.url+'/symbols/'+path) as r:
    self.assertEqual(r.status,200); self.assertEqual(r.headers.get_content_type(),mime)
    if path.endswith('.json'): self.assertEqual(len(json.loads(r.read())),17)
 def test_full_access_and_persistence(self):
  a,b=self.client(),self.client()
  self.assertEqual(self.req(a,'projects')[0],401)
  status,admin=self.req(a,'register',dict(email='admin@example.test',password='longpassword123',name='Admin')); self.assertEqual(status,200); self.assertEqual(admin['role'],'admin')
  status,member=self.req(b,'register',dict(email='member@example.test',password='longpassword123',name='Member')); self.assertEqual(status,200); self.assertEqual(member['role'],'member')
  self.assertEqual(self.req(b,'users')[0],403)
  raw=b'\x89PNG\r\n\x1a\nexample'
  status,asset=self.req(b,'assets',dict(mime='image/png',data=base64.b64encode(raw).decode())); self.assertEqual(status,200)
  self.assertEqual(self.req(a,'assets/'+asset['id'])[0],404)
  self.assertEqual(self.req(b,'assets/'+asset['id'])[1],raw)
  state=dict(asset=asset['id'],width=1600,height=1000,scale=.25,units='ft',items=[dict(type='symbol',code='FDC',x=100,y=200,label='FDC')])
  status,p=self.req(b,'projects',dict(title='Test plan',state=state)); self.assertEqual(status,200)
  self.assertEqual(self.req(a,'projects/'+p['id'])[0],404)
  self.assertEqual(self.req(a,'projects',dict(id=p['id'],title='Override',state={}))[0],404)
  self.assertEqual(self.req(a,'projects',dict(title='Foreign asset',state=state))[0],403)
  self.req(b,'logout',{},'POST'); self.assertEqual(self.req(b,'projects')[0],401)
  self.assertEqual(self.req(b,'login',dict(email='member@example.test',password='wrong'))[0],401)
  self.assertEqual(self.req(b,'login',dict(email='member@example.test',password='longpassword123'))[0],200)
  self.assertEqual(self.req(b,'projects/'+p['id'])[1]['state'],state)
  self.assertEqual(self.req(b,'projects',dict(title='Bad origin',state={}),origin='https://evil.test')[0],403)
  self.assertEqual(self.req(a,'users',dict(id=member['id'],status='suspended'),'PUT')[0],200)
  self.assertEqual(self.req(b,'projects')[0],401)
  self.assertEqual(self.req(b,'assets/'+asset['id'])[0],401)
  self.assertEqual(self.req(a,'users',dict(id=admin['id'],status='suspended'),'PUT')[0],400)
if __name__=='__main__': unittest.main()
