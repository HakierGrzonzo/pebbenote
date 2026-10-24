import { ActionEditModel, ApiError, AppClient } from "./api";
import {
  NotSignedInError,
  getAccessToken,
  isSignedIn,
  pollDeviceFlow,
  signOut,
  startDeviceFlow,
} from "./auth";
const keys = require("message_keys") as Record<string, number>;

import {
  ConfigNote,
  ConfigResult,
  configPageUrl,
  getBaseUrl,
  isValidUrl,
  setBaseUrl,
} from "./config";

function makeClient() {
  return new AppClient({ BASE: getBaseUrl(), TOKEN: getAccessToken });
}

// A 401 despite a fresh token means the session is gone server side
function failureMessage(e: unknown) {
  if (e instanceof ApiError && e.status === 401) signOut();
  if (
    e instanceof NotSignedInError ||
    (e instanceof ApiError && e.status === 401)
  )
    return "Sign in via settings";
  return "Backend unreachable";
}

function encodeNote(note: string) {
  const points = note.split("\n");
  const message = Object.fromEntries(
    points.map((text, index) => {
      const indentationNumber = text.length - text.trimStart().length;
      const encodedText = text.trim().replace("- ", "");
      return [
        keys.Result + index,
        String.fromCodePoint(indentationNumber) + encodedText,
      ];
    }),
  );
  return { ...message, NumberOfLines: points.length };
}

async function refreshNote() {
  try {
    const note = await makeClient().notes.getNoteById("default");
    PebbleTS.sendAppMessage({ ...encodeNote(note.content) });
  } catch (e) {
    console.error("Failed to fetch note", String(e));
    PebbleTS.sendAppMessage({ Result: failureMessage(e) });
  }
}

async function deleteNoteLine(index: number) {
  const notes = makeClient().notes;
  try {
    const note = await notes.getNoteById("default");
    const lines = note.content.split("\n");
    if (index >= 0 && index < lines.length) {
      lines.splice(index, 1);
    }
    const updated = await notes.editNoteById("default", {
      content: lines.join("\n"),
    });
    PebbleTS.sendAppMessage({ ...encodeNote(updated.content) });
  } catch (e) {
    console.error("Failed to delete line", String(e));
    PebbleTS.sendAppMessage({ Result: failureMessage(e) });
  }
}

Pebble.addEventListener("showConfiguration", async () => {
  let notes: ConfigNote[] | null = null;
  let signInUrl: string | null = null;
  if (isSignedIn()) {
    try {
      notes = await makeClient().notes.listNotes();
    } catch (e) {
      console.error("Failed to list notes", String(e));
      if (failureMessage(e) === "Sign in via settings")
        signInUrl = await beginSignIn();
    }
  } else {
    signInUrl = await beginSignIn();
  }
  Pebble.openURL(configPageUrl(notes, signInUrl));
});

// Returns the url the user has to open to approve this device. Polling
// continues in the background and refreshes the note once approved.
async function beginSignIn(): Promise<string | null> {
  try {
    const flow = await startDeviceFlow();
    pollDeviceFlow(flow).then((signedIn) => {
      if (signedIn) refreshNote();
    });
    return flow.verification_uri_complete;
  } catch (e) {
    console.error("Failed to start sign in", String(e));
    return null;
  }
}

async function applyNoteChanges({ newNotes, defaultId }: ConfigResult) {
  const notes = makeClient().notes;
  try {
    const createdIds: string[] = [];
    for (const content of newNotes ?? []) {
      createdIds.push((await notes.createNote(content)).note_id);
    }
    const target = defaultId?.startsWith("new:")
      ? createdIds[Number(defaultId.slice(4))]
      : defaultId;
    if (target) await notes.setDefaultNote(target);
  } catch (e) {
    console.error("Failed to apply note changes", String(e));
  }
}

// pkts typings omit the config-page close event
type WebViewClosedEvent = { type: "webviewclosed"; response?: string };

(
  Pebble.addEventListener as (
    event: "webviewclosed",
    callback: (e: WebViewClosedEvent) => void,
  ) => void
)("webviewclosed", async (e) => {
  if (!e.response) return;
  try {
    const result: ConfigResult = JSON.parse(decodeURIComponent(e.response));
    const { backendUrl } = result;
    if (backendUrl && !isValidUrl(backendUrl)) {
      console.error("Invalid backend url", backendUrl);
      return;
    }
    setBaseUrl(backendUrl || "");
    await applyNoteChanges(result);
  } catch (err) {
    console.error("Bad config response", String(err));
    return;
  }
  await refreshNote();
});

Pebble.addEventListener("ready", async () => {
  console.log("App Started 2");
  await refreshNote();

  Pebble.addEventListener("appmessage", async (e) => {
    const payload = e.payload;
    const deleteLine: number | undefined = payload["DeleteLine"];
    if (deleteLine !== undefined) {
      await deleteNoteLine(deleteLine);
      return;
    }
    const dictation: string | undefined = payload["Dictation"];
    if (!dictation) {
      console.error("dictation key is wrong?");
      return;
    }
    PebbleTS.sendAppMessage({ Result: "Sending to Ollama" });
    const actionPayload: ActionEditModel = {
      note_id: "default",
      action: dictation,
    };
    let response;
    try {
      response = await makeClient().actions.applyAction(actionPayload);
    } catch (err) {
      console.error("Failed to apply action", String(err));
      PebbleTS.sendAppMessage({ Result: failureMessage(err) });
      return;
    }
    const message = encodeNote(response.content);

    console.log(message);

    PebbleTS.sendAppMessage({
      ...message,
      Vibe: 1,
    });
  });
});
