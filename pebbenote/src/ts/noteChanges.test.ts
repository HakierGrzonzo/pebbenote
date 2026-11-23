import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";

import { NoteModel } from "./api";
import { ConfigResult } from "./config";
import { NoteChangesApi, applyNoteChanges } from "./noteChanges";

function note(noteId: string): NoteModel {
  return {
    note_id: noteId,
    content: "",
    is_default: false,
    updated_at: new Date().toISOString(),
    version: 1,
  };
}

function result(changes: Partial<ConfigResult>): ConfigResult {
  return {
    backendUrl: "",
    newNotes: [],
    deletedIds: [],
    defaultId: null,
    ...changes,
  };
}

describe("applyNoteChanges", () => {
  let calls: string[];
  let api: NoteChangesApi;

  beforeEach(() => {
    calls = [];
    let created = 0;
    api = {
      createNote: async (content) => {
        calls.push(`create ${content}`);
        return note(`created-${created++}`);
      },
      deleteNote: async (noteId) => {
        calls.push(`delete ${noteId}`);
      },
      setDefaultNote: async (noteId) => {
        calls.push(`default ${noteId}`);
        return note(noteId);
      },
    };
  });

  it("creates, then deletes, then sets the default", async () => {
    await applyNoteChanges(
      api,
      result({ newNotes: ["a"], deletedIds: ["x", "y"], defaultId: "z" }),
    );

    assert.deepEqual(calls, ["create a", "delete x", "delete y", "default z"]);
  });

  it("makes a new note the default", async () => {
    await applyNoteChanges(
      api,
      result({ newNotes: ["a", "b"], defaultId: "new:1" }),
    );

    assert.deepEqual(calls, ["create a", "create b", "default created-1"]);
  });

  it("does not make a deleted note the default", async () => {
    await applyNoteChanges(api, result({ deletedIds: ["x"], defaultId: "x" }));

    assert.deepEqual(calls, ["delete x"]);
  });

  it("accepts a result from before deletes", async () => {
    const old = { backendUrl: "", newNotes: [], defaultId: "z" };

    await applyNoteChanges(api, old as unknown as ConfigResult);

    assert.deepEqual(calls, ["default z"]);
  });
});
