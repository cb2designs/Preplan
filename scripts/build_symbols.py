"""Trace supplied NFPA 170 (2024) table screenshots into SVG paths.
Run with the bundled Python/Pillow runtime. No raster data is embedded in SVG.
"""
from pathlib import Path
from PIL import Image
import json, math, html, argparse
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-dir',type=Path,required=True,help='Directory containing the three original table screenshots')
SOURCE=parser.parse_args().source_dir
files={k:next(SOURCE.glob('Screenshot 2026-10-28 at '+v+'*.png')) for k,v in [('a','1.24.54'),('b','1.25.23'),('c','1.25.42')]}
RED='#C8102E'; BLUE='#005EB8'; GREEN='#00843D'
# code, source page, artwork bounds, title, application, foreground/background style
rows=[
('FDC-2','a',(83,175,213,302),'Fire Department Automatic Sprinkler Connection — Siamese','Identifies a fire department connection supplying an automatic sprinkler system through a siamese connection.','red'),
('FDC-1','a',(83,353,213,482),'Fire Department Automatic Sprinkler Connection — Single','Identifies a single fire department connection supplying an automatic sprinkler system.','red'),
('FDC-SP','a',(83,514,213,641),'Fire Department Standpipe Connection','Identifies the location of a fire department connection serving a standpipe system.','red'),
('FDC-C','a',(83,691,213,815),'Fire Department Combined Automatic Sprinkler/Standpipe Connection','Identifies a fire department connection supplying a combined automatic sprinkler and standpipe system.','red'),
('HYD','a',(83,848,207,973),'Fire Hydrant (All Types)','Identifies the location of a fire hydrant.','red'),
('VALVE','b',(42,156,167,281),'Automatic Sprinkler Control Valve','Identifies the location of an automatic sprinkler control valve.','red'),
('ELEC','b',(42,314,168,440),'Electric Panel or Electric Shutoff','Identifies an electrical panel or another device used to shut off electrical power.','blue'),
('GAS','b',(42,473,168,599),'Gas Shutoff Valve','Identifies the location of a valve used to shut off gas.','red'),
('HOSE','b',(42,631,168,757),'Firefighting Hose or Standpipe Outlet','Identifies the location of a firefighting hose or a standpipe outlet.','red'),
('EXT','b',(42,789,168,915),'Fire Extinguisher','Identifies the location of a fire extinguisher.','red'),
('ARROW','b',(42,947,125,1023),'Directional Arrow','Points toward firefighting equipment or a utility. Use adjacent to and together with the symbol for that equipment or utility; match its background color.','arrow'),
('ARROW-NE','c',(51,152,131,224),'Diagonal Directional Arrow','Points diagonally toward firefighting equipment or a utility. Use adjacent to and together with the symbol for that equipment or utility; match its background color.','arrow'),
('CHILD','c',(51,297,175,420),'Childcare Center','Identifies the location of a childcare center.','child'),
('PHONE','c',(49,454,138,543),'Emergency Telephone','Identifies the location of a fire-service or emergency telephone system.','red'),
('NO-FIRE','c',(49,575,175,699),'No Firefighting','Marks a building where firefighting must not occur. Place on, near, or on the approach to the building.','prohibition'),
('SCBA','c',(51,741,131,866),'Self-Contained Breathing Apparatus (SCBA)','Identifies SCBA equipment, breathing-air connections, or a refill location.','scba'),
('DRY-HYD','c',(49,910,176,1035),'Dry Hydrant / Drafting Port','Identifies the location of a dry hydrant or drafting port.','red')]
def simplify(points,eps=.7):
 if len(points)<3:return points
 a,b=points[0],points[-1];dx=b[0]-a[0];dy=b[1]-a[1];den=math.hypot(dx,dy)
 distances=[abs(dy*(p[0]-a[0])-dx*(p[1]-a[1]))/den if den else math.hypot(p[0]-a[0],p[1]-a[1]) for p in points]
 idx=max(range(len(points)),key=lambda i:distances[i])
 if distances[idx]<=eps:return [a,b]
 return simplify(points[:idx+1],eps)[:-1]+simplify(points[idx:],eps)
def trace(mask):
 h=len(mask);w=len(mask[0]);edges={}
 def edge(a,b):edges.setdefault(a,[]).append(b)
 for y in range(h):
  for x in range(w):
   if not mask[y][x]:continue
   if y==0 or not mask[y-1][x]:edge((x,y),(x+1,y))
   if x==w-1 or not mask[y][x+1]:edge((x+1,y),(x+1,y+1))
   if y==h-1 or not mask[y+1][x]:edge((x+1,y+1),(x,y+1))
   if x==0 or not mask[y][x-1]:edge((x,y+1),(x,y))
 paths=[]
 while edges:
  start=next(iter(edges));p=start;pts=[p]
  while True:
   nxt=edges[p].pop()
   if not edges[p]:del edges[p]
   pts.append(nxt);p=nxt
   if p==start:break
  if len(pts)<5:continue
  mid=len(pts)//2;pts=simplify(pts[:mid+1])[:-1]+simplify(pts[mid:])
  paths.append('M'+' '.join(f'{x},{y}' for x,y in pts)+'Z')
 return ' '.join(paths)
catalog=[]
for code,page,box,title,application,style in rows:
 im=Image.open(files[page]).convert('L').crop(box);w,h=im.size
 dark=style in ['child','prohibition','scba']
 mask=[[((im.getpixel((x,y))<145) if dark else (im.getpixel((x,y))>165)) for x in range(w)] for y in range(h)]
 # Eliminate table borders; retain artwork reaching the sign edge.
 if dark:
  for y in range(h):
   for x in range(w):
    if x<2 or y<2 or x>=w-2 or y>=h-2:mask[y][x]=False
 bg={'blue':BLUE,'child':'#FFFFFF','prohibition':'#FFFFFF','scba':GREEN}.get(style,RED)
 fg=BLUE if style=='child' else '#000000' if style=='prohibition' else '#FFFFFF'
 shape='rectangular' if style=='scba' else 'circular' if style=='prohibition' else 'square'
 vh=150 if style=='scba' else 100
 path=trace(mask)
 art=f'<g transform="scale({100/w:.7f} {vh/h:.7f})"><path fill="{fg}" fill-rule="evenodd" d="{path}"/></g>'
 if style=='prohibition':
  # Recolor the actual traced prohibition marks, preserving the truck/octagon.
  redmask=[[mask[y][x] and (math.hypot((x-w/2)/w,(y-h/2)/h)>.35 or abs(x/w-y/h)<.075) for x in range(w)] for y in range(h)]
  blackmask=[[mask[y][x] and not redmask[y][x] for x in range(w)] for y in range(h)]
  art=f'<g transform="scale({100/w:.7f} {100/h:.7f})"><path fill="#000000" fill-rule="evenodd" d="{trace(blackmask)}"/><path fill="{RED}" fill-rule="evenodd" d="{trace(redmask)}"/></g>'
 if style=='child':art+=f'<path d="M1 1H99V99H1Z" fill="none" stroke="{BLUE}" stroke-width="1.5"/>'
 background=f'<circle cx="50" cy="50" r="50" fill="{bg}"/>' if shape=='circular' else f'<path fill="{bg}" d="M0 0H100V{vh}H0Z"/>'
 svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 {vh}" width="100" height="{vh}" role="img"><title>{html.escape(title)}</title><desc>{html.escape(application)}</desc>{background}{art}</svg>'
 filename=code.lower()+'.svg';(ROOT/'static/symbols'/filename).write_text(svg)
 characteristics={'field':shape,'background':bg,'foreground':fg}
 if style=='arrow':characteristics['backgroundRule']='Match accompanying sign'
 if code=='GAS':characteristics['letter']='Red G (negative space in white valve)'
 if style=='prohibition':characteristics.update(prohibition=RED,truck='#000000',outline='Black octagon')
 catalog.append(dict(code=code,title=title,application=application,characteristics=characteristics,sourcePage={'a':15,'b':16,'c':17}[page],asset=filename,svg=svg))
(ROOT/'static/symbols/catalog.json').write_text(json.dumps(catalog,indent=2))
# Inline the vector assets so the existing local server can serve the complete app.
p=ROOT/'static/app.js';s=p.read_text()
if s.startswith('// BEGIN GENERATED SYMBOLS'):
 s=s.split('// END GENERATED SYMBOLS\n',1)[1]
s='// BEGIN GENERATED SYMBOLS\nconst nfpaSymbols='+json.dumps(catalog,separators=(',',':'))+';\n// END GENERATED SYMBOLS\n'+s;p.write_text(s)
# Standalone review sheet, with inline SVGs, works without the server.
cards=''.join(f'<article>{r["svg"]}<h2>{html.escape(r["title"])}</h2><p>{html.escape(r["application"])}</p><small>Table 5.2 · page 170-{r["sourcePage"]} · {r["characteristics"]["field"]} field</small></article>' for r in catalog)
(ROOT/'static/symbols/review.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>NFPA 170 — 2024 symbol review</title><style>body{font:15px system-ui;margin:40px;color:#243c31;background:#f4f6f2}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px}article{background:white;padding:24px;border:1px solid #dae2d8;border-radius:8px}svg{height:130px;width:130px}h2{font-size:16px}p{line-height:1.5}small{color:#647268}</style><h1>NFPA 170 · 2024</h1><p>17 vector reproductions from supplied Table 5.2 screenshots. Colors follow the Characteristics column.</p><main>'+cards+'</main></html>')
print('Generated',len(catalog),'SVG symbols, metadata, and review sheet.')
