import { ActionEditModel, AppClient } from "./api";

const apiClient = new AppClient({
  BASE: "http://ryzenrig.koperwas.local:8000",
});

Pebble.addEventListener("ready", async () => {
  console.log("App Started");
  const notes = await apiClient.notes.listNotes(Pebble.getAccountToken());

  if (notes.length === 0) {
    PebbleTS.sendAppMessage({ Result: "No notes available" });
  }

  const note = notes[0];

  PebbleTS.sendAppMessage({ Result: note.content.slice(0, 500) });

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
    PebbleTS.sendAppMessage({
      Result: response.content.slice(0, 500),
      Vibe: 1,
    });
  });
});
