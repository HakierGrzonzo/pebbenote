#pragma once

#include <pebble.h>

// Opens AppMessage and creates the dictation session
void comm_init(void);
void comm_deinit(void);

// True while the phone reported that the user has to sign in
bool comm_sign_in_required(void);

void start_dictation(void);
// Queues a line delete, the batch is sent after a short pause in deleting
void queue_delete_line(uint8_t index);
