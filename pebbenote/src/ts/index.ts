const rootUrl = "http://ryzenrig.koperwas.local:8000"


function getUrl<T>(method: "GET" | "POST", url: string, body: Object | null = null) {
  const request = new XMLHttpRequest()
  const target = rootUrl + url
  return new Promise<T>((resolve, reject) => {
    request.onreadystatechange = (e) => {
      if (request.readyState === 4 && request.status >= 200 && request.status < 300) {
        console.info("request", method, target, request.status, request.response)
        resolve(JSON.parse(request.response))
      }
      console.warn(JSON.stringify(e))
    }
    request.open(method, target)
    request.setRequestHeader("x-pebble-user-token", Pebble.getAccountToken())
    if (body === null) {
      request.send()
    } else {
      request.setRequestHeader("Content-Type", "application/json")
      const payload = JSON.stringify(body)
      console.log(payload)
      request.send(payload)
    }
  })
}

interface Note {
  note_id: string
  content: string
}

async function getSomeNote() {
  const data = await getUrl<Note[]>("GET", "/note/")
  const firstNote = data[0]
  return firstNote
}


Pebble.addEventListener("ready", async (e) => {
  console.log("App Started")
  const note = await getSomeNote()

  PebbleTS.sendAppMessage({"Result": note.content.slice(0, 500)})

  Pebble.addEventListener('appmessage', async (e) => {
    const payload = e.payload;
    console.log("Got message", JSON.stringify(payload))
    const dictation: string | undefined = payload["Dictation"]
    if (!dictation) {
      console.error("dictation key is wrong?")
      return
    }
    PebbleTS.sendAppMessage({"Result": "Sending to Ollama"})
    const response: Note = await getUrl("POST", "/action/", {
      ["note_id"]: note.note_id,
      action: dictation
    })
    PebbleTS.sendAppMessage({"Result": response.content.slice(0, 500), "Vibe": 1})
  })
})

