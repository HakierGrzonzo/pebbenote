const rootUrl = "http://ryzenrig.koperwas.local:8000";

function getUrl<T>(
  method: "GET" | "POST",
  url: string,
  body: Object | null = null,
) {
  const request = new XMLHttpRequest();
  const target = rootUrl + url;
  return new Promise<T>((resolve, reject) => {
    request.onreadystatechange = (e) => {
      if (
        request.readyState === 4 &&
        request.status >= 200 &&
        request.status < 300
      ) {
        console.info(
          "request",
          method,
          target,
          request.status,
          request.response,
        );
        resolve(JSON.parse(request.response));
      }
      console.warn(JSON.stringify(e));
    };
    request.open(method, target);
    request.setRequestHeader("x-pebble-user-token", Pebble.getAccountToken());
    if (body === null) {
      request.send();
    } else {
      request.setRequestHeader("Content-Type", "application/json");
      const payload = JSON.stringify(body);
      console.log(payload);
      request.send(payload);
    }
  });
}

export interface Note {
  note_id: string;
  content: string;
}

export async function getSomeNote() {
  const data = await getUrl<Note[]>("GET", "/note/");
  const firstNote = data[0];
  return firstNote;
}

export async function postAction(noteId: string, dictation: string) {
  const response: Note = await getUrl("POST", "/action/", {
    ["note_id"]: noteId,
    action: dictation,
  });
  return response;
}
