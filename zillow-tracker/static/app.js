const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const resultsContainer = document.getElementById("results");
const statusBar = document.getElementById("status-bar");
const demoBadge = document.getElementById("demo-badge");
const suggestionsEl = document.getElementById("suggestions");

let currentResults = [];
let currentSort = "pct_desc";
let currentSearchType = "area";
let allCities = [];

searchBtn.addEventListener("click", doSearch);
searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
        suggestionsEl.style.display = "none";
        doSearch();
    }
});

// City autocomplete
searchInput.addEventListener("input", () => {
    const val = searchInput.value.trim().toLowerCase();
    if (val.length < 2) {
        suggestionsEl.style.display = "none";
        return;
    }
    const matches = allCities.filter(c => c.toLowerCase().includes(val)).slice(0, 8);
    if (matches.length === 0) {
        suggestionsEl.style.display = "none";
        return;
    }
    suggestionsEl.innerHTML = matches.map(c =>
        `<div class="suggestion-item">${escapeHtml(c)}</div>`
    ).join("");
    suggestionsEl.style.display = "block";
});

suggestionsEl.addEventListener("click", (e) => {
    if (e.target.classList.contains("suggestion-item")) {
        searchInput.value = e.target.textContent;
        suggestionsEl.style.display = "none";
        doSearch();
    }
});

document.addEventListener("click", (e) => {
    if (!e.target.closest(".search-wrapper")) {
        suggestionsEl.style.display = "none";
    }
});

// Sort buttons
document.querySelectorAll(".sort-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".sort-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentSort = btn.dataset.sort;
        renderResults(sortResults(currentResults), currentSearchType);
    });
});

// Example address chips
document.addEventListener("click", (e) => {
    if (e.target.classList.contains("example-chip")) {
        searchInput.value = e.target.dataset.query;
        doSearch();
    }
});

// Modal close
document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("history-modal").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeModal();
});
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
});

async function doSearch() {
    const location = searchInput.value.trim();
    if (!location) return;

    searchBtn.disabled = true;
    searchBtn.textContent = "Searching...";
    resultsContainer.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Fetching properties for ${escapeHtml(location)}...</p>
        </div>`;
    statusBar.style.display = "none";

    try {
        const resp = await fetch(`/api/search?location=${encodeURIComponent(location)}`);
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        const data = await resp.json();

        demoBadge.style.display = data.demo_mode ? "inline-block" : "none";
        currentResults = data.results;
        currentSearchType = data.search_type || "area";
        statusBar.style.display = "flex";

        if (currentSearchType === "address") {
            document.getElementById("result-count").textContent =
                `Property found at "${data.query}"` +
                (data.result_count > 1 ? ` + ${data.result_count - 1} nearby` : "");
        } else {
            document.getElementById("result-count").textContent =
                `${data.result_count} properties found for "${data.query}"`;
        }

        renderResults(sortResults(currentResults), currentSearchType);
    } catch (err) {
        resultsContainer.innerHTML = `<div class="error-msg">Error: ${escapeHtml(err.message)}</div>`;
    } finally {
        searchBtn.disabled = false;
        searchBtn.textContent = "Search";
    }
}

function sortResults(results) {
    const sorted = [...results];
    switch (currentSort) {
        case "pct_desc":
            sorted.sort((a, b) => (b.price_increase_pct ?? -Infinity) - (a.price_increase_pct ?? -Infinity));
            break;
        case "pct_asc":
            sorted.sort((a, b) => (a.price_increase_pct ?? Infinity) - (b.price_increase_pct ?? Infinity));
            break;
        case "price_desc":
            sorted.sort((a, b) => b.property.current_price - a.property.current_price);
            break;
        case "price_asc":
            sorted.sort((a, b) => a.property.current_price - b.property.current_price);
            break;
        case "change_desc":
            sorted.sort((a, b) => (b.price_increase ?? -Infinity) - (a.price_increase ?? -Infinity));
            break;
    }
    return sorted;
}

function renderResults(results, searchType) {
    if (results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="empty-state">
                <h2>No properties found</h2>
                <p>Try a different address, city, or ZIP code.</p>
            </div>`;
        return;
    }

    if (searchType === "address" && results.length > 0) {
        // Show first result as a featured/primary card, rest as nearby
        const primary = results[0];
        const nearby = results.slice(1);

        let html = '<div class="address-results">';
        html += '<div class="primary-property">';
        html += '<h3 class="section-label">Searched Property</h3>';
        html += renderCard(primary, true);
        html += '</div>';

        if (nearby.length > 0) {
            html += '<div class="nearby-section">';
            html += `<h3 class="section-label">Nearby Properties (${nearby.length})</h3>`;
            html += '<div class="results-grid">' + nearby.map(item => renderCard(item, false)).join("") + '</div>';
            html += '</div>';
        }
        html += '</div>';

        resultsContainer.innerHTML = html;
    } else {
        resultsContainer.innerHTML = '<div class="results-grid">' +
            results.map(item => renderCard(item, false)).join("") + "</div>";
    }

    // Attach history button listeners
    resultsContainer.querySelectorAll(".history-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const zpid = btn.dataset.zpid;
            const address = btn.dataset.address;
            showPriceHistory(zpid, address);
        });
    });
}

function renderCard(item, isPrimary) {
    const p = item.property;
    const hasPrior = item.has_prior_sale;
    const pct = item.price_increase_pct;
    const increase = item.price_increase;
    const isPlaceholder = p.current_price === 0 && !hasPrior;

    let pctClass = "neutral";
    let pctText = "N/A";
    if (pct !== null && pct !== undefined) {
        pctClass = pct >= 0 ? "positive" : "negative";
        pctText = (pct >= 0 ? "+" : "") + pct.toFixed(1) + "%";
    }

    let changeClass = pct !== null && pct >= 0 ? "positive" : "negative";
    let changeHtml = "";
    if (hasPrior && increase !== null) {
        const arrow = increase >= 0 ? "&#9650;" : "&#9660;";
        changeHtml = `
            <div class="price-change ${changeClass}">
                <span>${arrow} ${formatCurrency(Math.abs(increase))}</span>
                <span>${pctText}</span>
            </div>`;
    }

    // Show a "no data" banner for placeholder properties (address found but no listing data)
    let placeholderHtml = "";
    if (isPlaceholder && isPrimary) {
        placeholderHtml = `<div class="placeholder-notice">Address found but no active listing data available. Nearby properties shown below.</div>`;
    }

    const imgHtml = p.image_url
        ? `<img src="${escapeHtml(p.image_url)}" alt="Property" loading="lazy">`
        : `<div class="no-image"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg><span>No image</span></div>`;

    const beds = p.bedrooms !== null ? `${p.bedrooms} bd` : "";
    const baths = p.bathrooms !== null ? `${p.bathrooms} ba` : "";
    const sqft = p.living_area !== null ? `${p.living_area.toLocaleString()} sqft` : "";
    const type = p.home_type ? p.home_type.replace(/_/g, " ").toLowerCase() : "";
    const details = [beds, baths, sqft, type].filter(Boolean).join(" &middot; ");

    const cardClass = isPrimary ? "property-card primary-card" : "property-card";

    return `
        <div class="${cardClass}">
            <div class="card-image">
                ${imgHtml}
                <span class="pct-badge ${pctClass}">${pctText}</span>
                ${isPrimary ? '<span class="primary-badge">Searched</span>' : ''}
            </div>
            <div class="card-body">
                <div class="card-address">${escapeHtml(p.address)}</div>
                <div class="card-location">${escapeHtml(p.city)}${p.state ? ", " + escapeHtml(p.state) : ""} ${escapeHtml(p.zipcode)}</div>
                ${placeholderHtml}
                ${!isPlaceholder ? `
                <div class="price-row">
                    <div class="current-price">${formatCurrency(p.current_price)}</div>
                    ${hasPrior ? `
                    <div class="prior-price">
                        <div class="label">Last sold${p.last_sold_date ? " " + escapeHtml(p.last_sold_date) : ""}</div>
                        <div class="value">${formatCurrency(p.last_sold_price)}</div>
                    </div>` : `
                    <div class="prior-price">
                        <div class="label">Prior sale</div>
                        <div class="value">N/A</div>
                    </div>`}
                </div>
                ${changeHtml}
                ${details ? `<div class="card-details"><span>${details}</span></div>` : ""}
                <button class="history-btn" data-zpid="${escapeHtml(p.zpid)}" data-address="${escapeHtml(p.address)}, ${escapeHtml(p.city)}">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                    Price History
                </button>` : ""}
            </div>
        </div>`;
}

// ---- Price History Modal ----

async function showPriceHistory(zpid, address) {
    const modal = document.getElementById("history-modal");
    document.getElementById("modal-title").textContent = `Price History - ${address}`;
    document.getElementById("history-tbody").innerHTML = `<tr><td colspan="3">Loading...</td></tr>`;
    document.getElementById("chart-container").innerHTML = '<canvas id="history-chart"></canvas>';
    modal.style.display = "flex";

    try {
        const resp = await fetch(`/api/history/${encodeURIComponent(zpid)}`);
        const data = await resp.json();
        const history = data.history || [];

        if (history.length === 0) {
            document.getElementById("history-tbody").innerHTML =
                `<tr><td colspan="3" class="no-data">No price history available yet. Check back after tracking for a few days.</td></tr>`;
            return;
        }

        renderHistoryTable(history);
        renderHistoryChart(history);
    } catch (err) {
        document.getElementById("history-tbody").innerHTML =
            `<tr><td colspan="3" class="error-msg">Failed to load history</td></tr>`;
    }
}

function renderHistoryTable(history) {
    const tbody = document.getElementById("history-tbody");
    let rows = "";
    for (let i = 0; i < history.length; i++) {
        const h = history[i];
        let changeHtml = "-";
        if (i > 0) {
            const prev = history[i - 1].price;
            const diff = h.price - prev;
            const pct = prev > 0 ? ((diff / prev) * 100).toFixed(1) : "0.0";
            const cls = diff >= 0 ? "positive" : "negative";
            const sign = diff >= 0 ? "+" : "";
            changeHtml = `<span class="${cls}">${sign}${formatCurrency(diff)} (${sign}${pct}%)</span>`;
        }
        rows += `<tr>
            <td>${escapeHtml(h.date)}</td>
            <td>${formatCurrency(h.price)}</td>
            <td>${changeHtml}</td>
        </tr>`;
    }
    tbody.innerHTML = rows;
}

function renderHistoryChart(history) {
    const canvas = document.getElementById("history-chart");
    const ctx = canvas.getContext("2d");
    const container = document.getElementById("chart-container");

    const dpr = window.devicePixelRatio || 1;
    const width = container.clientWidth;
    const height = 220;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = width + "px";
    canvas.style.height = height + "px";
    ctx.scale(dpr, dpr);

    if (history.length < 2) {
        ctx.fillStyle = "#8b8fa3";
        ctx.font = "14px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("Not enough data points for chart", width / 2, height / 2);
        return;
    }

    const prices = history.map(h => h.price);
    const minP = Math.min(...prices);
    const maxP = Math.max(...prices);
    const range = maxP - minP || 1;

    const padL = 70, padR = 20, padT = 20, padB = 40;
    const chartW = width - padL - padR;
    const chartH = height - padT - padB;

    // Background
    ctx.fillStyle = "#1a1d27";
    ctx.fillRect(0, 0, width, height);

    // Grid lines
    const gridLines = 5;
    ctx.strokeStyle = "#2a2e3d";
    ctx.lineWidth = 1;
    ctx.fillStyle = "#8b8fa3";
    ctx.font = "11px sans-serif";
    ctx.textAlign = "right";
    for (let i = 0; i <= gridLines; i++) {
        const y = padT + (chartH / gridLines) * i;
        const val = maxP - (range / gridLines) * i;
        ctx.beginPath();
        ctx.moveTo(padL, y);
        ctx.lineTo(width - padR, y);
        ctx.stroke();
        ctx.fillText(formatCurrencyShort(val), padL - 8, y + 4);
    }

    // X-axis labels
    ctx.textAlign = "center";
    const labelStep = Math.max(1, Math.floor(history.length / 6));
    for (let i = 0; i < history.length; i += labelStep) {
        const x = padL + (i / (history.length - 1)) * chartW;
        const date = history[i].date;
        const short = date.substring(0, 7); // YYYY-MM
        ctx.fillText(short, x, height - 8);
    }

    // Line
    const gradient = ctx.createLinearGradient(0, padT, 0, padT + chartH);
    const trending = prices[prices.length - 1] >= prices[0];
    if (trending) {
        gradient.addColorStop(0, "rgba(34, 197, 94, 0.3)");
        gradient.addColorStop(1, "rgba(34, 197, 94, 0.0)");
    } else {
        gradient.addColorStop(0, "rgba(239, 68, 68, 0.3)");
        gradient.addColorStop(1, "rgba(239, 68, 68, 0.0)");
    }

    // Area fill
    ctx.beginPath();
    for (let i = 0; i < history.length; i++) {
        const x = padL + (i / (history.length - 1)) * chartW;
        const y = padT + chartH - ((prices[i] - minP) / range) * chartH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.lineTo(padL + chartW, padT + chartH);
    ctx.lineTo(padL, padT + chartH);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();

    // Line stroke
    ctx.beginPath();
    for (let i = 0; i < history.length; i++) {
        const x = padL + (i / (history.length - 1)) * chartW;
        const y = padT + chartH - ((prices[i] - minP) / range) * chartH;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = trending ? "#22c55e" : "#ef4444";
    ctx.lineWidth = 2;
    ctx.stroke();

    // Dots on endpoints
    for (const idx of [0, history.length - 1]) {
        const x = padL + (idx / (history.length - 1)) * chartW;
        const y = padT + chartH - ((prices[idx] - minP) / range) * chartH;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, Math.PI * 2);
        ctx.fillStyle = trending ? "#22c55e" : "#ef4444";
        ctx.fill();
        ctx.strokeStyle = "#1a1d27";
        ctx.lineWidth = 2;
        ctx.stroke();
    }
}

function closeModal() {
    document.getElementById("history-modal").style.display = "none";
}

function formatCurrencyShort(n) {
    if (n >= 1_000_000) return "$" + (n / 1_000_000).toFixed(1) + "M";
    if (n >= 1_000) return "$" + (n / 1_000).toFixed(0) + "K";
    return "$" + Math.round(n);
}

function formatCurrency(n) {
    if (n === null || n === undefined) return "N/A";
    if (Math.abs(n) >= 1_000_000) return "$" + (n / 1_000_000).toFixed(2) + "M";
    if (Math.abs(n) >= 1_000) return "$" + (n / 1_000).toFixed(0) + "K";
    return "$" + n.toLocaleString();
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Load popular cities on startup
async function loadCities() {
    try {
        const resp = await fetch("/api/cities");
        const data = await resp.json();
        allCities = data.popular || [];

        // Render popular city buttons on the landing page
        const container = document.getElementById("popular-cities");
        if (container && allCities.length > 0) {
            const sample = allCities.slice(0, 12);
            container.innerHTML = `<p class="popular-label">Or browse by city:</p>` +
                sample.map(c => `<button class="city-chip">${escapeHtml(c)}</button>`).join("");
            container.querySelectorAll(".city-chip").forEach(btn => {
                btn.addEventListener("click", () => {
                    searchInput.value = btn.textContent;
                    doSearch();
                });
            });
        }
    } catch (e) {
        // ignore
    }
}

// Check health on load
fetch("/api/health").then(r => r.json()).then(data => {
    if (data.mode === "demo") {
        demoBadge.style.display = "inline-block";
    }
});

loadCities();
