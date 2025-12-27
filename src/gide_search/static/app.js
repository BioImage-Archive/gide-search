// GIDE Search Frontend

const PAGE_SIZE = 20;

// Current search state
const state = {
    query: '',
    sources: [],
    organisms: [],
    methods: [],
    yearFrom: null,
    yearTo: null,
    offset: 0,
};

// DOM Elements
const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const resultsCount = document.getElementById('results-count');
const resultsList = document.getElementById('results-list');
const pagination = document.getElementById('pagination');
const clearFiltersBtn = document.getElementById('clear-filters');

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadStateFromURL();
    setupFilterToggles();
    performSearch();

    searchForm.addEventListener('submit', handleSearch);
    clearFiltersBtn.addEventListener('click', clearFilters);
    window.addEventListener('popstate', () => {
        loadStateFromURL();
        performSearch();
    });
});

function setupFilterToggles() {
    document.querySelectorAll('.filter-toggle').forEach(toggle => {
        toggle.addEventListener('click', () => {
            const section = toggle.closest('.filter-section');
            const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
            toggle.setAttribute('aria-expanded', !isExpanded);
            section.setAttribute('aria-expanded', !isExpanded);
        });
    });
}

function loadStateFromURL() {
    const params = new URLSearchParams(window.location.search);
    state.query = params.get('q') || '';
    state.sources = params.getAll('source');
    state.organisms = params.getAll('organism');
    state.methods = params.getAll('imaging_method');
    state.yearFrom = params.get('year_from') ? parseInt(params.get('year_from')) : null;
    state.yearTo = params.get('year_to') ? parseInt(params.get('year_to')) : null;
    state.offset = params.get('offset') ? parseInt(params.get('offset')) : 0;

    searchInput.value = state.query;
}

function updateURL() {
    const params = new URLSearchParams();
    if (state.query) params.set('q', state.query);
    state.sources.forEach(s => params.append('source', s));
    state.organisms.forEach(o => params.append('organism', o));
    state.methods.forEach(m => params.append('imaging_method', m));
    if (state.yearFrom) params.set('year_from', state.yearFrom);
    if (state.yearTo) params.set('year_to', state.yearTo);
    if (state.offset > 0) params.set('offset', state.offset);

    const newURL = params.toString() ? `?${params.toString()}` : window.location.pathname;
    history.pushState(null, '', newURL);
}

function handleSearch(e) {
    e.preventDefault();
    state.query = searchInput.value;
    state.offset = 0;
    updateURL();
    performSearch();
}

async function performSearch() {
    const params = new URLSearchParams();
    if (state.query) params.set('q', state.query);
    state.sources.forEach(s => params.append('source', s));
    state.organisms.forEach(o => params.append('organism', o));
    state.methods.forEach(m => params.append('imaging_method', m));
    if (state.yearFrom) params.set('year_from', state.yearFrom);
    if (state.yearTo) params.set('year_to', state.yearTo);
    params.set('size', PAGE_SIZE);
    params.set('offset', state.offset);

    resultsList.innerHTML = `
        <div class="loading">
            <div class="loading-spinner"></div>
            <p>Searching...</p>
        </div>
    `;

    try {
        const response = await fetch(`/search?${params.toString()}`);
        if (!response.ok) throw new Error('Search failed');
        const data = await response.json();
        renderResults(data);
        renderFacets(data.facets);
        renderPagination(data.total);
    } catch (error) {
        resultsList.innerHTML = `
            <div class="error-message">
                <p>Error: ${escapeHtml(error.message)}</p>
                <p>Please try again or check if the server is running.</p>
            </div>
        `;
    }
}

function renderResults(data) {
    const start = state.offset + 1;
    const end = Math.min(state.offset + PAGE_SIZE, data.total);
    resultsCount.textContent = `${start} - ${end} of ${data.total.toLocaleString()} results`;

    if (data.hits.length === 0) {
        resultsList.innerHTML = `
            <div class="empty-state">
                <p>No studies found matching your search.</p>
                <p>Try adjusting your search terms or filters.</p>
            </div>
        `;
        return;
    }

    resultsList.innerHTML = data.hits.map(hit => renderStudyCard(hit)).join('');
}

function renderStudyCard(hit) {
    const sourceClass = hit.source.toLowerCase();
    const organisms = hit.organisms.slice(0, 3);
    const methods = hit.imaging_methods.slice(0, 3);

    return `
        <article class="study-card">
            <div class="study-card-header">
                <span class="source-badge ${sourceClass}">${escapeHtml(hit.source)}</span>
                <div class="study-card-title">
                    <h3>
                        <a href="${escapeHtml(hit.source_url)}" target="_blank" rel="noopener">
                            ${escapeHtml(hit.title)}
                        </a>
                    </h3>
                    <svg class="external-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                        <polyline points="15 3 21 3 21 9"/>
                        <line x1="10" y1="14" x2="21" y2="3"/>
                    </svg>
                </div>
            </div>
            <p class="study-description">${escapeHtml(hit.description)}</p>
            <div class="study-meta">
                ${hit.release_date ? `
                    <span class="study-meta-item">
                        <span class="study-meta-label">Release date:</span>
                        ${escapeHtml(hit.release_date)}
                    </span>
                ` : ''}
                ${methods.length > 0 ? `
                    <span class="study-meta-item">
                        <span class="study-meta-label">Imaging method:</span>
                        ${escapeHtml(methods.join(', '))}${hit.imaging_methods.length > 3 ? '...' : ''}
                    </span>
                ` : ''}
                ${organisms.length > 0 ? `
                    <span class="study-meta-item">
                        <span class="study-meta-label">Organism:</span>
                        ${escapeHtml(organisms.join(', '))}${hit.organisms.length > 3 ? '...' : ''}
                    </span>
                ` : ''}
            </div>
            ${(organisms.length > 0 || methods.length > 0) ? `
                <div class="study-tags">
                    ${organisms.map(o => `<span class="tag organism">${escapeHtml(o)}</span>`).join('')}
                    ${methods.map(m => `<span class="tag method">${escapeHtml(m)}</span>`).join('')}
                </div>
            ` : ''}
        </article>
    `;
}

function renderFacets(facets) {
    renderFacetGroup('facet-sources', facets.sources, 'source', state.sources, 'sources-count');
    renderFacetGroup('facet-organisms', facets.organisms, 'organism', state.organisms, 'organisms-count');
    renderFacetGroup('facet-methods', facets.imaging_methods, 'method', state.methods, 'methods-count');
    renderYearFacet('facet-years', facets.years, 'years-count');
}

function renderFacetGroup(containerId, buckets, type, selected, countId) {
    const container = document.getElementById(containerId);
    const countEl = document.getElementById(countId);

    if (countEl) {
        countEl.textContent = buckets.length > 0 ? buckets.length : '';
    }

    if (buckets.length === 0) {
        container.innerHTML = '<p class="empty-state" style="padding: 0.5rem 0; font-size: 0.875rem;">No options available</p>';
        return;
    }

    const maxItems = 10;
    const displayBuckets = buckets.slice(0, maxItems);

    container.innerHTML = displayBuckets.map(bucket => {
        const isChecked = selected.includes(bucket.key);
        const id = `${type}-${bucket.key.replace(/[^a-zA-Z0-9]/g, '-')}`;
        return `
            <label class="filter-option">
                <input type="checkbox" id="${escapeHtml(id)}"
                       ${isChecked ? 'checked' : ''}
                       onchange="toggleFacet('${type}', '${escapeHtml(bucket.key.replace(/'/g, "\\'"))}')">
                <span class="filter-option-label" title="${escapeHtml(bucket.key)}">${escapeHtml(bucket.key)}</span>
                <span class="filter-option-count">${bucket.count}</span>
            </label>
        `;
    }).join('');

    if (buckets.length > maxItems) {
        container.innerHTML += `<p style="padding: 0.5rem 0; font-size: 0.75rem; color: var(--text-muted);">${buckets.length - maxItems} more...</p>`;
    }
}

function renderYearFacet(containerId, buckets, countId) {
    const container = document.getElementById(containerId);
    const countEl = document.getElementById(countId);

    if (countEl) {
        countEl.textContent = buckets.length > 0 ? buckets.length : '';
    }

    if (buckets.length === 0) {
        container.innerHTML = '<p class="empty-state" style="padding: 0.5rem 0; font-size: 0.875rem;">No years available</p>';
        return;
    }

    const years = buckets.map(b => parseInt(b.key)).filter(y => !isNaN(y)).sort();
    const minYear = years[0];
    const maxYear = years[years.length - 1];

    container.innerHTML = `
        <div class="year-range">
            <input type="number" id="year-from" placeholder="${minYear}" min="${minYear}" max="${maxYear}" value="${state.yearFrom || ''}">
            <span>to</span>
            <input type="number" id="year-to" placeholder="${maxYear}" min="${minYear}" max="${maxYear}" value="${state.yearTo || ''}">
            <button type="button" onclick="applyYearFilter()">Apply</button>
        </div>
    `;
}

function toggleFacet(type, value) {
    let arr;
    switch (type) {
        case 'source': arr = state.sources; break;
        case 'organism': arr = state.organisms; break;
        case 'method': arr = state.methods; break;
        default: return;
    }

    const idx = arr.indexOf(value);
    if (idx === -1) {
        arr.push(value);
    } else {
        arr.splice(idx, 1);
    }

    state.offset = 0;
    updateURL();
    performSearch();
}

function applyYearFilter() {
    const fromInput = document.getElementById('year-from');
    const toInput = document.getElementById('year-to');

    state.yearFrom = fromInput.value ? parseInt(fromInput.value) : null;
    state.yearTo = toInput.value ? parseInt(toInput.value) : null;
    state.offset = 0;
    updateURL();
    performSearch();
}

function clearFilters() {
    state.sources = [];
    state.organisms = [];
    state.methods = [];
    state.yearFrom = null;
    state.yearTo = null;
    state.offset = 0;
    updateURL();
    performSearch();
}

function renderPagination(total) {
    if (total <= PAGE_SIZE) {
        pagination.innerHTML = '';
        return;
    }

    const currentPage = Math.floor(state.offset / PAGE_SIZE) + 1;
    const totalPages = Math.ceil(total / PAGE_SIZE);

    pagination.innerHTML = `
        <div class="pagination-controls">
            <button onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>
                Previous
            </button>
            <span class="pagination-info">Page ${currentPage} of ${totalPages}</span>
            <button onclick="goToPage(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled' : ''}>
                Next
            </button>
        </div>
    `;
}

function goToPage(page) {
    state.offset = (page - 1) * PAGE_SIZE;
    updateURL();
    performSearch();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions available globally for inline handlers
window.toggleFacet = toggleFacet;
window.applyYearFilter = applyYearFilter;
window.goToPage = goToPage;
