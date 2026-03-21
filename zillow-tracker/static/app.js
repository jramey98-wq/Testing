const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const resultsContainer = document.getElementById("results");
const statusBar = document.getElementById("status-bar");
const demoBadge = document.getElementById("demo-badge");

let currentResults = [];
let currentSort = "pct_desc";

searchBtn.addEventListener("click", doSearch);
searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doSearch();
});

// Sort buttons
document.querySelectorAll(".sort-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".sort-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentSort = btn.dataset.sort;
        renderResults(sortResults(currentResults));
    });
});

async function doSearch() {
    const location = searchInput.value.trim();
    if (!location) return;

    searchBtn.disabled = true;
    searchBtn.textContent = "Searching...";
    resultsContainer.innerHTML = `
        <div class="loading">
            <div class="spinner"></div>
            <p>Fetching properties in ${escapeHtml(location)}...</p>
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
        statusBar.style.display = "flex";
        document.getElementById("result-count").textContent =
            `${data.result_count} properties found for "${data.query}"`;

        renderResults(sortResults(currentResults));
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

function renderResults(results) {
    if (results.length === 0) {
        resultsContainer.innerHTML = `
            <div class="empty-state">
                <h2>No properties found</h2>
                <p>Try a different city or ZIP code.</p>
            </div>`;
        return;
    }

    resultsContainer.innerHTML = '<div class="results-grid">' +
        results.map(renderCard).join("") + "</div>";
}

function renderCard(item) {
    const p = item.property;
    const hasPrior = item.has_prior_sale;
    const pct = item.price_increase_pct;
    const increase = item.price_increase;

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

    const imgHtml = p.image_url
        ? `<img src="${escapeHtml(p.image_url)}" alt="Property" loading="lazy">`
        : `<div class="no-image"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg><span>No image</span></div>`;

    const beds = p.bedrooms !== null ? `${p.bedrooms} bd` : "";
    const baths = p.bathrooms !== null ? `${p.bathrooms} ba` : "";
    const sqft = p.living_area !== null ? `${p.living_area.toLocaleString()} sqft` : "";
    const type = p.home_type ? p.home_type.replace(/_/g, " ").toLowerCase() : "";
    const details = [beds, baths, sqft, type].filter(Boolean).join(" &middot; ");

    return `
        <div class="property-card">
            <div class="card-image">
                ${imgHtml}
                <span class="pct-badge ${pctClass}">${pctText}</span>
            </div>
            <div class="card-body">
                <div class="card-address">${escapeHtml(p.address)}</div>
                <div class="card-location">${escapeHtml(p.city)}, ${escapeHtml(p.state)} ${escapeHtml(p.zipcode)}</div>
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
            </div>
        </div>`;
}

function formatCurrency(n) {
    if (n === null || n === undefined) return "N/A";
    if (n >= 1_000_000) return "$" + (n / 1_000_000).toFixed(2) + "M";
    if (n >= 1_000) return "$" + (n / 1_000).toFixed(0) + "K";
    return "$" + n.toLocaleString();
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// Check health on load
fetch("/api/health").then(r => r.json()).then(data => {
    if (data.mode === "demo") {
        demoBadge.style.display = "inline-block";
    }
});
