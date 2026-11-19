import re, requests, urllib.parse as U
UA={"User-Agent":"RadarJF/1.0 (robo de transparencia; codigo aberto em https://github.com/alemantini/radar-jf)"}
B="https://www.camarajf.mg.gov.br/transparencia/"
vistos=set()
def links(url):
    try: r=requests.get(url,headers=UA,timeout=40)
    except Exception as e: print("ERRO",url,e); return []
    print("==",r.status_code,url,len(r.text))
    out=[]
    for h,t in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>',r.text,re.S):
        t=re.sub(r"<[^>]+>|\s+"," ",t).strip()
        out.append((U.urljoin(url,h),t))
    return out,r.text
res=links(B)
L,html=res
for u,t in L: print("  ",t[:70],"|",u)
KW=re.compile(r"gabin|combust|despes|verba|di[aá]ri|ve[ií]cul|abastec|custeio|contrat|empenho|pagament|frota",re.I)
for u,t in L:
    if KW.search(t+u) and u.startswith("https://www.camarajf") and u not in vistos:
        vistos.add(u)
        r=links(u)
        if not r: continue
        L2,h2=r
        txt=re.sub(r"<[^>]+>"," ",h2); txt=re.sub(r"\s+"," ",txt)
        print("   TXT:",txt[:600])
        for u2,t2 in L2:
            if KW.search(t2+u2) or "php?" in u2: print("     ->",t2[:60],"|",u2)
        for m in re.finditer(r"(?i)combust\w*.{0,200}",txt): print("     COMB:",m.group(0)[:200]); break
