/**
 * Sources Manager
 * ---------------
 * Handles dynamic user-added sources (e.g. Daily Excelsior, PIB, regional news portals),
 * URL parsing, state & category auto-detection, and syncing with Supabase/localStorage.
 */

const SourcesManager = (function () {
  const STORAGE_KEY = "labour_tracker_sources_custom";

  // Pre-configured domains mapping
  const KNOWN_DOMAINS = {
    "dailyexcelsior.com": { name: "Daily Excelsior (J&K & North)", state: "Jammu & Kashmir", category: "Labour Codes" },
    "economictimes.indiatimes.com": { name: "The Economic Times", state: "National / Central", category: "Labour Codes" },
    "livemint.com": { name: "Livemint Compliance", state: "National / Central", category: "Labour Codes" },
    "business-standard.com": { name: "Business Standard", state: "National / Central", category: "PF / EPFO" },
    "thehindu.com": { name: "The Hindu", state: "National / Central", category: "Labour Codes" },
    "barandbench.com": { name: "Bar and Bench Legal", state: "National / Central", category: "Labour Codes" },
    "livelaw.in": { name: "LiveLaw Court Updates", state: "National / Central", category: "Labour Codes" },
    "pib.gov.in": { name: "Press Information Bureau (PIB)", state: "National / Central", category: "Gazette / Notifications" },
    "epfindia.gov.in": { name: "EPFO Official Portal", state: "National / Central", category: "PF / EPFO" },
    "esic.gov.in": { name: "ESIC Official Portal", state: "National / Central", category: "ESI / ESIC" },
    "egazette.gov.in": { name: "The Gazette of India", state: "National / Central", category: "Gazette / Notifications" },
    "labour.gujarat.gov.in": { name: "Gujarat Labour & Employment Dept", state: "Gujarat", category: "Gujarat Labour Law" },
  };

  function parseUrl(urlString) {
    try {
      const url = new URL(urlString.trim());
      const domain = url.hostname.replace(/^www\./, "").toLowerCase();
      const isSpecificArticle = url.pathname.length > 3 && url.pathname !== "/";

      // Detect known domain info or fallback
      const known = KNOWN_DOMAINS[domain] || {};
      const name = known.name || domain.charAt(0).toUpperCase() + domain.slice(1);
      const state = known.state || (domain.includes("gujarat") ? "Gujarat" : domain.includes("jk") || domain.includes("excelsior") ? "Jammu & Kashmir" : "National / Central");
      const category = known.category || "Labour Codes";

      const query = `site:${domain} (labour OR "labour codes" OR pf OR epfo OR esic OR gratuity OR "minimum wages" OR "gig workers")`;

      return {
        id: `src-${domain.replace(/\./g, "-")}`,
        domain,
        url: urlString.trim(),
        name,
        state,
        category,
        query,
        isSpecificArticle,
        active: true,
        added_at: new Date().toISOString().split("T")[0],
      };
    } catch (e) {
      return null;
    }
  }

  function getLocalSources() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    } catch {
      return [];
    }
  }

  function saveLocalSources(list) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
  }

  async function addSource(urlString) {
    const parsed = parseUrl(urlString);
    if (!parsed) {
      throw new Error("Invalid URL. Please enter a valid website or article link (e.g. https://www.dailyexcelsior.com/...)");
    }

    let sources = getLocalSources();
    // Check if already present
    const existingIndex = sources.findIndex((s) => s.domain === parsed.domain);
    if (existingIndex > -1) {
      sources[existingIndex] = { ...sources[existingIndex], ...parsed, active: true };
    } else {
      sources.unshift(parsed);
    }

    saveLocalSources(sources);

    // Sync with Supabase if connected
    if (typeof SupabaseManager !== "undefined") {
      await SupabaseManager.syncSourceToRemote(parsed);
    }

    return parsed;
  }

  function removeSource(sourceId) {
    let sources = getLocalSources().filter((s) => s.id !== sourceId);
    saveLocalSources(sources);
    return sources;
  }

  function toggleSource(sourceId) {
    let sources = getLocalSources();
    const target = sources.find((s) => s.id === sourceId);
    if (target) {
      target.active = !target.active;
      saveLocalSources(sources);
    }
    return sources;
  }

  return {
    parseUrl,
    getLocalSources,
    addSource,
    removeSource,
    toggleSource,
  };
})();
