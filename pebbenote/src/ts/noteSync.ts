import {
  ActionAcceptedModel,
  ActionEditModel,
  ActionModel,
  ActionStatus,
  ApiError,
  NoteConflictModel,
  NoteModel,
  NoteUpdateModel,
  NoteViewModel,
} from "./api";
import { deleteLines, rebaseDeletes } from "./lines";

// The parts of the generated services NoteSync uses, so tests can fake them
export interface NotesApi {
  listNotes(): Promise<NoteModel[]>;
  getNoteById(
    noteId: string,
    ifModifiedSince?: string | null,
  ): Promise<NoteViewModel>;
  editNoteById(noteId: string, edit: NoteUpdateModel): Promise<NoteModel>;
  setDefaultNote(noteId: string): Promise<NoteModel>;
}

export interface ActionsApi {
  applyAction(
    action: ActionEditModel,
  ): Promise<NoteModel | ActionAcceptedModel>;
}

export type WatchMessage = Record<string, string | number>;

export interface NoteSyncDeps {
  // A client with a fresh token, made for each request
  api(): { notes: NotesApi; actions: ActionsApi };
  // Sends an AppMessage to the watch
  send(message: WatchMessage): void;
  // The watch message keys for the lines of a note
  encode(content: string): WatchMessage;
  // Tells the watch about a failed request, signing out on a 401
  onFailure(e: unknown): void;
  sleep?(ms: number): Promise<unknown>;
}

// The backend answers 202 when the LLM takes too long, matching its Retry-After
const POLL_INTERVAL_MS = 2000;
// Without any change of the note for this long the AI is considered stuck
const POLL_TIMEOUT_MS = 3 * 60 * 1000;
// How often a delete is redone on a note that was changed in the meantime
const DELETE_ATTEMPTS = 3;

export function isPending(note: NoteViewModel) {
  // Not just the latest action: applying the instructions adds a done one
  // while dictated ones can still be queued
  return note.actions.some((a) => a.status === ActionStatus.PENDING);
}

// The action that finished last, the one the poller reports on
export function lastFinished(note: NoteViewModel) {
  const time = (a: ActionModel) => Date.parse(a.updated_at);
  return note.actions.reduce<ActionModel | undefined>(
    (latest, a) => (!latest || time(a) > time(latest) ? a : latest),
    undefined,
  );
}

export function isAccepted(
  response: NoteModel | ActionAcceptedModel,
): response is ActionAcceptedModel {
  return "note_last_modified" in response;
}

type Shown = { noteId: string | null; version: number; content: string };

// Keeps the watch showing the default note: loads it, applies dictations and
// line deletes to it, switches to other notes and polls while the AI works
export class NoteSync {
  // The note the watch shows. Responses can arrive out of order, an older
  // version of the note must not replace a newer one.
  shown: Shown = { noteId: null, version: 0, content: "" };
  // The note being polled
  polling: string | null = null;
  // Dictations are sent one after another, so the backend queues them in the
  // order they were spoken
  private dictations: Promise<void> = Promise.resolve();
  private readonly sleep: (ms: number) => Promise<unknown>;

  constructor(private readonly deps: NoteSyncDeps) {
    this.sleep =
      deps.sleep ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
  }

  async refresh() {
    try {
      const note = await this.deps.api().notes.getNoteById("default");
      const pending = isPending(note);
      this.sendNote(note, { Processing: pending ? 1 : 0 }, true);
      // Actions dictated before the app was closed
      if (pending) this.pollWhilePending(note.note_id);
    } catch (e) {
      console.error("Failed to fetch note", String(e));
      this.deps.onFailure(e);
    }
  }

  // Makes the note step places after the shown one the default and shows it,
  // wrapping around the list
  async switchNote(step: number) {
    try {
      const notes = this.deps.api().notes;
      const list = await notes.listNotes();
      let index = list.findIndex((n) => n.note_id === this.shown.noteId);
      if (index < 0) index = list.findIndex((n) => n.is_default);
      const count = list.length;
      const target = list[(((index + step) % count) + count) % count];
      if (count > 1 && target) await notes.setDefaultNote(target.note_id);
    } catch (e) {
      console.error("Failed to switch notes", String(e));
      this.deps.onFailure(e);
      return;
    }
    // Also with a single note: the watch waits for one
    await this.refresh();
  }

  queueDictation(dictation: string) {
    // The note it was spoken on, the watch may switch notes before it is sent
    const noteId = this.shown.noteId ?? "default";
    this.dictations = this.dictations.then(() =>
      this.applyDictation(noteId, dictation),
    );
    return this.dictations;
  }

  // Each index is relative to the note after the earlier deletes, like the
  // watch applied them to the note it showed
  async deleteLines(indexes: number[]) {
    // The note the lines were deleted from, "default" may point at another one
    const base = this.shown;
    const noteId = base.noteId;
    if (noteId === null) return;
    const notes = this.deps.api().notes;
    const { content, deleted } = deleteLines(base.content, indexes);
    let edit = { content, base_version: base.version };
    try {
      for (let attempt = 1; ; attempt++) {
        try {
          const updated = await notes.editNoteById(noteId, edit);
          // The watch drops notes while deletes are queued, maybe the poller's
          // last one: this one has to say whether actions are still running
          const processing = this.polling === noteId ? 1 : 0;
          this.sendIfShown(updated, { Processing: processing }, true);
          return;
        } catch (e) {
          const conflict = e instanceof ApiError && e.status === 409;
          if (!conflict || attempt >= DELETE_ATTEMPTS) throw e;
          // The note has changed since the watch got it: delete the same
          // lines, found by their text, from the new one
          const current = (e.body as NoteConflictModel).current;
          edit = {
            content: rebaseDeletes(current.content, deleted),
            base_version: current.version,
          };
        }
      }
    } catch (e) {
      console.error("Failed to delete line", String(e));
      this.deps.onFailure(e);
    }
  }

  // Sends the note unless the watch already has this version or a newer one.
  // With force the same version is sent again, for its extra keys. Says
  // whether it was sent.
  private sendNote(
    note: NoteModel,
    extra: WatchMessage = {},
    force = false,
  ): boolean {
    if (note.note_id === this.shown.noteId) {
      if (note.version < this.shown.version) return false;
      if (note.version === this.shown.version && !force) return false;
    }
    this.shown = {
      noteId: note.note_id,
      version: note.version,
      content: note.content,
    };
    this.deps.send({ ...this.deps.encode(note.content), ...extra });
    return true;
  }

  // Like sendNote, but drops a note the watch switched away from meanwhile
  private sendIfShown(
    note: NoteModel,
    extra: WatchMessage = {},
    force = false,
  ): boolean {
    if (this.isSwitchedFrom(note.note_id)) return false;
    return this.sendNote(note, extra, force);
  }

  private isSwitchedFrom(noteId: string) {
    return this.shown.noteId !== null && this.shown.noteId !== noteId;
  }

  // Polls the note in the background until the backend worker is done with
  // all of its actions, forwarding every change to the watch. One poller
  // serves any number of queued actions. After a switch the poller of the old
  // note stops on its next tick, the new note gets its own meanwhile.
  private async pollWhilePending(noteId: string, lastModified?: string) {
    if (this.polling === noteId) return;
    this.polling = noteId;
    try {
      await this.pollNote(noteId, lastModified);
    } finally {
      if (this.polling === noteId) this.polling = null;
    }
  }

  private async pollNote(noteId: string, lastModified?: string) {
    const notes = this.deps.api().notes;
    let deadline = Date.now() + POLL_TIMEOUT_MS;

    while (Date.now() < deadline) {
      await this.sleep(POLL_INTERVAL_MS);
      if (this.isSwitchedFrom(noteId)) return;

      let note: NoteViewModel | null = null;
      try {
        // The server answers 304 until the note changes again
        note = await notes.getNoteById(noteId, lastModified);
      } catch (err) {
        if (!(err instanceof ApiError && err.status === 304)) {
          console.error("Failed to poll the note", String(err));
          this.deps.onFailure(err);
          return;
        }
      }
      if (note === null) continue;
      // Switched while the request was running
      if (this.isSwitchedFrom(noteId)) return;
      // Changed: from now on only newer changes are news
      lastModified = note.last_modified;

      if (isPending(note)) {
        // An earlier action or something else changed the note
        if (note.version > this.shown.version) {
          deadline = Date.now() + POLL_TIMEOUT_MS;
        }
        this.sendIfShown(note, { Processing: 1 });
        continue;
      }

      if (lastFinished(note)?.status === ActionStatus.FAILED) {
        this.deps.send({ Status: "AI failed, try again" });
      } else {
        const done = { Vibe: 1, Processing: 0 };
        // A delete may have sent this version or a newer one already, the
        // banner has to go all the same. The watch takes keys only with a note.
        if (!this.sendIfShown(note, done, true)) {
          this.deps.send({ ...this.deps.encode(this.shown.content), ...done });
        }
      }
      return;
    }
    this.deps.send({ Status: "AI is taking too long" });
  }

  private async applyDictation(noteId: string, dictation: string) {
    let response;
    try {
      response = await this.deps
        .api()
        .actions.applyAction({ note_id: noteId, action: dictation });
    } catch (err) {
      console.error("Failed to apply action", String(err));
      this.deps.onFailure(err);
      return;
    }
    if (isAccepted(response)) {
      // Back to the note, more can be dictated while this is applied
      this.deps.send({ Processing: 1 });
      this.pollWhilePending(
        response.action.note_id,
        response.note_last_modified,
      );
      return;
    }
    this.sendIfShown(response, { Vibe: 1, Processing: 0 }, true);
  }
}
