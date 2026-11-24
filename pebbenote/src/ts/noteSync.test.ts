import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";

import {
  ActionEditModel,
  ActionModel,
  ActionStatus,
  ApiError,
  NoteModel,
  NoteUpdateModel,
  NoteViewModel,
} from "./api";
import type { ApiRequestOptions } from "./api/core/ApiRequestOptions";
import { ActionsApi, NoteSync, NotesApi, WatchMessage } from "./noteSync";

// Lets pending promise callbacks and awaits run
const flush = () => new Promise((resolve) => setImmediate(resolve));

function apiError(status: number, body: unknown = null) {
  const request: ApiRequestOptions = { method: "GET", url: "" };
  return new ApiError(
    request,
    { url: "", ok: false, status, statusText: "", body },
    `HTTP ${status}`,
  );
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => (resolve = r));
  return { promise, resolve };
}

function action(noteId: string, status: ActionStatus): ActionModel {
  const now = new Date().toISOString();
  return {
    note_action_id: `${noteId}-action`,
    note_id: noteId,
    action: "something",
    status,
    created_at: now,
    updated_at: now,
  };
}

function toModel(note: NoteViewModel): NoteModel {
  const { note_id, content, title, is_default, updated_at, version } = note;
  return { note_id, content, title, is_default, updated_at, version };
}

// An in-memory backend and watch. The encoded note is just its content, under
// Content, so tests read what the watch shows from the sent messages.
class Fake {
  notes: NoteViewModel[] = [];
  sent: WatchMessage[] = [];
  failures: unknown[] = [];
  edits: string[] = [];
  appliedTo: string[] = [];
  private sleeping: (() => void)[] = [];

  addNote(note_id: string, content: string, version = 1) {
    this.notes.push({
      note_id,
      content,
      title: content.split("\n")[0],
      version,
      is_default: this.notes.length === 0,
      updated_at: new Date().toISOString(),
      actions: [],
      last_modified: `${note_id} v${version}`,
    });
  }

  note(id: string) {
    const note = this.notes.find((n) =>
      id === "default" ? n.is_default : n.note_id === id,
    );
    if (!note) throw apiError(404);
    return note;
  }

  // Changes a note like the backend would, for the poller to notice
  change(id: string, changes: Partial<NoteViewModel>) {
    const note = this.note(id);
    Object.assign(note, changes);
    note.last_modified = `${id} v${note.version} ${Math.random()}`;
  }

  notesApi: NotesApi = {
    listNotes: async () => this.notes.map(toModel),
    getNoteById: async (id, ifModifiedSince) => {
      const note = this.note(id);
      if (ifModifiedSince === note.last_modified) throw apiError(304);
      return structuredClone(note);
    },
    editNoteById: async (id: string, edit: NoteUpdateModel) =>
      this.editNote(id, edit),
    setDefaultNote: async (id) => {
      for (const n of this.notes) n.is_default = n.note_id === id;
      return toModel(this.note(id));
    },
  };

  async editNote(id: string, edit: NoteUpdateModel) {
    this.edits.push(id);
    const note = this.note(id);
    if (edit.base_version != null && edit.base_version !== note.version) {
      throw apiError(409, { detail: "conflict", current: toModel(note) });
    }
    this.change(id, { content: edit.content, version: note.version + 1 });
    return toModel(note);
  }

  actionsApi: ActionsApi = {
    applyAction: async (payload: ActionEditModel) => this.applyAction(payload),
  };

  // Applies a dictation right away: the 200 answer
  async applyAction({ note_id, action }: ActionEditModel) {
    this.appliedTo.push(note_id);
    const note = this.note(note_id);
    this.change(note.note_id, {
      content: `${note.content}\n${action}`,
      version: note.version + 1,
    });
    return toModel(note);
  }

  sync = new NoteSync({
    api: () => ({ notes: this.notesApi, actions: this.actionsApi }),
    send: (message) => this.sent.push(message),
    encode: (content) => ({ Content: content }),
    onFailure: (e) => this.failures.push(e),
    sleep: () => new Promise<void>((resolve) => this.sleeping.push(resolve)),
  });

  // Ends the poll interval of every poller
  async tick() {
    for (const wake of this.sleeping.splice(0)) wake();
    await flush();
  }

  // What the watch shows: the last note sent
  get shown() {
    return this.sent.findLast((m) => "Content" in m)?.Content;
  }

  get last() {
    return this.sent[this.sent.length - 1];
  }
}

let fake: Fake;

beforeEach(async () => {
  fake = new Fake();
  fake.addNote("a", "A");
  fake.addNote("b", "B");
  fake.addNote("c", "C");
});

describe("switchNote", () => {
  it("steps through the list and wraps both ways", async () => {
    await fake.sync.refresh();
    assert.equal(fake.shown, "A");

    const seen = [];
    for (const step of [1, 1, 1, -1, -1]) {
      await fake.sync.switchNote(step);
      seen.push(fake.shown);
    }

    assert.deepEqual(seen, ["B", "C", "A", "C", "B"]);
    assert.equal(fake.note("default").note_id, "b");
  });

  it("resends the note when there is no other", async () => {
    fake.notes = fake.notes.slice(0, 1);
    await fake.sync.refresh();

    await fake.sync.switchNote(1);

    assert.equal(fake.sent.length, 2);
    assert.equal(fake.shown, "A");
  });

  it("reports a failed list", async () => {
    await fake.sync.refresh();
    fake.notesApi.listNotes = async () => {
      throw apiError(500);
    };

    await fake.sync.switchNote(1);

    assert.equal(fake.failures.length, 1);
    assert.equal(fake.sent.length, 1);
  });
});

describe("after a switch", () => {
  it("drops the result of a delete on the old note", async () => {
    await fake.sync.refresh();
    const edit = deferred<void>();
    const editNote = fake.notesApi.editNoteById;
    fake.notesApi.editNoteById = async (id, body) => {
      await edit.promise;
      return editNote(id, body);
    };

    const deleting = fake.sync.deleteLines([0]);
    await fake.sync.switchNote(1);
    edit.resolve();
    await deleting;

    assert.equal(fake.note("a").content, "");
    assert.equal(fake.shown, "B");
  });

  it("applies a queued dictation to the note it was spoken on", async () => {
    await fake.sync.refresh();
    const first = deferred<void>();
    fake.actionsApi.applyAction = async (payload) => {
      await first.promise;
      return fake.applyAction(payload);
    };

    fake.sync.queueDictation("one");
    const dictations = fake.sync.queueDictation("two");
    await fake.sync.switchNote(1);
    first.resolve();
    await dictations;

    assert.deepEqual(fake.appliedTo, ["a", "a"]);
    assert.equal(fake.note("a").content, "A\none\ntwo");
    assert.equal(fake.shown, "B");
  });

  it("polls the new note while the old poller sleeps", async () => {
    fake.change("a", { actions: [action("a", ActionStatus.PENDING)] });
    fake.change("b", { actions: [action("b", ActionStatus.PENDING)] });
    await fake.sync.refresh();
    assert.equal(fake.sync.polling, "a");

    await fake.sync.switchNote(1);
    assert.equal(fake.sync.polling, "b");

    // The old poller stops, the new one keeps its claim
    await fake.tick();
    assert.equal(fake.sync.polling, "b");

    fake.change("b", {
      content: "B done",
      version: 2,
      actions: [action("b", ActionStatus.DONE)],
    });
    await fake.tick();

    assert.equal(fake.shown, "B done");
    assert.deepEqual(fake.last, { Content: "B done", Vibe: 1, Processing: 0 });
    assert.equal(fake.sync.polling, null);
  });
});

describe("sending notes", () => {
  it("drops an older version of the shown note", async () => {
    fake.change("a", { version: 3 });
    await fake.sync.refresh();
    fake.actionsApi.applyAction = async () => ({
      ...toModel(fake.note("a")),
      content: "stale",
      version: 2,
    });

    await fake.sync.queueDictation("x");

    assert.equal(fake.sent.length, 1);
    assert.equal(fake.shown, "A");
  });

  it("reports a failed action as such", async () => {
    fake.change("a", { actions: [action("a", ActionStatus.PENDING)] });
    await fake.sync.refresh();

    fake.change("a", { actions: [action("a", ActionStatus.FAILED)] });
    await fake.tick();

    assert.deepEqual(fake.last, { Status: "AI failed, try again" });
    assert.equal(fake.sync.polling, null);
  });
});

describe("deleteLines", () => {
  it("redoes the delete on a note changed meanwhile", async () => {
    fake.change("a", { content: "a\nb\nc" });
    await fake.sync.refresh();
    fake.change("a", { content: "new\na\nb\nc", version: 2 });

    await fake.sync.deleteLines([1]);

    assert.equal(fake.note("a").content, "new\na\nc");
    assert.equal(fake.shown, "new\na\nc");
    assert.deepEqual(fake.edits, ["a", "a"]);
  });

  it("gives up after three conflicts", async () => {
    await fake.sync.refresh();
    fake.notesApi.editNoteById = async (id) => {
      fake.edits.push(id);
      throw apiError(409, { current: toModel(fake.note(id)) });
    };

    await fake.sync.deleteLines([0]);

    assert.equal(fake.edits.length, 3);
    assert.equal(fake.failures.length, 1);
  });
});
