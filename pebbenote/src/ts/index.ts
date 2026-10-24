import { ActionEditModel, AppClient } from "./api";
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
  return new AppClient({ BASE: getBaseUrl() });
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
    const note = await makeClient().notes.getNoteById(
      "default",
      Pebble.getAccountToken(),
    );
    PebbleTS.sendAppMessage({ ...encodeNote(note.content) });
  } catch (e) {
    console.error("Failed to fetch note", String(e));
    PebbleTS.sendAppMessage({ Result: "Backend unreachable" });
  }
}

async function deleteNoteLine(index: number) {
  const notes = makeClient().notes;
  const token = Pebble.getAccountToken();
  try {
    const note = await notes.getNoteById("default", token);
    const lines = note.content.split("\n");
    if (index >= 0 && index < lines.length) {
      lines.splice(index, 1);
    }
    const updated = await notes.editNoteById("default", token, {
      content: lines.join("\n"),
    });
    PebbleTS.sendAppMessage({ ...encodeNote(updated.content) });
  } catch (e) {
    console.error("Failed to delete line", String(e));
    PebbleTS.sendAppMessage({ Result: "Backend unreachable" });
  }
}

Pebble.addEventListener("showConfiguration", async () => {
  let notes: ConfigNote[] | null = null;
  try {
    notes = await makeClient().notes.listNotes(Pebble.getAccountToken());
  } catch (e) {
    console.error("Failed to list notes", String(e));
  }
  Pebble.openURL(configPageUrl(notes));
});

async function applyNoteChanges({ newNotes, defaultId }: ConfigResult) {
  const notes = makeClient().notes;
  const token = Pebble.getAccountToken();
  try {
    const createdIds: string[] = [];
    for (const content of newNotes ?? []) {
      createdIds.push((await notes.createNote(content, token)).note_id);
    }
    const target = defaultId?.startsWith("new:")
      ? createdIds[Number(defaultId.slice(4))]
      : defaultId;
    if (target) await notes.setDefaultNote(target, token);
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
    console.log("Got message", JSON.stringify(payload));
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
      response = await makeClient().actions.applyAction(
        Pebble.getAccountToken(),
        actionPayload,
      );
    } catch (err) {
      console.error("Failed to apply action", String(err));
      PebbleTS.sendAppMessage({ Result: "Backend unreachable" });
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
