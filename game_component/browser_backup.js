const SAVE_KEY = "team-plot-twist-browser-save-v1";

export default function ({ data }) {
  if (!data?.player_id) return;
  try {
    localStorage.setItem(SAVE_KEY, JSON.stringify({
      id: data.player_id,
      backup: data.state ?? null,
    }));
  } catch (_) {
    // The app warns when browser storage is unavailable at first load.
  }
}
