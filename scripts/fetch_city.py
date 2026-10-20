"""Download residential parking (boende) and street cleaning (sopzoner) from Göteborg's open WFS."""
import json, time, urllib.request
BASE = "https://open.geodata.tkgbg.se/wfs?service=WFS&version=2.0.0&request=GetFeature&outputFormat=application/json&typeNames="
def get(layer):
    for attempt in range(5):
        try:
            return json.load(urllib.request.urlopen(BASE + layer, timeout=180))
        except Exception as e:
            print(layer, "retry", e); time.sleep(5 * (attempt + 1))
    raise SystemExit(f"Could not download {layer}")
b = get("parkering:boende"); json.dump(b, open("boende_all.json", "w"), ensure_ascii=False)
s = get("parkering:sopzoner"); json.dump(s, open("sop_all.json", "w"), ensure_ascii=False)
streets = sorted({f["properties"]["SiteName"] for f in b["features"] if (f["properties"].get("ResidentialParking") or "").startswith("M")})
json.dump(streets, open("m_streets.json", "w"), ensure_ascii=False)
print("boende", len(b["features"]), "sopzoner", len(s["features"]), "M streets", len(streets))
