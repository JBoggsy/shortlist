import { useState } from "react";

const STATE = {
  AVAILABLE: "available",
  DOWNLOADING: "downloading",
  READY: "ready",
};

export default function UpdateBanner({ update, onDismiss }) {
  const [state, setState] = useState(STATE.AVAILABLE);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);

  async function handleUpdate() {
    setState(STATE.DOWNLOADING);
    setError(null);
    try {
      let totalBytes = 0;
      let downloadedBytes = 0;
      await update.downloadAndInstall((event) => {
        if (event.event === "Started" && event.data?.contentLength) {
          totalBytes = event.data.contentLength;
        } else if (event.event === "Progress") {
          downloadedBytes += event.data.chunkLength;
          if (totalBytes > 0) {
            setProgress(Math.round((downloadedBytes / totalBytes) * 100));
          }
        } else if (event.event === "Finished") {
          setProgress(100);
        }
      });
      setState(STATE.READY);
    } catch (err) {
      console.error("Update failed:", err);
      setError(err.message || "Update failed");
      setState(STATE.AVAILABLE);
    }
  }

  async function handleRestart() {
    const { relaunch } = await import("@tauri-apps/plugin-process");
    await relaunch();
  }

  if (state === STATE.READY) {
    return (
      <div className="bg-green-600 text-white px-4 py-2 flex items-center justify-center gap-4 text-sm">
        <span>Update downloaded! Restart to apply.</span>
        <button
          onClick={handleRestart}
          className="px-3 py-1 bg-white text-green-700 rounded font-medium hover:bg-green-50"
        >
          Restart Now
        </button>
      </div>
    );
  }

  if (state === STATE.DOWNLOADING) {
    return (
      <div className="bg-indigo-600 text-white px-4 py-2 flex items-center justify-center gap-4 text-sm">
        <span>Downloading update...</span>
        <div className="w-48 bg-indigo-400 rounded-full h-2">
          <div
            className="bg-white h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="tabular-nums">{progress}%</span>
      </div>
    );
  }

  return (
    <div className="bg-indigo-600 text-white px-4 py-2 flex items-center justify-center gap-4 text-sm">
      <span>
        Version {update.version} is available!
      </span>
      {error && <span className="text-amber-200">{error}</span>}
      <button
        onClick={handleUpdate}
        className="px-3 py-1 bg-white text-indigo-700 rounded font-medium hover:bg-indigo-50"
      >
        Update Now
      </button>
      <button
        onClick={onDismiss}
        className="px-3 py-1 text-indigo-200 hover:text-white"
      >
        Later
      </button>
    </div>
  );
}
