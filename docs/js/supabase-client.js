/**
 * Supabase Client Integration Layer
 * ---------------------------------
 * Handles Auth (Sign Up, Sign In, Sign Out, User Session)
 * and Database Syncing (Articles, Custom Sources, Bookmarks).
 */

const SupabaseManager = (function () {
  // Storage keys for configuration
  const STORAGE_KEYS = {
    URL: "labour_tracker_supabase_url",
    KEY: "labour_tracker_supabase_key",
    USER: "labour_tracker_user",
    BOOKMARKS: "labour_tracker_bookmarks_local",
    CUSTOM_SOURCES: "labour_tracker_sources_local",
  };

  let client = null;
  let currentUser = null;
  let authListeners = [];

  function getConfig() {
    return {
      url: localStorage.getItem(STORAGE_KEYS.URL) || "",
      key: localStorage.getItem(STORAGE_KEYS.KEY) || "",
    };
  }

  function saveConfig(url, key) {
    if (url && key) {
      localStorage.setItem(STORAGE_KEYS.URL, url.trim());
      localStorage.setItem(STORAGE_KEYS.KEY, key.trim());
      initClient();
      return true;
    }
    return false;
  }

  function isConfigured() {
    const config = getConfig();
    return Boolean(config.url && config.key);
  }

  function initClient() {
    const config = getConfig();
    if (config.url && config.key && window.supabase) {
      try {
        client = window.supabase.createClient(config.url, config.key);
        // Check current session
        client.auth.getSession().then(({ data: { session } }) => {
          currentUser = session?.user || null;
          notifyAuthListeners(currentUser);
        });

        client.auth.onAuthStateChange((event, session) => {
          currentUser = session?.user || null;
          notifyAuthListeners(currentUser);
        });
        return client;
      } catch (e) {
        console.warn("Supabase initialisation failed:", e);
      }
    }
    return null;
  }

  function onAuthChange(callback) {
    if (typeof callback === "function") {
      authListeners.push(callback);
      callback(currentUser);
    }
  }

  function notifyAuthListeners(user) {
    authListeners.forEach((fn) => {
      try {
        fn(user);
      } catch (e) {
        console.error("Auth listener error:", e);
      }
    });
  }

  async function signUp(email, password) {
    if (!client) {
      // Local fallback simulation if Supabase is not connected
      const mockUser = { id: "local-" + Date.now(), email: email, is_local: true };
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(mockUser));
      currentUser = mockUser;
      notifyAuthListeners(currentUser);
      return { user: mockUser, error: null };
    }
    try {
      const { data, error } = await client.auth.signUp({
        email,
        password,
      });
      if (error) throw error;
      currentUser = data.user;
      notifyAuthListeners(currentUser);
      return { user: data.user, error: null };
    } catch (err) {
      return { user: null, error: err.message };
    }
  }

  async function signIn(email, password) {
    if (!client) {
      // Local fallback simulation
      const mockUser = { id: "local-" + Date.now(), email: email, is_local: true };
      localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(mockUser));
      currentUser = mockUser;
      notifyAuthListeners(currentUser);
      return { user: mockUser, error: null };
    }
    try {
      const { data, error } = await client.auth.signInWithPassword({
        email,
        password,
      });
      if (error) throw error;
      currentUser = data.user;
      notifyAuthListeners(currentUser);
      return { user: data.user, error: null };
    } catch (err) {
      return { user: null, error: err.message };
    }
  }

  async function signOut() {
    if (client) {
      try {
        await client.auth.signOut();
      } catch (e) {
        console.error("Sign out error:", e);
      }
    }
    localStorage.removeItem(STORAGE_KEYS.USER);
    currentUser = null;
    notifyAuthListeners(null);
  }

  // Database helpers
  async function fetchRemoteArticles() {
    if (!client) return null;
    try {
      const { data, error } = await client
        .from("articles")
        .select("*")
        .order("added_date", { ascending: false });
      if (error) throw error;
      return data;
    } catch (e) {
      console.warn("Failed to fetch remote Supabase articles:", e);
      return null;
    }
  }

  async function syncArticleToRemote(article) {
    if (!client) return false;
    try {
      const { error } = await client.from("articles").upsert([article], { onConflict: "id" });
      if (error) throw error;
      return true;
    } catch (e) {
      console.warn("Failed to sync article to Supabase:", e);
      return false;
    }
  }

  async function fetchRemoteSources() {
    if (!client) return null;
    try {
      const { data, error } = await client.from("custom_sources").select("*");
      if (error) throw error;
      return data;
    } catch (e) {
      console.warn("Failed to fetch Supabase custom sources:", e);
      return null;
    }
  }

  async function syncSourceToRemote(source) {
    if (!client) return false;
    try {
      const { error } = await client.from("custom_sources").upsert([source], { onConflict: "id" });
      if (error) throw error;
      return true;
    } catch (e) {
      console.warn("Failed to sync source to Supabase:", e);
      return false;
    }
  }

  // Bookmarks Helper
  function getLocalBookmarks() {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEYS.BOOKMARKS) || "[]");
    } catch {
      return [];
    }
  }

  function toggleLocalBookmark(articleId) {
    let list = getLocalBookmarks();
    const index = list.indexOf(articleId);
    let bookmarked = false;
    if (index > -1) {
      list.splice(index, 1);
      bookmarked = false;
    } else {
      list.push(articleId);
      bookmarked = true;
    }
    localStorage.setItem(STORAGE_KEYS.BOOKMARKS, JSON.stringify(list));
    return { list, isBookmarked: bookmarked };
  }

  // Initialize on load
  document.addEventListener("DOMContentLoaded", () => {
    initClient();
  });

  return {
    getConfig,
    saveConfig,
    isConfigured,
    initClient,
    onAuthChange,
    getCurrentUser: () => currentUser,
    signUp,
    signIn,
    signOut,
    fetchRemoteArticles,
    syncArticleToRemote,
    fetchRemoteSources,
    syncSourceToRemote,
    getLocalBookmarks,
    toggleLocalBookmark,
  };
})();
