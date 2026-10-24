#pragma once

#include <pebble.h>

#define min(a, b) ((a) > (b) ? (b) : (a))

// Must match the Result[20] message key in package.json
#define MAX_MESSAGES 20

struct MessageWithPrefix {
  int8_t prefix;
  char* message;
  TextLayer* layer;
  int yOffset;
};

extern uint8_t numberOfMessages;
extern uint8_t selectedNote;
extern struct MessageWithPrefix messages[MAX_MESSAGES];

void save_notes(void);
// Fills messages[] from persistent storage, returns whether there was a cached note
bool load_notes(void);
