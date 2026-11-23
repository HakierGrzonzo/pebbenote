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
  // Delete locally right away so several lines can be removed quickly
  queue_delete_line(selectedNote);
  delete_note_line(selectedNote);
  vibes_short_pulse();
  if (numberOfMessages == 0) {
    display_text("Note is empty");
  } else {
    scroll_to_selected_note();
  }
}

// Moves the highlight by step lines. Past the first or last line a fresh
// press switches to the previous or next note, holding the button stops there.
static void move_highlight(ClickRecognizerRef recognizer, int step) {
  int target = selectedNote + step;
  if (target < 0 || target >= numberOfMessages) {
    if (!click_recognizer_is_repeating(recognizer)) {
      comm_switch_note(step);
    }
    return;
  }
  selectedNote = target;
  save_selected_note();
  scroll_to_selected_note();
}

static void down_click_handler(ClickRecognizerRef recognizer, void *context) {
  move_highlight(recognizer, 1);
}

static void up_click_handler(ClickRecognizerRef recognizer, void *context) {
  move_highlight(recognizer, -1);
}

static void back_click_handler(ClickRecognizerRef recognizer, void *context) {
  // A second press skips waiting for the phone
  if (comm_is_exiting()) {
    window_stack_pop_all(true);
    return;
  }
  comm_flush_and_exit();
}

void input_click_config_provider(void *context) {
  window_single_click_subscribe(BUTTON_ID_BACK, back_click_handler);
  window_single_click_subscribe(BUTTON_ID_SELECT, select_click_handler);
  window_long_click_subscribe(BUTTON_ID_SELECT, 500, select_long_click_handler, NULL);
  window_single_repeating_click_subscribe(BUTTON_ID_DOWN, 300, down_click_handler);
  window_single_repeating_click_subscribe(BUTTON_ID_UP, 300, up_click_handler);
}

void input_swipe_handler(const Recognizer *recognizer, RecognizerEvent event) {
  if (event != RecognizerEvent_Completed) {
    return;
  }
  // The next note comes in from the right, like turning a page
  switch (swipe_recognizer_get_direction(recognizer)) {
  case SwipeDirection_Left:
    comm_switch_note(1);
    break;
  case SwipeDirection_Right:
    comm_switch_note(-1);
    break;
  default:
    break;
  }
}
