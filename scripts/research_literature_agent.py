#!/usr/bin/env python3
"""Public-literature-only PubMed weekly research digest. No LLM or patient data."""
import datetime as dt
import html
import json
import os
import pathlib
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "literature_digest.json"
TOPICS = {
 "Lymphoma pathology": '("lymphoma"[Title/Abstract]) AND (classification OR molecular OR pathology OR diagnosis)',
 "MDS microenvironment": '("myelodysplastic"[Title/Abstract] OR "MDS"[Title/Abstract]) AND (microenvironment OR macrophage OR spatial OR inflammation)',
 "Optical genome mapping": '("optical genome mapping"[Title/Abstract] OR "optical mapping"[Title/Abstract]) AND (leukemia OR myeloid OR hematologic)',
 "AML molecular pathology": '("acute myeloid leukemia"[Title/Abstract] OR AML[Title/Abstract]) AND (RUNX1 OR SRSF2 OR "trisomy 13" OR molecular)',
 "Transfusion medicine": '("transfusion"[Title/Abstract] OR "IVIG"[Title/Abstract]) AND (reaction OR platelet OR safety OR immunoglobulin)'
}
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
def request(endpoint, params):
    params = dict(params)
    params.update({"tool":"HemeResearchLiteratureAgent","email":os.environ.get("NCBI_EMAIL","research@example.org")})
    url=BASE+endpoint+"?"+urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"HemeResearchLiteratureAgent/1.0"}),timeout=35) as r:
        return r.read()
def node_text(node):
    return " ".join("".join(node.itertext()).split()) if node is not None else ""
def main():
    today=dt.date.today()
    start=today-dt.timedelta(days=int(os.environ.get("LOOKBACK_DAYS","10")))
    results={}
    for topic, query in TOPICS.items():
        xml=ET.fromstring(request("esearch.fcgi",{"db":"pubmed","term":query,"retmax":"25","retmode":"xml","datetype":"edat","mindate":start.isoformat(),"maxdate":today.isoformat(),"sort":"pub date"}))
        ids=[n.text for n in xml.findall("./IdList/Id") if n.text]
        time.sleep(.4)
        papers=[]
        if ids:
            records=ET.fromstring(request("efetch.fcgi",{"db":"pubmed","id":",".join(ids),"retmode":"xml"}))
            for article in records.findall(".//PubmedArticle"):
                pmid=node_text(article.find("./MedlineCitation/PMID"))
                if not pmid: continue
                title=node_text(article.find("./MedlineCitation/Article/ArticleTitle"))
                journal=node_text(article.find("./MedlineCitation/Article/Journal/Title"))
                abstract=node_text(article.find("./MedlineCitation/Article/Abstract"))
                doi=""
                for identifier in article.findall("./PubmedData/ArticleIdList/ArticleId"):
                    if identifier.attrib.get("IdType")=="doi": doi=node_text(identifier); break
                papers.append({"pmid":pmid,"title":title,"journal":journal,"doi":doi,"abstract":abstract[:2000],"url":"https://pubmed.ncbi.nlm.nih.gov/"+urllib.parse.quote(pmid)+"/"})
        results[topic]=papers
        time.sleep(.4)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"window_start":start.isoformat(),"window_end":today.isoformat(),"topics":results},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Wrote",OUT,"papers",sum(map(len,results.values())))
if __name__=="__main__": main()
