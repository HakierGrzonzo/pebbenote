import { ActionEditModel, AppClient } from "./api";
const keys = require("message_keys") as Record<string, number>;

const apiClient = new AppClient({
  BASE: "http://ryzenrig.koperwas.local:8000",
});

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

Pebble.addEventListener("ready", async () => {
  console.log("App Started 2");
  const notes = await apiClient.notes.listNotes(Pebble.getAccountToken());

  if (notes.length === 0) {
    PebbleTS.sendAppMessage({ Result: "No notes available" });
  }

  const note = notes[0];

  const message = encodeNote(note.content);
  PebbleTS.sendAppMessage({ ...message });

  Pebble.addEventListener("appmessage", async (e) => {
    const payload = e.payload;
    console.log("Got message", JSON.stringify(payload));
    const dictation: string | undefined = payload["Dictation"];
    if (!dictation) {
      console.error("dictation key is wrong?");
      return;
    }
    PebbleTS.sendAppMessage({ Result: "Sending to Ollama" });
    const actionPayload: ActionEditModel = {
      note_id: note.note_id,
      action: dictation,
    };
    const response = await apiClient.actions.applyAction(
      Pebble.getAccountToken(),
      actionPayload,
    );
    const message = encodeNote(response.content);

    console.log(message);

    PebbleTS.sendAppMessage({
      ...message,
      Vibe: 1,
    });
  });
});
