const rootUrl = "http://ryzenrig.koperwas.local:8000"

function getUrl<T>(method: "GET" | "POST", url: string, body: Object | null = null) {
  const request = new XMLHttpRequest()
  const target = rootUrl + url
  return new Promise<T>((resolve, reject) => {
    request.onreadystatechange = (e) => {
      if (request.readyState === 4) {
        console.info("Request", method, target, request.status)
        resolve(JSON.parse(request.response))
      }
    }
    request.open(method, target)
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

const messageKey = 0x0

Pebble.addEventListener("ready", async (e) => {
  const note = await getSomeNote()
  console.log(note.content)


  Pebble.addEventListener('appmessage', async (e) => {
    const payload = e.payload;
    console.log("Got message", JSON.stringify(payload))
    const dictation: string | undefined = payload[messageKey]
    if (!dictation) {
      console.error("dictation key is wrong?")
      return
    }
    const response = await getUrl("POST", "/action/", {
      ["note_id"]: note.note_id,
      action: dictation
    })
    console.log(JSON.stringify(response))
  })
})

