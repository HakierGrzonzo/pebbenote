#pragma once

#include <pebble.h>

// Creates the main window and pushes it. click_config is installed on it.
void ui_init(ClickConfigProvider click_config);
void ui_deinit(void);

// Shows a centered status/dictation string in place of the note
void display_text(char* text);
// Lays out and shows the cached note lines
void display_notes(void);
// Redraws the note and scrolls so the selected line is in view
void scroll_to_selected_note(void);
