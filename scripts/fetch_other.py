import json,urllib.request,collections
from pyproj import Transformer
t=Transformer.from_crs("EPSG:3007","EPSG:4326",always_xy=True)
layers=["taxa_1","taxa_2","taxa_3","taxa_4","taxa_5","taxa_6","taxa_7","taxa_8","Taxa_9","Taxa_12","taxa_22","taxa_24","Taxa_62","taxa_a","tidsbegransad","lastplats","handikapp","mc","pbolaget","privat"]
W,S,E,N=11.936,57.687,11.998,57.716
out=[];cnt=collections.Counter()
import time
for L in layers:
    url=f"https://open.geodata.tkgbg.se/wfs?service=WFS&version=2.0.0&request=GetFeature&outputFormat=application/json&typeNames=parkering:{L}"
    d=None
    for a in range(4):
        try: d=json.load(urllib.request.urlopen(url,timeout=180)); break
        except Exception as e: print(L,"retry",e); import time; time.sleep(4)
    if d is None: print(L,"FAILED"); continue
    for f in d["features"]:
        g=f["geometry"]
        if not g: continue
        c=g["coordinates"]
        pts=c if g["type"]=="LineString" else (c[0] if g["type"]=="Polygon" else ([p for l in c for p in l] if g["type"]=="MultiLineString" else [c]))
        ll=[t.transform(p[0],p[1])[::-1] for p in pts]
        if not any(S<a<N and W<b<E for a,b in ll): continue
        p=f["properties"]
        if L=="lastplats": lab="Loading zone"
        elif L=="handikapp": lab="Disabled permit"
        elif L=="mc": lab="Motorcycle"
        elif L=="tidsbegransad": lab="Time limited"+(f' {p.get("MaxParkingTime")}' if p.get("MaxParkingTime") else "")
        elif L in("pbolaget","privat"): lab="Parking company"
        else: lab=(p.get("ParkingCharge") or L.replace("_"," ").title())
        out.append([lab,p.get("SiteName") or "",[[round(a,5),round(b,5)] for a,b in ll]]); cnt[L]+=1
print(cnt); json.dump(out,open("other_parking.json","w"),ensure_ascii=False,separators=(",",":"))
print(len(out))
