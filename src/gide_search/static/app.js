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
    performSearch();

    searchForm.addEventListener('submit', handleSearch);
    clearFiltersBtn.addEventListener('click', clearFilters);
    window.addEventListener('popstate', () => {
        loadStateFromURL();
        performSearch();
    });
});

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

    resultsList.innerHTML = '<p aria-busy="true">Searching...</p>';

    try {
        const response = await fetch(`/search?${params.toString()}`);
        if (!response.ok) throw new Error('Search failed');
        const data = await response.json();
        renderResults(data);
        renderFacets(data.facets);
        renderPagination(data.total);
    } catch (error) {
        resultsList.innerHTML = `<p class="error">Error: ${error.message}</p>`;
    }
}

function renderResults(data) {
    resultsCount.textContent = `${data.total.toLocaleString()} studies found`;

    if (data.hits.length === 0) {
        resultsList.innerHTML = '<p>No studies found. Try adjusting your search or filters.</p>';
        return;
    }

    resultsList.innerHTML = data.hits.map(hit => `
        <article class="result-card">
            <header>
                <span class="source-badge source-${hit.source.toLowerCase()}">${hit.source}</span>
                <h4><a href="${escapeHtml(hit.source_url)}" target="_blank">${escapeHtml(hit.title)}</a></h4>
            </header>
            <p class="description">${escapeHtml(hit.description)}</p>
            <footer>
                <div class="tags">
                    ${hit.organisms.map(o => `<span class="tag organism">${escapeHtml(o)}</span>`).join('')}
                    ${hit.imaging_methods.map(m => `<span class="tag method">${escapeHtml(m)}</span>`).join('')}
                </div>
                ${hit.release_date ? `<small class="date">${hit.release_date}</small>` : ''}
            </footer>
        </article>
    `).join('');
}

function renderFacets(facets) {
    renderFacetGroup('facet-sources', facets.sources, 'source', state.sources);
    renderFacetGroup('facet-organisms', facets.organisms, 'organism', state.organisms);
    renderFacetGroup('facet-methods', facets.imaging_methods, 'method', state.methods);
    renderFacetGroup('facet-years', facets.years, 'year', []);
}

function renderFacetGroup(containerId, buckets, type, selected) {
    const container = document.getElementById(containerId);

    if (buckets.length === 0) {
        container.innerHTML = '<small>No options available</small>';
        return;
    }

    if (type === 'year') {
        // Render year range selector
        const years = buckets.map(b => parseInt(b.key)).filter(y => !isNaN(y)).sort();
        if (years.length === 0) {
            container.innerHTML = '<small>No years available</small>';
            return;
        }
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
        return;
    }

    container.innerHTML = buckets.slice(0, 15).map(bucket => {
        const isChecked = selected.includes(bucket.key);
        const id = `${type}-${bucket.key.replace(/\s+/g, '-')}`;
        return `
            <label class="facet-item">
                <input type="checkbox" id="${escapeHtml(id)}"
                       ${isChecked ? 'checked' : ''}
                       onchange="toggleFacet('${type}', '${escapeHtml(bucket.key)}')">
                <span class="facet-label">${escapeHtml(bucket.key)}</span>
                <span class="facet-count">${bucket.count}</span>
            </label>
        `;
    }).join('');

    if (buckets.length > 15) {
        container.innerHTML += `<small>${buckets.length - 15} more...</small>`;
    }
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
            <button onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>Previous</button>
            <span>Page ${currentPage} of ${totalPages}</span>
            <button onclick="goToPage(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled' : ''}>Next</button>
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
