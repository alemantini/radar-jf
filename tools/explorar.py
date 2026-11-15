import requests
for u in ["https://alemantini.github.io/radar-jf/", "https://alemantini.github.io/radar-jf/dados/resumo.json"]:
    r = requests.get(u, allow_redirects=False, timeout=30)
    print(u, r.status_code, r.headers.get("location"), r.headers.get("cache-control"))
