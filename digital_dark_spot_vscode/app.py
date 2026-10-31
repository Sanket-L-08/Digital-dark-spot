from flask import Flask, render_template, request, jsonify
from datetime import datetime
import re
from urllib.parse import urlparse

app = Flask(__name__)

STOPWORDS = {
    "the","a","an","and","or","but","if","then","is","are","was","were","be","been",
    "being","to","of","in","on","for","with","by","at","from","as","it","this","that",
    "these","those","what","when","where","why","how","who","which","should","can",
    "could","would","do","does","did","i","we","you","they","my","our","your","about",
    "before","after","into","through","than","also","not","have","has","had"
}

def words(text):
    return [w.lower() for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", text or "")
            if len(w) > 2 and w.lower() not in STOPWORDS]

def extract_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if len(s.strip()) > 20]

def source_label(source, index):
    title = (source.get("title") or "").strip()
    url = (source.get("url") or "").strip()
    return title or url or f"Source {index + 1}"

def analyze_research(payload):
    question = (payload.get("question") or "").strip()
    sources = payload.get("sources") or []
    usable = []
    for i, source in enumerate(sources):
        content = (source.get("content") or "").strip()
        if content:
            usable.append({
                "title": source_label(source, i),
                "url": (source.get("url") or "").strip(),
                "content": content,
                "index": i + 1
            })

    if not question:
        return {"error": "Please enter a research question or goal."}, 400
    if not usable:
        return {"error": "Add at least one source and paste its text before analyzing."}, 400

    all_text = "\n".join(s["content"] for s in usable)
    question_terms = list(dict.fromkeys(words(question)))
    combined_words = set(words(all_text))
    question_terms_found = [term for term in question_terms if term in combined_words]
    question_terms_missing = [term for term in question_terms if term not in combined_words]

    # A short, source-grounded excerpt for each source.
    source_summaries = []
    all_sentences = []
    for s in usable:
        sentences = extract_sentences(s["content"])
        source_summaries.append({
            "title": s["title"],
            "url": s["url"],
            "word_count": len(words(s["content"])),
            "excerpt": (sentences[0][:280] if sentences else s["content"][:280])
        })
        for sentence in sentences:
            all_sentences.append({
                "sentence": sentence,
                "source": s["title"],
                "url": s["url"],
                "terms": set(words(sentence))
            })

    # Conservative potential-conflict heuristic: sentences from different sources
    # share multiple meaningful terms but contain different numbers/dates/negation.
    conflicts = []
    seen = set()
    for i in range(len(all_sentences)):
        a = all_sentences[i]
        for j in range(i + 1, len(all_sentences)):
            b = all_sentences[j]
            if a["source"] == b["source"]:
                continue
            overlap = a["terms"] & b["terms"]
            if len(overlap) < 3:
                continue
            a_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", a["sentence"]))
            b_numbers = set(re.findall(r"\b\d+(?:[.,]\d+)?%?\b", b["sentence"]))
            a_neg = bool(re.search(r"\b(no|not|never|none|cannot|mustn't|ineligible|prohibited)\b", a["sentence"], re.I))
            b_neg = bool(re.search(r"\b(no|not|never|none|cannot|mustn't|ineligible|prohibited)\b", b["sentence"], re.I))
            differs = (a_numbers and b_numbers and a_numbers != b_numbers) or (a_neg != b_neg)
            key = tuple(sorted([a["sentence"], b["sentence"]]))
            if differs and key not in seen:
                seen.add(key)
                conflicts.append({
                    "claim_a": a["sentence"][:420], "source_a": a["source"], "url_a": a["url"],
                    "claim_b": b["sentence"][:420], "source_b": b["source"], "url_b": b["url"],
                    "shared_terms": ", ".join(sorted(overlap)[:6])
                })
            if len(conflicts) >= 5:
                break
        if len(conflicts) >= 5:
            break

    # Date/freshness hints. These are flags, not proof that a source is outdated.
    freshness = []
    date_patterns = [
        r"\b20\d{2}\b",
        r"\b(?:updated|published|last modified|effective from|valid until)\b.{0,45}"
    ]
    for s in usable:
        found = []
        for pattern in date_patterns:
            matches = re.findall(pattern, s["content"], re.I)
            found.extend(matches[:3])
        if not found:
            freshness.append({
                "source": s["title"], "url": s["url"],
                "message": "No obvious publication/update date was detected in the pasted text. Check the original page for date information."
            })
        else:
            years = [int(x) for x in re.findall(r"\b20\d{2}\b", s["content"])]
            old_years = [y for y in years if y < datetime.now().year - 2]
            if old_years:
                freshness.append({
                    "source": s["title"], "url": s["url"],
                    "message": f"Text contains year(s) {', '.join(map(str, sorted(set(old_years))))}. Confirm whether this information still applies."
                })

    gaps = []
    if question_terms_missing:
        gaps.append({
            "title": "Question terms not found in the provided text",
            "detail": "These terms from your question were not detected in the pasted sources: " +
                      ", ".join(question_terms_missing[:12]) + ". This is a clue for manual review, not proof that the information is absent."
        })
    else:
        gaps.append({
            "title": "Check whether the answer is complete",
            "detail": "The main terms in your question appear in the pasted text, but their presence does not guarantee that all required details are covered."
        })

    gap_prompts = [
        ("Deadline or date", r"\b(deadline|due date|by \w+ \d{1,2}|expires|closing date|application period)\b"),
        ("Eligibility or conditions", r"\b(eligib|criteria|qualif|condition|requirement)\w*\b"),
        ("Required documents", r"\b(document|certificate|proof|transcript|identification|ID)\w*\b"),
        ("Renewal or follow-up conditions", r"\b(renew|renewal|recurring|reapply|continuation)\w*\b"),
        ("Official application or action link", r"\b(apply|application form|submit|portal|official website)\b")
    ]
    corpus = all_text.lower()
    for label, pattern in gap_prompts:
        if re.search(pattern, question, re.I) and not re.search(pattern, corpus, re.I):
            gaps.append({
                "title": f"Possible gap: {label}",
                "detail": f"The question may involve {label.lower()}, but no matching terms were detected in the supplied text. Verify with an authoritative source."
            })

    checklist = []
    if question_terms_missing:
        checklist.append("Search the official source for the unresolved terms: " + ", ".join(question_terms_missing[:6]) + ".")
    if conflicts:
        checklist.append("Open both source references for each possible conflict and compare the exact context, date, and applicability.")
    if freshness:
        checklist.append("Check publication/update dates and confirm whether the information applies to the current period.")
    checklist.extend([
        "Identify the primary or official source for each critical requirement.",
        "Confirm important dates, eligibility conditions, required documents, and exceptions where relevant.",
        "Record any question that remains unanswered after reviewing the source material."
    ])
    # Preserve order and remove duplicates
    checklist = list(dict.fromkeys(checklist))[:6]

    summary = (
        f"Reviewed {len(usable)} source(s) containing approximately "
        f"{sum(s['word_count'] for s in source_summaries)} words. "
        f"Detected {len(conflicts)} possible cross-source conflict(s) and "
        f"{len(freshness)} source freshness flag(s). These are preliminary heuristic findings "
        f"and should be verified manually."
    )
    return {
        "question": question,
        "summary": summary,
        "source_count": len(usable),
        "sources": source_summaries,
        "gaps": gaps,
        "conflicts": conflicts,
        "freshness": freshness,
        "checklist": checklist,
        "method_note": "This starter version uses transparent text rules, not a trained AI model. A flagged gap means a term or pattern was not detected in the pasted material; it does not prove the information is absent. It does not automatically browse URLs."
    }, 200

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    result, status = analyze_research(data)
    return jsonify(result), status

if __name__ == "__main__":
    app.run(debug=True)
