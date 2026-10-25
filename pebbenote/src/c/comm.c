#include "comm.h"

#include <string.h>

#include "notes.h"
#include "ui.h"

static DictationSession *s_dictation_session;
static bool s_sign_in_required;

// Largest expected inbox and outbox message sizes
static const uint32_t inbox_size = 2048;
static const uint32_t outbox_size = 512;

static void send_dictation(char* transcription) {
  DictionaryIterator *out_iter;
  AppMessageResult result = app_message_outbox_begin(&out_iter);

  if (result != APP_MSG_OK) {
    APP_LOG(APP_LOG_LEVEL_ERROR, "Failed to app_message_outbox_begin");
    return;
  }
  dict_write_cstring(out_iter, MESSAGE_KEY_Dictation, transcription);
  dict_write_end(out_iter);

  result = app_message_outbox_send();
  if (result != APP_MSG_OK) {
    APP_LOG(APP_LOG_LEVEL_ERROR, "Failed to send the message");
    return;
  }
  APP_LOG(APP_LOG_LEVEL_INFO, "Message sent");
  display_text("Sending to Ollama...");
}

void send_delete_line(uint8_t index) {
  DictionaryIterator *out_iter;
  AppMessageResult result = app_message_outbox_begin(&out_iter);

  if (result != APP_MSG_OK) {
    APP_LOG(APP_LOG_LEVEL_ERROR, "Failed to app_message_outbox_begin");
    return;
  }
  dict_write_uint8(out_iter, MESSAGE_KEY_DeleteLine, index);
  dict_write_end(out_iter);

  result = app_message_outbox_send();
  if (result != APP_MSG_OK) {
    APP_LOG(APP_LOG_LEVEL_ERROR, "Failed to send the delete message");
    return;
  }
  display_text("Deleting...");
}

bool comm_sign_in_required(void) {
  return s_sign_in_required;
}

static void inbox_received_handler(DictionaryIterator *iter, void *context) {
  Tuple *number_on_lines = dict_find(iter, MESSAGE_KEY_NumberOfLines);

  s_sign_in_required = dict_find(iter, MESSAGE_KEY_SignInRequired) != NULL;
  if (s_sign_in_required) {
    display_sign_in();
    return;
  }

  if(!number_on_lines) {
    Tuple *status_tuple = dict_find(iter, MESSAGE_KEY_Status);
    if (status_tuple && status_tuple->type == TUPLE_CSTRING) {
      display_text(status_tuple->value->cstring);
    } else {
      display_text("Failed to load notes?");
    }
    return;
  }

  if (number_on_lines->type != TUPLE_INT || number_on_lines->length != 4) {
    display_text("tuple is not int32");
    return;
  }

  APP_LOG(APP_LOG_LEVEL_DEBUG, "Got %d messages", (int)number_on_lines->value->int32);

  int32_t newCount = min(number_on_lines->value->int32, MAX_MESSAGES);
  if (newCount < 0) {
    newCount = 0;
  }

  // Stage the new lines so a malformed message can't leave messages[] half-updated
  char* newTexts[MAX_MESSAGES];
  int8_t newPrefixes[MAX_MESSAGES];

  for (int i = 0; i < newCount; i++) {
    Tuple *note_tuple = dict_find(iter, MESSAGE_KEY_Result + i);

    // Format is first byte is indent, the rest is the actual cstring
    char* newString = NULL;
    if (note_tuple && note_tuple->type == TUPLE_CSTRING && note_tuple->length >= 2) {
      newString = malloc(note_tuple->length - 1);
    }
    if (newString == NULL) {
      for (int j = 0; j < i; j++) {
        free(newTexts[j]);
      }
      display_text("Failed to load notes!");
      return;
    }

    APP_LOG(APP_LOG_LEVEL_DEBUG, "Got %s in %d byte long message", note_tuple->value->cstring + 1, note_tuple->length);
    memcpy(newString, note_tuple->value->cstring + 1, note_tuple->length - 1);
    newString[note_tuple->length - 2] = '\0';

    newPrefixes[i] = note_tuple->value->cstring[0];
    newTexts[i] = newString;
  }

  for (int i = 0; i < MAX_MESSAGES; i++) {
    free(messages[i].message);
    messages[i].message = i < newCount ? newTexts[i] : NULL;
    messages[i].prefix = i < newCount ? newPrefixes[i] : 0;
  }
  numberOfMessages = newCount;
  selectedNote = numberOfMessages == 0 ? 0 : min(numberOfMessages - 1, selectedNote);

  save_notes();
  display_notes();


  Tuple *vibe_tuple = dict_find(iter, MESSAGE_KEY_Vibe);
  if (vibe_tuple) {
    vibes_short_pulse();
  }
}

static void inbox_dropped_handler(AppMessageResult reason, void *context) {
  APP_LOG(APP_LOG_LEVEL_ERROR, "Inbox message dropped: %d", (int)reason);
}

static void outbox_failed_handler(DictionaryIterator *iter, AppMessageResult reason, void *context) {
  APP_LOG(APP_LOG_LEVEL_ERROR, "Outbox message failed: %d", (int)reason);
  display_text("Failed to reach phone");
}

/******************************* Dictation API ********************************/

static void dictation_session_callback(DictationSession *session, DictationSessionStatus status,
                                       char *transcription, void *context) {
  if(status == DictationSessionStatusSuccess) {
    // Display the dictated text
    send_dictation(transcription);
  } else {
    // Display the reason for any error
    static char s_failed_buff[128];
    snprintf(s_failed_buff, sizeof(s_failed_buff), "Transcription failed.\n\nError ID:\n%d", (int)status);
    display_text(s_failed_buff);
  }
}

void start_dictation(void) {
  // NULL when the watch has no microphone or dictation isn't supported
  if (s_dictation_session == NULL) {
    display_text("Dictation unavailable");
    return;
  }
  dictation_session_start(s_dictation_session);
}

void comm_init(void) {
  app_message_open(inbox_size, outbox_size);
  app_message_register_inbox_received(inbox_received_handler);
  app_message_register_inbox_dropped(inbox_dropped_handler);
  app_message_register_outbox_failed(outbox_failed_handler);

  // Create new dictation session
  s_dictation_session = dictation_session_create(512, dictation_session_callback, NULL);
}

void comm_deinit(void) {
  // Free the last session data
  dictation_session_destroy(s_dictation_session);
}
