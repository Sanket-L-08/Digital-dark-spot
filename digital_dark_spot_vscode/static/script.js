const sourcesEl = document.getElementById("sources");
const addSourceBtn = document.getElementById("addSource");
const analyzeBtn = document.getElementById("analyzeBtn");
const loadExampleBtn = document.getElementById("loadExample");
const clearBtn = document.getElementById("clearBtn");
const statusEl = document.getElementById("status");
const resultsEl = document.getElementById("results");

function sourceTemplate(index) {
  return `
    <div class="source-card">
      <div class="source-card-top">
        <strong>Source ${index}</strong>
        <button type="button" class="remove-source" aria-label="Remove source" title="Remove source">×</button>
      </div>
      <label>Source title</label>
      <input class="source-title" type="text" placeholder="e.g., Official scholarship guidelines">
      <label>Source URL (optional)</label>
      <input class="source-url" type="url" placeholder="https://example.org/guidelines">
      <label>Paste source text</label>
      <textarea class="source-content" rows="5" placeholder="Paste relevant text here. Include dates and requirements if available."></textarea>
    </div>`;
}

function refreshSourceLabels() {
  [...sourcesEl.querySelectorAll(".source-card")].forEach((card, i) => {
    card.querySelector(".source-card-top strong").textContent = `Source ${i + 1}`;
  });
}

addSourceBtn.addEventListener("click", () => {
  const count = sourcesEl.querySelectorAll(".source-card").length;
  sourcesEl.insertAdjacentHTML("beforeend", sourceTemplate(count + 1));
});

sourcesEl.addEventListener("click", (event) => {
  if (event.target.classList.contains("remove-source")) {
    const cards = sourcesEl.querySelectorAll(".source-card");
    if (cards.length === 1) {
      cards[0].querySelectorAll("input, textarea").forEach((field) => field.value = "");
    } else {
      event.target.closest(".source-card").remove();
      refreshSourceLabels();
    }
  }
});

function collectSources() {
  return [...sourcesEl.querySelectorAll(".source-card")].map((card) => ({
    title: card.querySelector(".source-title").value.trim(),
    url: card.querySelector(".source-url").value.trim(),
    content: card.querySelector(".source-content").value.trim()
  })).filter((source) => source.content);
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  }[char]));
}

function linkHTML(url, label = "Open source") {
  if (!url) return "";
  try {
    const parsed = new URL(url);
    if (!["http:", "https:"].includes(parsed.protocol)) return "";
    return `<p><a class="source-ref" href="${escapeHTML(parsed.href)}" target="_blank" rel="noopener noreferrer">${escapeHTML(label)} ↗</a></p>`;
  } catch {
    return "";
  }
}

function renderCards(targetId, items, type, emptyText, renderItem) {
  const target = document.getElementById(targetId);
  if (!items || !items.length) {
    target.innerHTML = `<div class="empty-state">${escapeHTML(emptyText)}</div>`;
    return;
  }
  target.innerHTML = items.map((item) => `<article class="result-card ${type}">${renderItem(item)}</article>`).join("");
}

function renderReport(data) {
  resultsEl.classList.remove("hidden");
  document.getElementById("summary").textContent = data.summary;
  document.getElementById("stats").innerHTML = `
    <div class="stat"><div class="stat-number">${data.source_count}</div><div class="stat-label">Sources reviewed</div></div>
    <div class="stat"><div class="stat-number">${data.gaps.length}</div><div class="stat-label">Potential gaps to review</div></div>
    <div class="stat"><div class="stat-number">${data.conflicts.length}</div><div class="stat-label">Possible conflicts</div></div>`;

  renderCards("gaps", data.gaps, "gap", "No gap flags were generated. Still review the source material for completeness.", (item) =>
    `<strong>${escapeHTML(item.title)}</strong><p>${escapeHTML(item.detail)}</p>`);

  renderCards("conflicts", data.conflicts, "conflict", "No possible conflicts were detected by the starter rules. This does not prove that the sources agree.", (item) =>
    `<strong>Possible conflict: ${escapeHTML(item.source_a)} vs ${escapeHTML(item.source_b)}</strong>
     <p><b>Source A:</b> ${escapeHTML(item.claim_a)}</p>${linkHTML(item.url_a, "View Source A")}
     <p><b>Source B:</b> ${escapeHTML(item.claim_b)}</p>${linkHTML(item.url_b, "View Source B")}
     <p class="source-ref">Shared terms: ${escapeHTML(item.shared_terms)}</p>`);

  renderCards("freshness", data.freshness, "freshness", "No freshness flags were generated. Check dates manually where they matter.", (item) =>
    `<strong>${escapeHTML(item.source)}</strong><p>${escapeHTML(item.message)}</p>${linkHTML(item.url)}`);

  document.getElementById("checklist").innerHTML = data.checklist.map((item) => `<li>${escapeHTML(item)}</li>`).join("");

  renderCards("sourceList", data.sources, "source", "No sources were returned.", (item) =>
    `<strong>${escapeHTML(item.title)}</strong><p>${item.word_count} words analyzed</p><p>${escapeHTML(item.excerpt)}</p>${linkHTML(item.url)}`);

  document.getElementById("methodNote").textContent = data.method_note;
  resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
}

analyzeBtn.addEventListener("click", async () => {
  statusEl.textContent = "";
  const question = document.getElementById("question").value.trim();
  const sources = collectSources();
  if (!question) {
    statusEl.textContent = "Enter a research question first.";
    return;
  }
  if (!sources.length) {
    statusEl.textContent = "Add at least one source and paste its text.";
    return;
  }
  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing…";
  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, sources })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Analysis failed.");
    renderReport(data);
  } catch (error) {
    statusEl.textContent = error.message || "Could not connect to the app. Is the Flask server running?";
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = 'Analyze sources <span>→</span>';
  }
});

loadExampleBtn.addEventListener("click", () => {
  document.getElementById("question").value = "What should I verify before applying for this scholarship? Check eligibility, deadline, required documents, and renewal conditions.";
  const example = [
    {
      title: "Scholarship information page",
      url: "https://example.org/scholarship",
      content: "Scholarship applications for the 2026 cycle must be submitted by 30 June 2026. Applicants must be enrolled full-time and provide an academic transcript and proof of enrollment. The official application form is available through the scholarship portal."
    },
    {
      title: "Scholarship applicant guide",
      url: "https://example.org/applicant-guide",
      content: "For the 2026 scholarship cycle, applicants must submit their application by 15 July 2026. Required documents include an academic transcript, proof of enrollment, and a personal statement. Applicants should check the official portal for updates."
    }
  ];
  sourcesEl.innerHTML = "";
  example.forEach((source, i) => {
    sourcesEl.insertAdjacentHTML("beforeend", sourceTemplate(i + 1));
    const card = sourcesEl.lastElementChild;
    card.querySelector(".source-title").value = source.title;
    card.querySelector(".source-url").value = source.url;
    card.querySelector(".source-content").value = source.content;
  });
  refreshSourceLabels();
  statusEl.textContent = "Example loaded. The source URLs are placeholders; the text is synthetic and for testing only.";
});

clearBtn.addEventListener("click", () => {
  document.getElementById("question").value = "";
  sourcesEl.innerHTML = sourceTemplate(1);
  statusEl.textContent = "";
  resultsEl.classList.add("hidden");
});
