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
ol=sorted({o[0] for o in oth}); oi={l:i for i,l in enumerate(ol)}
O=[[oi[o[0]],o[2]] for o in oth]
data={"olabels":ol,"other":O,"v":datetime.date.today().isoformat(),"streets":streets,"seg":S,"addr":A,"rnames":rn,"roads":R}
s=json.dumps(data,ensure_ascii=False,separators=(",",":"))
assert len(S)>300 and len(A)>1000 and len(R)>1000, "data looks incomplete, not publishing"
open("../docs/data.json","w").write(s)
print(len(S),len(A),len(R),len(s))
