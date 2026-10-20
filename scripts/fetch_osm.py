import json,urllib.request,time,sys
streets=set(json.load(open("m_streets.json")))
W,S,E,N=11.9400,57.6895,11.9945,57.7140
dx,dy=0.006,0.004
addr={};roads={}
skip={"footway","steps","path","cycleway","service","pedestrian","corridor","platform","track","bridleway","proposed","construction"}
x=W;n=0
while x<E:
    y=S
    while y<N:
        url=f"https://api.openstreetmap.org/api/0.6/map.json?bbox={x:.4f},{y:.4f},{min(x+dx,E):.4f},{min(y+dy,N):.4f}"
        for attempt in range(3):
            try:
                req=urllib.request.Request(url,headers={"User-Agent":"m4-parking-check/1.0 (+https://github.com/marwa112/m4-parking)"})
                j=json.load(urllib.request.urlopen(req,timeout=90));break
            except Exception as e:
                print("retry",url,e,file=sys.stderr);time.sleep(3)
        else: y+=dy;continue
        nodes={e["id"]:e for e in j["elements"] if e["type"]=="node"}
        for e in j["elements"]:
            t=e.get("tags",{})
            if t.get("addr:street") in streets and "addr:housenumber" in t:
                if e["type"]=="node": lat,lon=e["lat"],e["lon"]
                elif e["type"]=="way":
                    ps=[nodes[i] for i in e["nodes"] if i in nodes]
                    if not ps: continue
                    lat=sum(p["lat"] for p in ps)/len(ps); lon=sum(p["lon"] for p in ps)/len(ps)
                else: continue
                addr[f'{e["type"]}{e["id"]}']=[t["addr:street"],t["addr:housenumber"],round(lat,6),round(lon,6)]
            if e["type"]=="way" and "highway" in t and t["highway"] not in skip:
                ps=[nodes[i] for i in e["nodes"] if i in nodes]
                if len(ps)>=2:
                    k=e["id"]; g=[[round(p["lat"],5),round(p["lon"],5)] for p in ps]
                    if k not in roads or len(g)>len(roads[k]["g"]): roads[k]={"n":t.get("name",""),"h":t["highway"],"g":g}
        n+=1;print(n,len(addr),len(roads),file=sys.stderr);time.sleep(1)
        y+=dy
    x+=dx
json.dump(list(addr.values()),open("m_addr.json","w"),ensure_ascii=False)
json.dump(list(roads.values()),open("m_roads.json","w"),ensure_ascii=False,separators=(",",":"))
print("addresses",len(addr),"roads",len(roads))
