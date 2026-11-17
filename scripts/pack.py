import json,datetime,re
seg=json.load(open("m_segments.json")); addr=json.load(open("m_addr.json")); roads=json.load(open("m_roads.json"))
streets=sorted({s["s"] for s in seg}); si={s:i for i,s in enumerate(streets)}
S=[[si[s["s"]],s["taxa"],1 if s["n"] else 0,s["sp"],[[round(a,5),round(b,5)] for a,b in s["g"]],
    [[r["wd"],r["sm"],r["sd"],r["em"],r["ed"],r["f"],r["t"],1 if r["odd"] else 0,1 if r["even"] else 0] for r in s["cl"]]] for s in seg]
A=[]
for st,hn,lat,lon in addr:
    for part in re.split(r"[,;]",hn):
        part=part.strip()
        m=re.match(r"^(\d+)\s*([A-Za-z]?)",part)
        if m: A.append([si[st],int(m.group(1)),m.group(2).upper(),round(lat,5),round(lon,5)])
rn=sorted({r["n"] for r in roads}); ri={n:i for i,n in enumerate(rn)}
major={"primary":3,"secondary":3,"tertiary":2,"trunk":3}
R=[[ri[r["n"]],major.get(r["h"],1),r["g"]] for r in roads]
oth=json.load(open("other_parking.json"))

# --- Paid parking under each M section ("pay instead of moving") ---------------------------
# Parkering Göteborg platskoder for the city's street taxa: Taxa 1 -> 801 ... Taxa 8 -> 800, Taxa A -> 808,
# two-digit taxa -> 8xx. The sign on the street always governs; the app tells the user to check it.
import math
def platskod(name):
    m=re.match(r"Taxa\s*(\w+)$",name.strip(),re.I)
    if not m: return ""
    t=m.group(1).upper()
    if t=="A": return "808"
    if not t.isdigit(): return ""
    n=int(t)
    return "800" if n==8 else (f"80{n}" if n<10 else f"8{n}")
def _xy(lat,lon,lat0,lon0): return ((lon-lon0)*math.radians(1)*6371000*math.cos(math.radians(lat0)),(lat-lat0)*math.radians(1)*6371000)
def _dist(p,g):
    pts=[_xy(a,b,p[0],p[1]) for a,b in g]
    if len(pts)==1: return math.hypot(*pts[0])
    best=1e9
    for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
        dx,dy=x2-x1,y2-y1;L=dx*dx+dy*dy;u=0 if L==0 else max(0,min(1,(-x1*dx-y1*dy)/L))
        best=min(best,math.hypot(x1+u*dx,y1+u*dy))
    return best
paid=[];paid_i={}
taxa=[o for o in oth if o[0].startswith("Taxa") and len(o)>3 and o[3]]
by_street={}
for o in taxa: by_street.setdefault(o[1],[]).append(o)
for s_in,s_out in zip(seg,S):
    g=s_in["g"];probe=[g[0],g[len(g)//2],g[-1]] if len(g)>2 else g
    best=None
    for o in by_street.get(s_in["s"],[]):
        d=min(_dist(pt,o[2]) for pt in probe)
        if d<4 and (best is None or d<best[0]): best=(d,o)
    idx=-1
    if best:
        o=best[1];row=[o[0],platskod(o[0]),o[3][0],o[3][1],o[3][2]]
        k=json.dumps(row,ensure_ascii=False)
        if k not in paid_i: paid_i[k]=len(paid);paid.append(row)
        idx=paid_i[k]
    s_out.append(idx)
print("M sections with paid parking underneath:",sum(1 for x in S if x[6]>=0),"of",len(S),"| paid regimes:",len(paid))
ol=sorted({o[0] for o in oth}); oi={l:i for i,l in enumerate(ol)}
O=[[oi[o[0]],o[2]] for o in oth]
data={"paid":paid,"olabels":ol,"other":O,"v":datetime.date.today().isoformat(),"streets":streets,"seg":S,"addr":A,"rnames":rn,"roads":R}
s=json.dumps(data,ensure_ascii=False,separators=(",",":"))
assert len(S)>300 and len(A)>1000 and len(R)>1000, "data looks incomplete, not publishing"
open("../docs/data.json","w").write(s)
print(len(S),len(A),len(R),len(s))
