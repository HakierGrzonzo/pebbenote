#include "input.h"

#include "comm.h"
#include "notes.h"
#include "ui.h"

static void select_click_handler(ClickRecognizerRef recognizer, void *context) {
  // Dictation can't succeed until the user signs in on the phone
  if (comm_sign_in_required()) {
    return;
  }
  // Start voice dictation UI
  start_dictation();
}

static void select_long_click_handler(ClickRecognizerRef recognizer, void *context) {
  if (numberOfMessages == 0) {
    return;
  }
  send_delete_line(selectedNote);
}

static void down_click_handler(ClickRecognizerRef recognizer, void *context) {
  if (numberOfMessages == 0) {
    return;
  }
  selectedNote = (selectedNote + 1) % numberOfMessages;
  save_selected_note();
  scroll_to_selected_note();
}

static void up_click_handler(ClickRecognizerRef recognizer, void *context) {
  if (numberOfMessages == 0) {
    return;
  }
  selectedNote = (selectedNote + numberOfMessages - 1) % numberOfMessages;
  save_selected_note();
  scroll_to_selected_note();
}

void input_click_config_provider(void *context) {
  window_single_click_subscribe(BUTTON_ID_SELECT, select_click_handler);
  window_long_click_subscribe(BUTTON_ID_SELECT, 500, select_long_click_handler, NULL);
  window_single_repeating_click_subscribe(BUTTON_ID_DOWN, 300, down_click_handler);
  window_single_repeating_click_subscribe(BUTTON_ID_UP, 300, up_click_handler);
}
