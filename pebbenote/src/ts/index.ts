import { getSomeNote, postAction } from "./api";

Pebble.addEventListener("ready", async () => {
  console.log("App Started");
  const note = await getSomeNote();

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
    const response = await postAction(note.note_id, dictation);
    PebbleTS.sendAppMessage({
      Result: response.content.slice(0, 500),
      Vibe: 1,
    });
  });
});
