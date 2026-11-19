"""Adapters of stage E4 (doc/DATA_SOURCES.md, odstavec 4.3): the news of ministries,
authorities and agencies. Each adapter is `function(entry, session, since, context)`
like those of harvest_adapters.py.

Most feeds are read by harvest_standards.rss_items, which keeps the items whose title
or description has a basic search term (tier 1). The feeds of authorities whose own
agenda is a broader area of the database — dangerous goods by rail (OTIF, the Czech
Rail Authority), pressure and gas equipment (SÚIP) — also keep the items with a broader
term (tier 2), rss_items_broader; elsewhere a broader term would let through most of
the authority's own news (as "metrologie" does at ÚNMZ).

* ehsp_documents — the documents of the European Hydrogen Safety Panel from the
  WordPress REST API of ehsp.eu (its RSS feed has a single item).
* du_rid_page — the page of the Czech Rail Authority on RID: a finding when the page
  changed since the last applied run (`modified`); the first run only sets the baseline.
"""
import hashlib
import html
import re

from harvest import Finding

EHSP_PER_PAGE = 100
# The media library of ehsp.eu also holds the members' profiles ("<name> Web") and calls; kept are the
# documents that name hydrogen or are plainly expert material.
EHSP_DOCUMENT = re.compile(r"\b(safety|guidance|guideline|report|recommendation|statistics|lessons|RCS|HIAD|"
                           r"factsheet|position|assessment|incident)\b", re.IGNORECASE)


def rss_items_broader(entry, session, since, context):
    import harvest_standards as st
    return st.rss_items(entry, session, since, context, broader=True)


def _title(rendered):
    text = html.unescape(re.sub(r"<[^>]+>", " ", rendered or ""))
    return " ".join(text.replace("_", " ").split())


def ehsp_documents(entry, session, since, context):
    import harvest
    endpoint = re.sub(r"per_page=\d+", f"per_page={EHSP_PER_PAGE}", entry["access"]["endpoint"])
    response = session.get(endpoint, timeout=60)
    response.raise_for_status()
    total = int(response.headers.get("X-WP-Total") or 0)
    media = response.json()
    if total > len(media):
        raise RuntimeError(f"{total} documents, only {len(media)} read")
    findings = []
    for item in media:
        url = item.get("source_url")
        if not url:
            continue
        title = _title(item.get("title", {}).get("rendered"))
        if title.endswith(" Web") or not (harvest.matches(title) or EHSP_DOCUMENT.search(title)):
            continue
        findings.append(Finding(entry["id"], "new_document", title, url=url, native_id=str(item.get("id")),
                                tier=1 if harvest.matches(title) else 2, date=(item.get("date") or "")[:10] or None,
                                language="EN", jurisdikce="EU", document_type="Metodika",
                                excerpt=f"European Hydrogen Safety Panel, nahráno {(item.get('date') or '')[:10]}"))
    return findings


def du_rid_page(entry, session, since, context):
    response = session.get(entry["access"]["endpoint"], timeout=60)
    response.raise_for_status()
    page = response.json()
    modified = page.get("modified") or page.get("modified_gmt")
    if not modified or since is None or modified[:19] <= since[:19]:
        return []  # no change since the last applied run (or the baseline of the first one)
    title = _title(page.get("title", {}).get("rendered")) or "RID"
    key = f"{entry['id']}:page-{page.get('id')}:{hashlib.sha256(modified.encode()).hexdigest()[:8]}"
    return [Finding(entry["id"], "new_document", f"Drážní úřad: změna stránky „{title}“ ({modified[:10]})",
                    key=None, native_id=key.split(":", 1)[1], url=page.get("link"), tier=2, date=modified[:10],
                    language="CS", jurisdikce="CZ",
                    excerpt=f"Stránka byla změněna {modified[:10]}; zkontrolovat, zda nepřináší nové znění RID "
                            f"nebo metodický pokyn.")]
