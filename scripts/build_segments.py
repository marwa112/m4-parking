import json,re,math,collections,sys
from pyproj import Transformer
t=Transformer.from_crs("EPSG:3007","EPSG:4326",always_xy=True)
B=json.load(open("boende_all.json")); S=json.load(open("sop_all.json"))
def pts(g):
    c=g["coordinates"]
    if g["type"]=="LineString": return c
    if g["type"]=="MultiLineString": return [p for l in c for p in l]
    if g["type"]=="Polygon": return c[0]
    return [c]
def mid(p): return (sum(x for x,_ in p)/len(p), sum(y for _,y in p)/len(p))
def segdist(a,p):
    if len(p)==1: return math.hypot(p[0][0]-a[0],p[0][1]-a[1])
    best=1e9
    for (x1,y1),(x2,y2) in zip(p,p[1:]):
        dx,dy=x2-x1,y2-y1; L=dx*dx+dy*dy
        u=0 if L==0 else max(0,min(1,((a[0]-x1)*dx+(a[1]-y1)*dy)/L))
        best=min(best,math.hypot(x1+u*dx-a[0],y1+u*dy-a[1]))
    return best
sop=[]
for f in S["features"]:
    p=f["properties"]; g=[q[:2] for q in pts(f["geometry"])]
    txt=p["ActivePeriod"] or ""
    m=re.search(r"(\d{1,2})[.:](\d{2})\s*-\s*(\d{1,2})[.:](\d{2})",txt)
    sh,smin,eh,emin=(int(m.group(1)),int(m.group(2)),int(m.group(3)),int(m.group(4))) if m else (p["StartHour"],0,p["EndHour"],0)
    wd=-1 if p["WeekDay"] is None else p["WeekDay"]%7
    sop.append(dict(ltf=p["LtfRegulationNumber"],street=p["SiteName"],g=g,
      r=dict(wd=wd,sm=p["StartMonth"],sd=p["StartDay"],em=p["EndMonth"],ed=p["EndDay"],
             f=sh*60+smin,t=eh*60+emin,odd=p["OddWeeks"]=="Yes",even=p["EvenWeeks"]=="Yes",txt=txt)))
DAYS={"måndag":1,"tisdag":2,"onsdag":3,"torsdag":4,"fredag":5,"lördag":6,"söndag":0}
def parse_info(txt):
    m=re.search(r"(måndag|tisdag|onsdag|torsdag|fredag|lördag|söndag)\w*\s+klockan\s+(\d{1,2})[.:](\d{2})\s*-\s*(\d{1,2})[.:](\d{2})",txt.lower())
    if not m: return None
    odd="udda" in txt; even="jämna" in txt
    if not odd and not even: odd=even=True
    return dict(wd=DAYS[m.group(1)],sm=1,sd=1,em=12,ed=31,f=int(m.group(2))*60+int(m.group(3)),t=int(m.group(4))*60+int(m.group(5)),odd=odd,even=even,txt=txt)
out=[];nomatch=[]
for f in B["features"]:
    p=f["properties"]; code=p["ResidentialParking"] or ""
    if not code.startswith("M"): continue
    g=[q[:2] for q in pts(f["geometry"])]
    md=mid(g)
    cands=[s for s in sop if s["street"]==p["SiteName"] and segdist(md,s["g"])<4]
    same=[s for s in cands if s["ltf"]==p["LtfRegulationNumber"]]
    use=same or cands
    rules=[];seen=set()
    for s in use:
        k=json.dumps(s["r"],sort_keys=True)
        if k not in seen: seen.add(k); rules.append(s["r"])
    if not rules and p["ExtraInfo"]:
        r=parse_info(p["ExtraInfo"])
        if r: rules=[r]
        else: nomatch.append((p["SiteName"],code,p["ExtraInfo"]))
    mm=re.match(r"M(\d)(n?)",code)
    out.append(dict(s=p["SiteName"],c=code,taxa=int(mm.group(1)),n=bool(mm.group(2)),sp=int(p["ParkingSpaces"] or 0),
       g=[[round(v,6) for v in t.transform(x,y)][::-1] for x,y in g],cl=rules,info=p["ExtraInfo"] or "",ltf=p["LtfRegulationNumber"]))
print("segments",len(out),"with rules",sum(1 for o in out if o["cl"]),"info-but-no-rule",len(nomatch))
print(collections.Counter(len(o["cl"]) for o in out))
for n in nomatch[:5]: print("  ",n)
json.dump(out,open("m_segments.json","w"),ensure_ascii=False,separators=(",",":"))
