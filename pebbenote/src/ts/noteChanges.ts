import type { NoteModel } from "./api";
import type { ConfigResult } from "./config";

// The parts of the generated notes service the config page needs
export interface NoteChangesApi {
  createNote(content: string): Promise<NoteModel>;
  deleteNote(noteId: string): Promise<void>;
  setDefaultNote(noteId: string): Promise<NoteModel>;
}

// Applies what was chosen on the config page: new notes first, so a pending
// one can be made the default, then deletes. Deleting the default makes the
// backend pick the next one, unless another was chosen.
export async function applyNoteChanges(
  notes: NoteChangesApi,
  { newNotes, deletedIds, defaultId }: ConfigResult,
) {
  const createdIds: string[] = [];
  for (const content of newNotes ?? []) {
    createdIds.push((await notes.createNote(content)).note_id);
  }
  const deleted = deletedIds ?? [];
  for (const noteId of deleted) {
    await notes.deleteNote(noteId);
  }
  const target = defaultId?.startsWith("new:")
    ? createdIds[Number(defaultId.slice(4))]
    : defaultId;
  if (target && !deleted.includes(target)) await notes.setDefaultNote(target);
}
