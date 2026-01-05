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
    currentView: 'browse', // 'browse' or 'study'
    currentStudyId: null,
};

// DOM Elements
const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const resultsCount = document.getElementById('results-count');
const resultsList = document.getElementById('results-list');
const pagination = document.getElementById('pagination');
const clearFiltersBtn = document.getElementById('clear-filters');
const browseView = document.getElementById('browse-view');
const studyView = document.getElementById('study-view');
const helpView = document.getElementById('help-view');
const breadcrumbCurrent = document.getElementById('breadcrumb-current');
const inlineHelpBtn = document.getElementById('inline-help-btn');
const inlineHelpPopup = document.getElementById('inline-help-popup');
const advancedSearchView = document.getElementById('advanced-search-view');
const advancedSearchForm = document.getElementById('advanced-search-form');

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadStateFromURL();
    setupFilterToggles();
    setupInlineHelp();
    setupAdvancedSearch();

    // Check which page we're loading
    const path = window.location.pathname;
    const studyMatch = path.match(/^\/study\/(.+)$/);
    if (studyMatch) {
        state.currentStudyId = decodeURIComponent(studyMatch[1]);
        showStudyView(state.currentStudyId);
    } else if (path === '/help') {
        showHelpView();
    } else if (path === '/advanced-search') {
        showAdvancedSearchView();
    } else {
        performSearch();
    }

    searchForm.addEventListener('submit', handleSearch);
    clearFiltersBtn.addEventListener('click', clearFilters);
    window.addEventListener('popstate', handlePopState);
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

function setupInlineHelp() {
    // Toggle popup on button click
    inlineHelpBtn.addEventListener('click', () => {
        inlineHelpPopup.classList.toggle('active');
    });

    // Close on close button click
    const closeBtn = inlineHelpPopup.querySelector('.inline-help-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            inlineHelpPopup.classList.remove('active');
        });
    }

    // Close on outside click
    document.addEventListener('click', (e) => {
        if (!inlineHelpBtn.contains(e.target) && !inlineHelpPopup.contains(e.target)) {
            inlineHelpPopup.classList.remove('active');
        }
    });

    // Handle "View full search guide" link
    const moreLink = inlineHelpPopup.querySelector('.inline-help-more');
    if (moreLink) {
        moreLink.addEventListener('click', (e) => {
            e.preventDefault();
            inlineHelpPopup.classList.remove('active');
            history.pushState(null, '', '/help');
            showHelpView();
        });
    }
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
    showBrowseView();
    updateURL();
    performSearch();
}

function handlePopState() {
    const path = window.location.pathname;
    const studyMatch = path.match(/^\/study\/(.+)$/);
    if (studyMatch) {
        state.currentStudyId = decodeURIComponent(studyMatch[1]);
        showStudyView(state.currentStudyId);
    } else if (path === '/help') {
        showHelpView();
    } else if (path === '/advanced-search') {
        showAdvancedSearchViewWithoutPush();
    } else {
        loadStateFromURL();
        showBrowseViewWithoutPush();
        performSearch();
    }
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

    // Use highlighted title if available, otherwise escape the plain title
    const titleHtml = hit.highlights?.title
        ? sanitizeHighlight(hit.highlights.title)
        : escapeHtml(hit.title);

    // Use highlighted description fragments if available
    let descriptionHtml;
    if (hit.highlights?.description && hit.highlights.description.length > 0) {
        descriptionHtml = hit.highlights.description.map(sanitizeHighlight).join(' ... ');
    } else {
        descriptionHtml = escapeHtml(hit.description);
    }

    return `
        <article class="study-card" onclick="openStudy('${escapeHtml(hit.id)}')" style="cursor: pointer;">
            <div class="study-card-header">
                <span class="source-badge ${sourceClass}">${escapeHtml(hit.source)}</span>
                <div class="study-card-title">
                    <h3>
                        <a href="/study/${encodeURIComponent(hit.id)}" onclick="event.stopPropagation(); openStudy('${escapeHtml(hit.id)}'); return false;">
                            ${titleHtml}
                        </a>
                    </h3>
                    <a href="${escapeHtml(hit.source_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation();" title="View original study">
                        <svg class="external-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                            <polyline points="15 3 21 3 21 9"/>
                            <line x1="10" y1="14" x2="21" y2="3"/>
                        </svg>
                    </a>
                </div>
            </div>
            <p class="study-description">${descriptionHtml}</p>
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
            <div class="study-card-footer">
                ${(organisms.length > 0 || methods.length > 0) ? `
                    <div class="study-tags">
                        ${organisms.map(o => `<span class="tag organism">${escapeHtml(o)}</span>`).join('')}
                        ${methods.map(m => `<span class="tag method">${escapeHtml(m)}</span>`).join('')}
                    </div>
                ` : '<div></div>'}
                ${(hit.file_count || hit.total_size_bytes) ? `
                    <div class="study-size-info">
                        ${hit.file_count ? `<span class="size-item">${hit.file_count.toLocaleString()} files</span>` : ''}
                        ${hit.total_size_bytes ? `<span class="size-item">${formatBytes(hit.total_size_bytes)}</span>` : ''}
                    </div>
                ` : ''}
            </div>
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

function sanitizeHighlight(text) {
    // Escape all HTML except <mark> and </mark> tags for search highlighting
    // This prevents XSS while allowing highlight marks to render
    if (!text) return '';

    // First, replace <mark> and </mark> with placeholders
    const markPlaceholder = '\u0000MARK\u0000';
    const markEndPlaceholder = '\u0000/MARK\u0000';

    let result = text
        .replace(/<mark>/g, markPlaceholder)
        .replace(/<\/mark>/g, markEndPlaceholder);

    // Escape the rest
    const div = document.createElement('div');
    div.textContent = result;
    result = div.innerHTML;

    // Restore <mark> tags
    result = result
        .replace(new RegExp(markPlaceholder, 'g'), '<mark>')
        .replace(new RegExp(markEndPlaceholder, 'g'), '</mark>');

    return result;
}

// ============================================
// Study Detail View Functions
// ============================================

function openStudy(studyId) {
    state.currentStudyId = studyId;
    history.pushState({ studyId }, '', `/study/${encodeURIComponent(studyId)}`);
    showStudyView(studyId);
}

function showBrowseView() {
    state.currentView = 'browse';
    state.currentStudyId = null;
    browseView.style.display = '';
    studyView.style.display = 'none';
    helpView.style.display = 'none';
    advancedSearchView.style.display = 'none';
    breadcrumbCurrent.textContent = 'Browse Studies';
    updateNavActive('browse');
    history.pushState(null, '', getSearchURL());
}

function showBrowseViewWithoutPush() {
    state.currentView = 'browse';
    state.currentStudyId = null;
    browseView.style.display = '';
    studyView.style.display = 'none';
    helpView.style.display = 'none';
    advancedSearchView.style.display = 'none';
    breadcrumbCurrent.textContent = 'Browse Studies';
    updateNavActive('browse');
}

function showHelpView() {
    state.currentView = 'help';
    state.currentStudyId = null;
    browseView.style.display = 'none';
    studyView.style.display = 'none';
    helpView.style.display = '';
    advancedSearchView.style.display = 'none';
    breadcrumbCurrent.innerHTML = '<a href="/" onclick="showBrowseView(); return false;">GIDE Search</a> <span class="separator">&gt;</span> <span>Search Help</span>';
    updateNavActive('help');
}

function updateNavActive(view) {
    document.getElementById('nav-browse').classList.toggle('active', view === 'browse' || view === 'study');
    document.getElementById('nav-advanced').classList.toggle('active', view === 'advanced-search');
    document.getElementById('nav-help').classList.toggle('active', view === 'help');
}

function getSearchURL() {
    const params = new URLSearchParams();
    if (state.query) params.set('q', state.query);
    state.sources.forEach(s => params.append('source', s));
    state.organisms.forEach(o => params.append('organism', o));
    state.methods.forEach(m => params.append('imaging_method', m));
    if (state.yearFrom) params.set('year_from', state.yearFrom);
    if (state.yearTo) params.set('year_to', state.yearTo);
    if (state.offset > 0) params.set('offset', state.offset);
    return params.toString() ? `/?${params.toString()}` : '/';
}

async function showStudyView(studyId) {
    state.currentView = 'study';
    browseView.style.display = 'none';
    studyView.style.display = '';
    helpView.style.display = 'none';
    advancedSearchView.style.display = 'none';
    updateNavActive('browse'); // Study view is part of browse

    // Show loading state
    document.getElementById('study-title').textContent = 'Loading...';
    document.getElementById('study-id').textContent = studyId;
    breadcrumbCurrent.innerHTML = `<a href="/" onclick="showBrowseView(); return false;">Browse Studies</a> <span class="separator">&gt;</span> <span>${escapeHtml(studyId)}</span>`;

    try {
        const response = await fetch(`/api/study/${encodeURIComponent(studyId)}`);
        if (!response.ok) throw new Error('Study not found');
        const study = await response.json();
        renderStudyDetail(study);
    } catch (error) {
        studyView.innerHTML = `
            <div class="study-detail">
                <div class="error-message" style="margin: 2rem;">
                    <p>Error: ${escapeHtml(error.message)}</p>
                    <p><a href="/" onclick="showBrowseView(); return false;">Return to browse</a></p>
                </div>
            </div>
        `;
    }
}

function renderStudyDetail(study) {
    const sourceClass = study.source.toLowerCase();

    // Header
    document.getElementById('study-source-badge').className = `source-badge ${sourceClass}`;
    document.getElementById('study-source-badge').textContent = study.source;
    document.getElementById('study-id').textContent = study.id;
    document.getElementById('study-title').textContent = study.title;
    breadcrumbCurrent.innerHTML = `<a href="/" onclick="showBrowseView(); return false;">Browse Studies</a> <span class="separator">&gt;</span> <span>${escapeHtml(study.id)}</span>`;

    // Identifiers (DOI, dates)
    let identifiersHtml = '';
    if (study.release_date) {
        identifiersHtml += `
            <span class="study-identifier">
                <span class="study-identifier-label">Released:</span>
                <span class="study-identifier-value">${escapeHtml(study.release_date)}</span>
            </span>
        `;
    }
    if (study.data_doi) {
        identifiersHtml += `
            <span class="study-identifier">
                <span class="study-identifier-label">DOI:</span>
                <span class="study-identifier-value">
                    <a href="https://doi.org/${escapeHtml(study.data_doi)}" target="_blank">${escapeHtml(study.data_doi)}</a>
                </span>
            </span>
        `;
    }
    document.getElementById('study-identifiers').innerHTML = identifiersHtml;

    // Authors
    if (study.authors && study.authors.length > 0) {
        const affiliationsMap = new Map();
        let affIndex = 1;

        // Collect unique affiliations
        study.authors.forEach(author => {
            if (author.affiliations) {
                author.affiliations.forEach(aff => {
                    if (!affiliationsMap.has(aff.display_name)) {
                        affiliationsMap.set(aff.display_name, affIndex++);
                    }
                });
            }
        });

        const authorsHtml = study.authors.map((author, i) => {
            let authorHtml = `<span class="study-author">`;
            authorHtml += `<span class="study-author-name">${escapeHtml(author.name)}</span>`;

            // Add affiliation superscripts
            if (author.affiliations && author.affiliations.length > 0) {
                const indices = author.affiliations.map(aff => affiliationsMap.get(aff.display_name));
                authorHtml += `<sup>${indices.join(',')}</sup>`;
            }

            // Add ORCID link
            if (author.orcid) {
                authorHtml += `
                    <a href="https://orcid.org/${escapeHtml(author.orcid)}" target="_blank" class="orcid-link" title="ORCID">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="#a6ce39">
                            <path d="M12 0C5.372 0 0 5.372 0 12s5.372 12 12 12 12-5.372 12-12S18.628 0 12 0zM7.369 4.378c.525 0 .947.431.947.947s-.422.947-.947.947a.95.95 0 0 1-.947-.947c0-.525.422-.947.947-.947zm-.722 3.038h1.444v10.041H6.647V7.416zm3.562 0h3.9c3.712 0 5.344 2.653 5.344 5.025 0 2.578-2.016 5.025-5.325 5.025h-3.919V7.416zm1.444 1.303v7.444h2.297c3.272 0 4.022-2.484 4.022-3.722 0-1.444-.844-3.722-3.919-3.722h-2.4z"/>
                        </svg>
                    </a>
                `;
            }

            authorHtml += `</span>`;
            return authorHtml;
        }).join('<span style="color: rgba(255,255,255,0.5)">, </span>');

        document.getElementById('study-authors').innerHTML = authorsHtml;

        // Affiliations
        if (affiliationsMap.size > 0) {
            const affiliationsHtml = Array.from(affiliationsMap.entries()).map(([name, index]) => {
                return `<span class="study-affiliation"><sup>${index}</sup>${escapeHtml(name)}</span>`;
            }).join('<span style="color: rgba(255,255,255,0.5)">; </span>');
            document.getElementById('study-affiliations').innerHTML = affiliationsHtml;
        } else {
            document.getElementById('study-affiliations').innerHTML = '';
        }
    } else {
        document.getElementById('study-authors').innerHTML = '';
        document.getElementById('study-affiliations').innerHTML = '';
    }

    // Stats
    let statsHtml = '';
    if (study.file_count) {
        statsHtml += `
            <div class="study-stat">
                <span class="study-stat-label">Files</span>
                <span class="study-stat-value">${study.file_count.toLocaleString()}</span>
            </div>
        `;
    }
    if (study.total_size_bytes) {
        statsHtml += `
            <div class="study-stat">
                <span class="study-stat-label">Total Size</span>
                <span class="study-stat-value">${formatBytes(study.total_size_bytes)}</span>
            </div>
        `;
    }
    document.getElementById('study-stats').innerHTML = statsHtml;
    document.getElementById('study-stats').style.display = statsHtml ? '' : 'none';

    // Source link
    document.getElementById('study-source-link').href = study.source_url;

    // Description
    document.getElementById('study-description').textContent = study.description || 'No description available.';

    // Keywords
    if (study.keywords && study.keywords.length > 0) {
        document.getElementById('study-keywords-container').style.display = '';
        document.getElementById('study-keywords').innerHTML = study.keywords.map(k =>
            `<span class="keyword-tag">${escapeHtml(k)}</span>`
        ).join('');
    } else {
        document.getElementById('study-keywords-container').style.display = 'none';
    }

    // License
    document.getElementById('study-license').textContent = study.license || 'Not specified';

    // Funding
    if (study.funding && study.funding.length > 0) {
        document.getElementById('study-funding-container').style.display = '';
        document.getElementById('study-funding').innerHTML = study.funding.map(f => `
            <li>
                <span class="funding-funder">${escapeHtml(f.funder)}</span>
                <span class="funding-grant">Grant: ${escapeHtml(f.grant_id)}</span>
            </li>
        `).join('');
    } else {
        document.getElementById('study-funding-container').style.display = 'none';
    }

    // Organisms (aggregate from all biosamples)
    const allOrganisms = (study.biosamples || []).flatMap(bs => bs.organism || []);
    if (allOrganisms.length > 0) {
        document.getElementById('study-organisms').innerHTML = allOrganisms.map(o => {
            let html = `<span class="tag organism">${escapeHtml(o.scientific_name)}</span>`;
            if (o.ncbi_taxon_id) {
                html = `<a href="https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=${o.ncbi_taxon_id}" target="_blank">${html}</a>`;
            }
            return html;
        }).join(' ');
    }

    // Sample type (from first biosample)
    const firstBiosample = study.biosamples?.[0];
    document.getElementById('study-sample-type').textContent = firstBiosample?.sample_type || 'Not specified';

    // Cell line (from first biosample)
    if (firstBiosample?.cell_line) {
        document.getElementById('study-cell-line-container').style.display = '';
        document.getElementById('study-cell-line').textContent = firstBiosample.cell_line;
    } else {
        document.getElementById('study-cell-line-container').style.display = 'none';
    }

    // Strain (from first biosample)
    if (firstBiosample?.strain) {
        document.getElementById('study-strain-container').style.display = '';
        document.getElementById('study-strain').textContent = firstBiosample.strain;
    } else {
        document.getElementById('study-strain-container').style.display = 'none';
    }

    // Imaging methods (aggregate from all protocols)
    const allMethods = (study.image_acquisition_protocols || []).flatMap(iap => iap.methods || []);
    if (allMethods.length > 0) {
        document.getElementById('study-methods').innerHTML = allMethods.map(m => {
            let html = `<span class="tag method">${escapeHtml(m.name)}</span>`;
            if (m.fbbi_id) {
                const fbbi = m.fbbi_id.replace('FBbi:', '');
                html = `<a href="http://purl.obolibrary.org/obo/FBbi_${fbbi}" target="_blank" title="${m.fbbi_id}">${html}</a>`;
            }
            return html;
        }).join(' ');
    }

    // Instrument description (from first protocol)
    const firstProtocol = study.image_acquisition_protocols?.[0];
    if (firstProtocol?.imaging_instrument_description) {
        document.getElementById('study-instruments-container').style.display = '';
        document.getElementById('study-instruments').textContent = firstProtocol.imaging_instrument_description;
    } else {
        document.getElementById('study-instruments-container').style.display = 'none';
    }

    // Publications
    if (study.publications && study.publications.length > 0) {
        document.getElementById('study-publications-section').style.display = '';
        document.getElementById('study-publications').innerHTML = study.publications.map(pub => {
            let linksHtml = '';
            if (pub.doi) {
                linksHtml += `<a href="https://doi.org/${escapeHtml(pub.doi)}" target="_blank" class="publication-link">DOI: ${escapeHtml(pub.doi)}</a>`;
            }
            if (pub.pubmed_id) {
                linksHtml += `<a href="https://pubmed.ncbi.nlm.nih.gov/${escapeHtml(pub.pubmed_id)}" target="_blank" class="publication-link">PubMed: ${escapeHtml(pub.pubmed_id)}</a>`;
            }
            if (pub.pmc_id) {
                linksHtml += `<a href="https://www.ncbi.nlm.nih.gov/pmc/articles/${escapeHtml(pub.pmc_id)}" target="_blank" class="publication-link">PMC: ${escapeHtml(pub.pmc_id)}</a>`;
            }

            return `
                <div class="publication-card">
                    ${pub.title ? `<div class="publication-title">${escapeHtml(pub.title)}</div>` : ''}
                    ${pub.authors_name ? `<div class="publication-authors">${escapeHtml(pub.authors_name)}</div>` : ''}
                    ${pub.year ? `<div class="publication-year">${pub.year}</div>` : ''}
                    ${linksHtml ? `<div class="publication-links">${linksHtml}</div>` : ''}
                </div>
            `;
        }).join('');
    } else {
        document.getElementById('study-publications-section').style.display = 'none';
    }

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// ============================================
// Advanced Search Functions
// ============================================

function setupAdvancedSearch() {
    if (!advancedSearchForm) return;

    advancedSearchForm.addEventListener('submit', handleAdvancedSearch);

    const clearBtn = document.getElementById('advanced-search-clear');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearAdvancedForm);
    }
}

function showAdvancedSearchView() {
    state.currentView = 'advanced-search';
    state.currentStudyId = null;
    browseView.style.display = 'none';
    studyView.style.display = 'none';
    helpView.style.display = 'none';
    advancedSearchView.style.display = '';
    breadcrumbCurrent.innerHTML = '<a href="/" onclick="showBrowseView(); return false;">GIDE Search</a> <span class="separator">&gt;</span> <span>Advanced Search</span>';
    updateNavActive('browse');
    history.pushState(null, '', '/advanced-search');
}

function showAdvancedSearchViewWithoutPush() {
    state.currentView = 'advanced-search';
    state.currentStudyId = null;
    browseView.style.display = 'none';
    studyView.style.display = 'none';
    helpView.style.display = 'none';
    advancedSearchView.style.display = '';
    breadcrumbCurrent.innerHTML = '<a href="/" onclick="showBrowseView(); return false;">GIDE Search</a> <span class="separator">&gt;</span> <span>Advanced Search</span>';
    updateNavActive('browse');
}

function handleAdvancedSearch(e) {
    e.preventDefault();

    // Get form values
    const title = document.getElementById('adv-title')?.value.trim() || '';
    const description = document.getElementById('adv-description')?.value.trim() || '';
    const author = document.getElementById('adv-author')?.value.trim() || '';
    const keywords = document.getElementById('adv-keywords')?.value.trim() || '';
    const anyField = document.getElementById('adv-any-field')?.value.trim() || '';

    // Get selected sources
    const sources = [];
    document.querySelectorAll('input[name="adv-source"]:checked').forEach(cb => {
        sources.push(cb.value);
    });

    // Get organism and imaging method
    const organism = document.getElementById('adv-organism')?.value || '';
    const imagingMethod = document.getElementById('adv-imaging-method')?.value || '';

    // Get year range
    const yearFrom = document.getElementById('adv-year-from')?.value || '';
    const yearTo = document.getElementById('adv-year-to')?.value || '';

    // Get match mode
    const matchAll = document.querySelector('input[name="adv-match-mode"]:checked')?.value === 'all';

    // Build query parts
    const queryParts = [];

    if (title) {
        queryParts.push(`title:${quoteIfNeeded(title)}`);
    }
    if (description) {
        queryParts.push(`description:${quoteIfNeeded(description)}`);
    }
    if (author) {
        queryParts.push(`authors.name:${quoteIfNeeded(author)}`);
    }
    if (keywords) {
        queryParts.push(`keywords:${quoteIfNeeded(keywords)}`);
    }
    if (anyField) {
        queryParts.push(quoteIfNeeded(anyField));
    }

    // Join query parts with operator
    const operator = matchAll ? ' AND ' : ' OR ';
    const query = queryParts.join(operator);

    // Build URL parameters
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    sources.forEach(s => params.append('source', s));
    if (organism) params.append('organism', organism);
    if (imagingMethod) params.append('imaging_method', imagingMethod);
    if (yearFrom) params.set('year_from', yearFrom);
    if (yearTo) params.set('year_to', yearTo);

    // Navigate to search results
    const url = params.toString() ? `/?${params.toString()}` : '/';
    window.location.href = url;
}

function quoteIfNeeded(value) {
    // Quote the value if it contains spaces or special characters
    if (value.includes(' ') || /[+\-&|!(){}[\]^"~*?:\\]/.test(value)) {
        // Escape any existing quotes and wrap in quotes
        return `"${value.replace(/"/g, '\\"')}"`;
    }
    return value;
}

function clearAdvancedForm() {
    if (!advancedSearchForm) return;

    // Clear text inputs
    document.getElementById('adv-title').value = '';
    document.getElementById('adv-description').value = '';
    document.getElementById('adv-author').value = '';
    document.getElementById('adv-keywords').value = '';
    document.getElementById('adv-any-field').value = '';

    // Clear source checkboxes
    document.querySelectorAll('input[name="adv-source"]').forEach(cb => {
        cb.checked = false;
    });

    // Reset dropdowns
    document.getElementById('adv-organism').value = '';
    document.getElementById('adv-imaging-method').value = '';

    // Clear year inputs
    document.getElementById('adv-year-from').value = '';
    document.getElementById('adv-year-to').value = '';

    // Reset to match all
    document.querySelector('input[name="adv-match-mode"][value="all"]').checked = true;
}

// Make functions available globally for inline handlers
window.toggleFacet = toggleFacet;
window.applyYearFilter = applyYearFilter;
window.goToPage = goToPage;
window.openStudy = openStudy;
window.showBrowseView = showBrowseView;
window.showHelpView = showHelpView;
window.showAdvancedSearchView = showAdvancedSearchView;
