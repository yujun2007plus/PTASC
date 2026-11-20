const DB_NAME = "ptasc";
const STORE = "media";
const MODE_KEY = "ptasc-mode";

let opening = null;
const tails = {
  image: Promise.resolve(),
  video: Promise.resolve(),
};

function openDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      const database = request.result;
      if (!database.objectStoreNames.contains(STORE)) {
        database.createObjectStore(STORE);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function database() {
  if (!opening) {
    opening = openDb().catch((error) => {
      opening = null;
      throw error;
    });
  }
  return opening;
}

function asFile(record) {
  if (!record || !record.blob) {
    return null;
  }
  if (record.blob instanceof File) {
    return record.blob;
  }
  return new File([record.blob], record.name || "file", {
    type: record.type || record.blob.type || "",
  });
}

async function write(kind, file) {
  const db = await database();
  await new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(
      { blob: file, name: file.name, type: file.type },
      kind,
    );
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
    tx.onabort = () => reject(tx.error || new Error("cache aborted"));
  });
}

export function saveMedia(kind, file) {
  const job = tails[kind].then(
    () => write(kind, file),
    () => write(kind, file),
  );
  tails[kind] = job.catch(() => {});
  return job;
}

export async function loadMedia(kind) {
  try {
    const db = await database();
    const record = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const request = tx.objectStore(STORE).get(kind);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });
    return asFile(record);
  } catch {
    return null;
  }
}

export function saveMode(mode) {
  try {
    localStorage.setItem(MODE_KEY, mode);
  } catch {
    /* private mode can reject storage */
  }
}

export function loadMode() {
  try {
    return localStorage.getItem(MODE_KEY) === "video" ? "video" : "image";
  } catch {
    return "image";
  }
}
