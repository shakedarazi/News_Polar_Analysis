async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function fmt(value, digits = 3) {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(digits);
}

async function loadFilters() {
  const sources = await fetchJson("/api/sources");
  const categories = await fetchJson("/api/categories");
  const sourceSel = document.getElementById("source");
  const categorySel = document.getElementById("category");

  sourceSel.innerHTML = '<option value="">הכל</option>' +
    sources.map(s => `<option value="${s.source}">${s.source} (${s.article_count})</option>`).join("");

  categorySel.innerHTML = '<option value="">הכל</option>' +
    categories.map(c => `<option value="${c.category}">${c.category} (${c.article_count})</option>`).join("");
}

async function loadArticles() {
  const params = new URLSearchParams();
  const source = document.getElementById("source").value;
  const category = document.getElementById("category").value;
  const minAudience = document.getElementById("minAudience").value;
  if (source) params.set("source", source);
  if (category) params.set("category", category);
  if (minAudience) params.set("min_audience_mean", minAudience);

  const articles = await fetchJson(`/api/articles?${params}`);
  const tbody = document.querySelector("#articlesTable tbody");
  tbody.innerHTML = articles.map(a => `
    <tr data-id="${a.article_id}">
      <td>${a.source}</td>
      <td>${a.title || ""}</td>
      <td>${a.primary_category || "—"}</td>
      <td>${a.num_comments ?? 0}</td>
      <td class="score">${fmt(a.audience_mean)}</td>
      <td>${fmt(a.audience_p85)}</td>
    </tr>
  `).join("");

  tbody.querySelectorAll("tr").forEach(row => {
    row.addEventListener("click", () => showDetail(row.dataset.id));
  });
}

async function showDetail(articleId) {
  const data = await fetchJson(`/api/articles/${articleId}`);
  document.querySelector("main table").hidden = true;
  const detail = document.getElementById("detail");
  detail.hidden = false;

  document.getElementById("detailTitle").textContent = data.title || "ללא כותרת";
  document.getElementById("detailMeta").innerHTML = `
    <span class="meta">${data.source} · ${data.primary_category || "ללא קטגוריה"} ·
    <a href="${data.canonical_url}" target="_blank" rel="noopener">לכתבה</a></span>
  `;

  const agg = data.aggregation;
  document.getElementById("detailAgg").innerHTML = agg ? `
    <p><strong>תגובות:</strong> ${agg.num_comments} |
    <strong>audience_mean:</strong> <span class="score">${fmt(agg.audience_mean)}</span> |
    <strong>p85:</strong> ${fmt(agg.audience_p85)} |
    <strong>controversy:</strong> ${fmt(agg.controversy_mean)}</p>
  ` : "<p>אין ניתוח פולריות עדיין</p>";

  document.getElementById("detailComments").innerHTML = (data.comments || []).map(c => `
    <li>
      <span class="score">polar ${fmt(c.polar_ratio)}</span>
      · לייקים ${c.like_count || 0}
      ${c.author ? `· ${c.author}` : ""}
      <div>${(c.text || "").slice(0, 280)}</div>
    </li>
  `).join("") || "<li>אין תגובות</li>";
}

function showList() {
  document.getElementById("detail").hidden = true;
  document.querySelector("main table").hidden = false;
}

document.getElementById("reload").addEventListener("click", loadArticles);
document.getElementById("back").addEventListener("click", showList);

loadFilters().then(loadArticles).catch(err => alert(err.message));
