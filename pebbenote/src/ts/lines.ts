// A line deleted on the watch, with its place in the note the watch showed
export type DeletedLine = { text: string; index: number };

// Deletes lines by the watch's indexes, each relative to the lines left by
// the deletes before it, like the watch applied them
export function deleteLines(content: string, indexes: number[]) {
  const lines = content.split("\n").map((text, index) => ({ text, index }));
  const deleted: DeletedLine[] = [];
  for (const index of indexes) {
    if (index >= 0 && index < lines.length) {
      deleted.push(...lines.splice(index, 1));
    }
  }
  return { content: lines.map((line) => line.text).join("\n"), deleted };
}

// Deletes the same lines from a newer version of the note, where lines may
// have moved: each one where it is closest to its old place. A line that is
// gone or was changed is left alone.
export function rebaseDeletes(content: string, deleted: DeletedLine[]) {
  const lines = content.split("\n");
  const kept = lines.map(() => true);
  for (const { text, index } of deleted) {
    let best = -1;
    lines.forEach((line, i) => {
      if (!kept[i] || line !== text) return;
      if (best < 0 || Math.abs(i - index) < Math.abs(best - index)) best = i;
    });
    if (best >= 0) kept[best] = false;
  }
  return lines.filter((_, i) => kept[i]).join("\n");
}
