/**
 * India & Gujarat Labour Law Tracker - Main Application Logic
 * -----------------------------------------------------------
 * Pure Vanilla JavaScript Client Application
 */

const App = (function () {
  // Application State
  let state = {
    articles: [],
    filteredArticles: [],
    filters: {
      search: "",
      state: "all",
      category: "all",
      sector: "all",
      time: "all",
      onlyBookmarks: false,
    },
    sort: "newest",
    viewMode: "grid",
    theme: localStorage.getItem("labour_tracker_theme") || "light",
    bookmarks: [],
    isLoading: true,
  };

  // DOM Elements cache
  const el = {};

  function init() {
    cacheElements();
    applyTheme(state.theme);
    state.bookmarks = SupabaseManager.getLocalBookmarks();
    bindEvents();
    loadArticlesData();
    setupAuthListeners();
  }

  function cacheElements() {
    el.articlesGrid = document.getElementById("articlesGrid");
    el.resultsCount = document.getElementById("resultsCount");
    el.searchInput = document.getElementById("searchInput");
    el.clearSearchBtn = document.getElementById("clearSearchBtn");
    el.sortSelect = document.getElementById("sortSelect");
    el.viewToggleGrid = document.getElementById("viewToggleGrid");
    el.viewToggleList = document.getElementById("viewToggleList");
    el.themeToggleBtn = document.getElementById("themeToggleBtn");
    el.liveRefreshBtn = document.getElementById("liveRefreshBtn");
    
    // Stats elements
    el.statTotal = document.getElementById("statTotal");
    el.statStates = document.getElementById("statStates");
    el.statCategories = document.getElementById("statCategories");
    el.statToday = document.getElementById("statToday");
    
    // Modals
    el.addSourceModal = document.getElementById("addSourceModal");
    el.authModal = document.getElementById("authModal");
    el.settingsModal = document.getElementById("settingsModal");
    el.toastContainer = document.getElementById("toastContainer");
  }

  function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("labour_tracker_theme", theme);
    if (el.themeToggleBtn) {
      el.themeToggleBtn.innerHTML = theme === "dark" ? "☀️" : "🌙";
      el.themeToggleBtn.title = theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme";
    }
  }

  function toggleTheme() {
    applyTheme(state.theme === "dark" ? "light" : "dark");
  }

  function bindEvents() {
    // Theme toggle
    if (el.themeToggleBtn) {
      el.themeToggleBtn.addEventListener("click", toggleTheme);
    }

    // Search input
    if (el.searchInput) {
      el.searchInput.addEventListener("input", (e) => {
        state.filters.search = e.target.value.trim().toLowerCase();
        if (el.clearSearchBtn) {
          el.clearSearchBtn.style.display = state.filters.search ? "block" : "none";
        }
        applyFilters();
      });
    }

    if (el.clearSearchBtn) {
      el.clearSearchBtn.addEventListener("click", () => {
        el.searchInput.value = "";
        state.filters.search = "";
        el.clearSearchBtn.style.display = "none";
        applyFilters();
        el.searchInput.focus();
      });
    }

    // Sort select
    if (el.sortSelect) {
      el.sortSelect.addEventListener("change", (e) => {
        state.sort = e.target.value;
        applyFilters();
      });
    }

    // View toggle
    if (el.viewToggleGrid) {
      el.viewToggleGrid.addEventListener("click", () => setViewMode("grid"));
    }
    if (el.viewToggleList) {
      el.viewToggleList.addEventListener("click", () => setViewMode("list"));
    }

    // Filter Chips binding
    document.querySelectorAll(".chip-btn").forEach((chip) => {
      chip.addEventListener("click", (e) => {
        const target = e.currentTarget;
        const group = target.dataset.group;
        const val = target.dataset.val;

        if (group && val) {
          document.querySelectorAll(`.chip-btn[data-group="${group}"]`).forEach((c) => c.classList.remove("active"));
          target.classList.add("active");
          state.filters[group] = val;
          applyFilters();
        }
      });
    });

    // Live refresh / sync
    if (el.liveRefreshBtn) {
      el.liveRefreshBtn.addEventListener("click", async () => {
        showToast("Syncing latest live feeds...");
        await loadArticlesData(true);
        showToast("Live data refreshed successfully!");
      });
    }

    // Quick Add Source Form
    const quickAddForm = document.getElementById("quickAddSourceForm");
    if (quickAddForm) {
      quickAddForm.addEventListener("submit", handleAddSourceSubmit);
    }

    // Modal Close buttons
    document.querySelectorAll(".modal-close-btn, .modal-backdrop").forEach((closeEl) => {
      closeEl.addEventListener("click", (e) => {
        if (e.target === closeEl || e.target.classList.contains("modal-close-btn")) {
          closeAllModals();
        }
      });
    });
  }

  function setViewMode(mode) {
    state.viewMode = mode;
    if (mode === "list") {
      el.articlesGrid.classList.add("list-view");
      el.viewToggleList.classList.add("active");
      el.viewToggleGrid.classList.remove("active");
    } else {
      el.articlesGrid.classList.remove("list-view");
      el.viewToggleGrid.classList.add("active");
      el.viewToggleList.classList.remove("active");
    }
  }

  async function loadArticlesData(forceRefresh = false) {
    state.isLoading = true;
    renderLoadingState();

    let fetchedData = null;

    // 1. Try Supabase if connected
    if (SupabaseManager.isConfigured() && !forceRefresh) {
      fetchedData = await SupabaseManager.fetchRemoteArticles();
    }

    // 2. Fetch from data/archive.json
    if (!fetchedData || fetchedData.length === 0) {
      try {
        const response = await fetch("data/archive.json?t=" + Date.now());
        if (response.ok) {
          fetchedData = await response.json();
        }
      } catch (err) {
        console.warn("Could not load from root data/archive.json, trying fallback...", err);
      }
    }

    // Fallback path
    if (!fetchedData || fetchedData.length === 0) {
      try {
        const response = await fetch("docs/data/archive.json?t=" + Date.now());
        if (response.ok) {
          fetchedData = await response.json();
        }
      } catch (e) {
        console.error("Failed to load archive data:", e);
      }
    }

    state.articles = Array.isArray(fetchedData) ? fetchedData : [];
    state.isLoading = false;
    
    updateStatsBar();
    applyFilters();
  }

  function updateStatsBar() {
    const total = state.articles.length;
    const states = new Set(state.articles.map((a) => a.state)).size;
    const categories = new Set(state.articles.map((a) => a.category)).size;

    const todayStr = new Date().toISOString().split("T")[0];
    const todayCount = state.articles.filter((a) => a.added_date === todayStr).length;

    if (el.statTotal) el.statTotal.textContent = total;
    if (el.statStates) el.statStates.textContent = states;
    if (el.statCategories) el.statCategories.textContent = categories;
    if (el.statToday) el.statToday.textContent = todayCount > 0 ? `+${todayCount}` : "Live";
  }

  function applyFilters() {
    const { search, state: selectedState, category, sector, time, onlyBookmarks } = state.filters;
    const today = new Date();

    let list = state.articles.filter((item) => {
      // 1. State Filter
      if (selectedState !== "all") {
        if (selectedState === "Gujarat" && item.state !== "Gujarat") return false;
        if (selectedState === "Jammu & Kashmir" && item.state !== "Jammu & Kashmir") return false;
        if (selectedState === "Maharashtra" && item.state !== "Maharashtra") return false;
        if (selectedState === "Karnataka" && item.state !== "Karnataka") return false;
        if (selectedState === "National / Central" && item.state !== "National / Central") return false;
        if (item.state !== selectedState) return false;
      }

      // 2. Category Filter
      if (category !== "all" && item.category !== category) {
        return false;
      }

      // 3. Sector Filter
      if (sector !== "all" && item.sector !== sector) {
        return false;
      }

      // 4. Bookmarks Only
      if (onlyBookmarks && !state.bookmarks.includes(item.id)) {
        return false;
      }

      // 5. Time Period Filter
      if (time !== "all" && item.added_date) {
        const itemDate = new Date(item.added_date);
        const diffDays = (today - itemDate) / (1000 * 60 * 60 * 24);

        if (time === "1d" && diffDays > 1.5) return false;
        if (time === "7d" && diffDays > 7.5) return false;
        if (time === "30d" && diffDays > 31) return false;
        if (time === "90d" && diffDays > 92) return false;
        if (time === "365d" && diffDays > 366) return false;
      }

      // 6. Search Query (full text across title, summary, source, category, state)
      if (search) {
        const combined = `${item.title} ${item.summary} ${item.source} ${item.category} ${item.state} ${item.sector}`.toLowerCase();
        if (!combined.includes(search)) return false;
      }

      return true;
    });

    // Sorting
    if (state.sort === "oldest") {
      list.sort((a, b) => (a.added_date || "").localeCompare(b.added_date || ""));
    } else {
      list.sort((a, b) => (b.added_date || "").localeCompare(a.added_date || ""));
    }

    state.filteredArticles = list;
    renderArticles();
  }

  function renderArticles() {
    if (!el.articlesGrid) return;

    if (state.filteredArticles.length === 0) {
      el.articlesGrid.innerHTML = `
        <div class="empty-state">
          <div class="empty-icon">🔍</div>
          <div class="empty-title">No matching labour updates found</div>
          <div class="empty-desc">Try clearing your search query or selecting "All States" / "All Topics" to see historical updates back to October 2025.</div>
          <button class="nav-btn btn-accent" style="color:white; display:inline-block;" onclick="App.resetFilters()">Reset All Filters</button>
        </div>
      `;
      if (el.resultsCount) el.resultsCount.innerHTML = `Showing <strong>0</strong> updates`;
      return;
    }

    if (el.resultsCount) {
      el.resultsCount.innerHTML = `Showing <strong>${state.filteredArticles.length}</strong> of ${state.articles.length} updates`;
    }

    const html = state.filteredArticles.map((item) => createArticleCardHtml(item)).join("");
    el.articlesGrid.innerHTML = html;

    // Attach bookmark click handlers
    el.articlesGrid.querySelectorAll(".bookmark-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const articleId = btn.dataset.id;
        toggleBookmark(articleId);
      });
    });
  }

  function createArticleCardHtml(item) {
    const isBookmarked = state.bookmarks.includes(item.id);
    const dateFormatted = formatDate(item.added_date);
    
    return `
      <article class="article-card" id="card-${escapeHtml(item.id)}">
        <div class="card-header-tags">
          <div class="tag-badges-row">
            <span class="badge badge-state">📍 ${escapeHtml(item.state || "National")}</span>
            <span class="badge badge-category">🏷️ ${escapeHtml(item.category || "Labour Law")}</span>
            <span class="badge badge-sector">🏭 ${escapeHtml(item.sector || "General")}</span>
          </div>
          <span class="card-date">${dateFormatted}</span>
        </div>

        <a href="${escapeHtml(item.link)}" target="_blank" rel="noopener noreferrer" class="card-title">
          ${escapeHtml(item.title)}
        </a>

        <!-- Approximately 40-50 Words Summary Box -->
        <div class="card-summary-box">
          <p class="card-summary-text">${escapeHtml(item.summary)}</p>
        </div>

        <div class="card-footer">
          <div class="source-credit">
            📰 <span>${escapeHtml(item.source || "Official Source")}</span>
          </div>
          <div class="card-action-btns">
            <button class="bookmark-btn ${isBookmarked ? "bookmarked" : ""}" data-id="${escapeHtml(item.id)}" title="${isBookmarked ? "Remove Bookmark" : "Save Article"}">
              ${isBookmarked ? "★" : "☆"}
            </button>
            <a href="${escapeHtml(item.link)}" target="_blank" rel="noopener noreferrer" class="read-more-btn">
              Read More &rarr;
            </a>
          </div>
        </div>
      </article>
    `;
  }

  function toggleBookmark(articleId) {
    const res = SupabaseManager.toggleLocalBookmark(articleId);
    state.bookmarks = res.list;
    showToast(res.isBookmarked ? "Article saved to bookmarks!" : "Article removed from bookmarks.");
    
    // Update card UI instantly
    const card = document.getElementById(`card-${articleId}`);
    if (card) {
      const btn = card.querySelector(".bookmark-btn");
      if (btn) {
        btn.classList.toggle("bookmarked", res.isBookmarked);
        btn.innerHTML = res.isBookmarked ? "★" : "☆";
      }
    }

    if (state.filters.onlyBookmarks) {
      applyFilters();
    }
  }

  function resetFilters() {
    state.filters = {
      search: "",
      state: "all",
      category: "all",
      sector: "all",
      time: "all",
      onlyBookmarks: false,
    };
    if (el.searchInput) {
      el.searchInput.value = "";
      el.clearSearchBtn.style.display = "none";
    }
    document.querySelectorAll(".chip-btn").forEach((c) => {
      if (c.dataset.val === "all") c.classList.add("active");
      else c.classList.remove("active");
    });
    applyFilters();
  }

  function toggleBookmarksView() {
    state.filters.onlyBookmarks = !state.filters.onlyBookmarks;
    applyFilters();
    showToast(state.filters.onlyBookmarks ? "Filtering saved bookmarks" : "Showing all updates");
  }

  // Add Source Handler (e.g. Daily Excelsior link)
  async function handleAddSourceSubmit(e) {
    e.preventDefault();
    const input = document.getElementById("sourceUrlInput");
    const url = input.value.trim();
    if (!url) return;

    try {
      showToast("Adding source and analyzing link...");
      const registered = await SourcesManager.addSource(url);

      // If it is a specific article, immediately insert it into the active feed
      if (registered.isSpecificArticle) {
        const newArticle = {
          id: "custom-" + Date.now(),
          title: `Labour Code & Policy Review: ${registered.name}`,
          link: url,
          source: registered.name,
          category: registered.category,
          state: registered.state,
          sector: "General / All Sectors",
          summary: `Directly added update from ${registered.name} regarding state and national labour policy implementation. Review full details, circular citations, and compliance guidance directly at the original source.`,
          added_date: new Date().toISOString().split("T")[0],
          notified: true,
        };

        state.articles.unshift(newArticle);
        updateStatsBar();
        applyFilters();
      }

      input.value = "";
      closeAllModals();
      showToast(`Source '${registered.name}' added! It will be continuously referenced in all daily 6:00 PM updates.`);
    } catch (err) {
      alert(err.message || "Failed to add source");
    }
  }

  function renderLoadingState() {
    if (!el.articlesGrid) return;
    el.articlesGrid.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⏳</div>
        <div class="empty-title">Loading Labour Law Updates...</div>
        <div class="empty-desc">Fetching latest PF, ESI, gratuity, state policy, and gazette records from database.</div>
      </div>
    `;
  }

  function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add("active");
  }

  function closeAllModals() {
    document.querySelectorAll(".modal-backdrop").forEach((m) => m.classList.remove("active"));
  }

  function showToast(msg) {
    if (!el.toastContainer) return;
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.innerHTML = `🔔 <span>${escapeHtml(msg)}</span>`;
    el.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function setupAuthListeners() {
    SupabaseManager.onAuthChange((user) => {
      const authBtn = document.getElementById("authNavBtn");
      if (authBtn) {
        if (user) {
          authBtn.innerHTML = `👤 ${escapeHtml(user.email.split("@")[0])}`;
          authBtn.title = `Logged in as ${user.email}. Click to manage account.`;
        } else {
          authBtn.innerHTML = `🔐 Sign In / Supabase`;
          authBtn.title = "Connect Supabase or Sign In";
        }
      }
    });
  }

  function formatDate(isoStr) {
    if (!isoStr) return "";
    try {
      const parts = isoStr.split("-");
      if (parts.length === 3) {
        const year = parts[0];
        const monthIndex = parseInt(parts[1], 10) - 1;
        const day = parseInt(parts[2], 10);
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        return `${day} ${monthNames[monthIndex]} ${year}`;
      }
    } catch {
      return isoStr;
    }
    return isoStr;
  }

  function escapeHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // Public Interface
  return {
    init,
    resetFilters,
    toggleBookmarksView,
    openModal,
    closeAllModals,
    showToast,
  };
})();

document.addEventListener("DOMContentLoaded", App.init);
