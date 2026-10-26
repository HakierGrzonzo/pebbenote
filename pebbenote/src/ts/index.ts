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
function isAuthError(e: unknown) {
  return (
    e instanceof NotSignedInError || (e instanceof ApiError && e.status === 401)
  );
}

// The watch shows sign in directions for SignInRequired, text otherwise
function sendFailure(e: unknown) {
  if (e instanceof ApiError && e.status === 401) signOut();
  if (isAuthError(e)) PebbleTS.sendAppMessage({ SignInRequired: 1 });
  else PebbleTS.sendAppMessage({ Status: "Backend unreachable" });
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
    sendFailure(e);
  }
}

// Each index is relative to the note after the earlier deletes, like the watch applied them
async function deleteNoteLines(indexes: number[]) {
  const notes = makeClient().notes;
  try {
    const note = await notes.getNoteById("default");
    const lines = note.content.split("\n");
    for (const index of indexes) {
      if (index >= 0 && index < lines.length) {
        lines.splice(index, 1);
      }
    }
    const updated = await notes.editNoteById("default", {
      content: lines.join("\n"),
    });
    PebbleTS.sendAppMessage({ ...encodeNote(updated.content) });
  } catch (e) {
    console.error("Failed to delete line", String(e));
    sendFailure(e);
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
      if (isAuthError(e)) {
        if (e instanceof ApiError) signOut();
        signInUrl = await beginSignIn();
      }
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
    // The watch sends a byte array of batched indexes
    const deleteLine: number[] | number | undefined = payload["DeleteLine"];
    if (deleteLine !== undefined) {
      await deleteNoteLines(
        Array.isArray(deleteLine) ? deleteLine : [deleteLine],
      );
      return;
    }
    const dictation: string | undefined = payload["Dictation"];
    if (!dictation) {
      console.error("dictation key is wrong?");
      return;
    }
    const actionPayload: ActionEditModel = {
      note_id: "default",
      action: dictation,
    };
    let response;
    try {
      response = await makeClient().actions.applyAction(actionPayload);
    } catch (err) {
      console.error("Failed to apply action", String(err));
      sendFailure(err);
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
