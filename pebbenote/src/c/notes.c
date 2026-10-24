#include "notes.h"

#include <string.h>

// Cached note: one persist key for the line count, then one key per line
#define PERSIST_KEY_COUNT 1
#define PERSIST_KEY_LINE_BASE 100

uint8_t numberOfMessages = 0;
uint8_t selectedNote = 0;

struct MessageWithPrefix messages[MAX_MESSAGES];

void save_notes(void) {
  persist_write_int(PERSIST_KEY_COUNT, numberOfMessages);
  for (int i = 0; i < MAX_MESSAGES; i++) {
    uint32_t key = PERSIST_KEY_LINE_BASE + i;
    if (i >= numberOfMessages || messages[i].message == NULL) {
      persist_delete(key);
      continue;
    }
    // Format matches the inbox message: first byte is indent, then the cstring
    char buffer[PERSIST_DATA_MAX_LENGTH];
    size_t length = min(strlen(messages[i].message), sizeof(buffer) - 2);
    buffer[0] = messages[i].prefix;
    memcpy(buffer + 1, messages[i].message, length);
    buffer[length + 1] = '\0';
    persist_write_data(key, buffer, length + 2);
  }
}

bool load_notes(void) {
  if (!persist_exists(PERSIST_KEY_COUNT)) {
    return false;
  }
  int count = min(persist_read_int(PERSIST_KEY_COUNT), MAX_MESSAGES);
  int loaded = 0;
  for (int i = 0; i < count; i++) {
    char buffer[PERSIST_DATA_MAX_LENGTH];
    int size = persist_read_data(PERSIST_KEY_LINE_BASE + i, buffer, sizeof(buffer));
    if (size < 2) {
      break;
    }
    buffer[size - 1] = '\0';
    char* text = malloc(size - 1);
    if (text == NULL) {
      break;
    }
    memcpy(text, buffer + 1, size - 1);
    free(messages[i].message);
    messages[i].prefix = buffer[0];
    messages[i].message = text;
    loaded++;
  }
  numberOfMessages = loaded;
  selectedNote = 0;
  return loaded > 0;
}
