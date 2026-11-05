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
// Exits the app, first sending queued deletes and waiting for the phone to confirm them
void comm_flush_and_exit(void);
// True once comm_flush_and_exit() is waiting for the phone
bool comm_is_exiting(void);
