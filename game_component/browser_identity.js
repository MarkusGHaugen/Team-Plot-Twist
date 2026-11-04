const SAVE_KEY = "team-plot-twist-browser-save-v1";

function newId() {
  if (crypto.randomUUID) return crypto.randomUUID().replaceAll("-", "");
  return [...crypto.getRandomValues(new Uint8Array(16))]
    .map(byte => byte.toString(16).padStart(2, "0"))
    .join("");
}

export default function ({ data, setStateValue }) {
  // The game is authored in English; prevent browser translation of its controls.
  if (typeof document !== 'undefined' && document.documentElement && document.head) {
    document.documentElement.lang = 'en';
    document.documentElement.setAttribute('translate','no');
    document.documentElement.classList.add('notranslate');
    let meta=document.head.querySelector('meta[name="google"]');
    if(!meta){meta=document.createElement('meta');meta.name='google';document.head.append(meta);}
    meta.content='notranslate';
  }
  if (!data?.request_identity) return;
  let record = null;
  let storage_available = true;
  let stored = null;
  try {
    stored = localStorage.getItem(SAVE_KEY);
  } catch (_) {
    storage_available = false;
  }
  if (stored) {
    try { record = JSON.parse(stored); }
    catch (_) { record = null; }
  }
  if (!record || !/^[0-9a-f]{32}$/.test(record.id)) {
    record = { id: newId(), backup: null };
    if (storage_available) {
      try { localStorage.setItem(SAVE_KEY, JSON.stringify(record)); }
      catch (_) { storage_available = false; }
    }
  }
  setStateValue("identity", {
    id: record.id,
    backup: record.backup ?? null,
    storage_available,
  });
}
