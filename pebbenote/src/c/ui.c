#include "ui.h"

#include <string.h>

#include "glance.h"
#include "notes.h"

static Window *s_main_window;
static TextLayer *s_output_layer;
static ScrollLayer *s_scroll_layer;
static StatusBarLayer *s_status_bar;
static TextLayer *s_processing_layer;
static char s_last_text[512];
static GRect s_bounds;

static void set_longer_text_hidden(bool hide) {
  for (int i = 0; i < MAX_MESSAGES; i++) {
    layer_set_hidden(text_layer_get_layer(messages[i].layer), hide);
  }
}

static void show_text(char *text, const char *font_key) {
  Layer *layer = text_layer_get_layer(s_output_layer);
  layer_set_hidden(layer, false);
  set_longer_text_hidden(true);

  layer_set_frame(layer, GRect(s_bounds.origin.x, s_bounds.size.h / 2 - 24, s_bounds.size.w,
                               s_bounds.size.h / 3));
  strncpy(s_last_text, text, sizeof(s_last_text) - 1);

  text_layer_set_text_alignment(s_output_layer, GTextAlignmentCenter);
  text_layer_set_font(s_output_layer, fonts_get_system_font(font_key));
  text_layer_set_text(s_output_layer, s_last_text);

  GSize text_size = text_layer_get_content_size(s_output_layer);
  layer_set_frame(layer,
                  GRect(s_bounds.origin.x, s_bounds.size.h / 2 - 24, s_bounds.size.w, text_size.h));
  scroll_layer_set_content_size(s_scroll_layer, text_size);
}

void display_text(char *text) { show_text(text, FONT_KEY_GOTHIC_28); }

void display_sign_in(void) {
  show_text("Sign in required\n"
            "Open the Pebble app on your phone, open pebbenote settings and "
            "tap the sign in link",
            FONT_KEY_GOTHIC_18_BOLD);
}

void display_notes(void) {
  layer_set_hidden(text_layer_get_layer(s_output_layer), true);
  set_longer_text_hidden(true);

  GFont big_font = fonts_get_system_font(FONT_KEY_GOTHIC_18_BOLD);
  GFont small_font = fonts_get_system_font(FONT_KEY_GOTHIC_14);

  int yOffset = 0;
  for (int i = 0; i < numberOfMessages; i++) {
    struct MessageWithPrefix message = messages[i];
    layer_set_hidden(text_layer_get_layer(message.layer), false);
    int prefixOffset = min(message.prefix * 2, 40);
    layer_set_frame(text_layer_get_layer(message.layer),
                    GRect(prefixOffset, yOffset, s_bounds.size.w - prefixOffset, s_bounds.size.h));
    text_layer_set_text(message.layer, message.message ? message.message : "");

    GFont *fontToSet;
    GColor color;
    GColor backgroundColor;
    uint8_t margin = 0;
    if (i == selectedNote) {
      fontToSet = &big_font;
      color = GColorWhite;
      backgroundColor = GColorBlack;
      margin = 3;
    } else {
      fontToSet = &small_font;
      color = GColorBlack;
      backgroundColor = GColorWhite;
    }

    text_layer_set_font(message.layer, *fontToSet);
    text_layer_set_text_color(message.layer, color);
    text_layer_set_background_color(message.layer, backgroundColor);

    GSize text_size = text_layer_get_content_size(message.layer);
    layer_set_frame(
        text_layer_get_layer(message.layer),
        GRect(prefixOffset, yOffset, s_bounds.size.w - prefixOffset, text_size.h + 2 + margin));
    messages[i].yOffset = yOffset;

    yOffset += text_size.h + 2 + margin;
  }
  scroll_layer_set_content_size(s_scroll_layer, GSize(s_bounds.size.w, yOffset));
}

void ui_set_processing(bool processing) {
  layer_set_hidden(text_layer_get_layer(s_processing_layer), !processing);
}

void scroll_to_selected_note(void) {
  display_notes();

  GPoint offset = GPoint(0, -messages[selectedNote].yOffset + 10);
  scroll_layer_set_content_offset(s_scroll_layer, offset, true);
}

static void window_load(Window *window) {
  Layer *window_layer = window_get_root_layer(window);
  GRect window_bounds = layer_get_bounds(window_layer);
  // Content coordinates are relative to the scroll layer, which sits below the status bar
  s_bounds = GRect(0, 0, window_bounds.size.w, window_bounds.size.h - STATUS_BAR_LAYER_HEIGHT);
  GRect content_size =
      GRect(s_bounds.origin.x, s_bounds.origin.y, s_bounds.size.w, s_bounds.size.h * 4);
  GRect scroll_content_size = GRect(0, STATUS_BAR_LAYER_HEIGHT, s_bounds.size.w, s_bounds.size.h);
  s_scroll_layer = scroll_layer_create(scroll_content_size);

  layer_add_child(window_layer, scroll_layer_get_layer(s_scroll_layer));

  s_status_bar = status_bar_layer_create();
  status_bar_layer_set_colors(s_status_bar, GColorWhite, GColorBlack);
  layer_add_child(window_layer, status_bar_layer_get_layer(s_status_bar));

  scroll_layer_set_shadow_hidden(s_scroll_layer, true);

  GFont smallFont = fonts_get_system_font(FONT_KEY_GOTHIC_18);
  s_output_layer = text_layer_create(content_size);
  for (int i = 0; i < MAX_MESSAGES; i++) {
    messages[i].layer = text_layer_create(content_size);
    text_layer_set_font(messages[i].layer, smallFont);
    text_layer_set_text_alignment(messages[i].layer, GTextAlignmentLeft);
    scroll_layer_add_child(s_scroll_layer, text_layer_get_layer(messages[i].layer));
  }

  scroll_layer_add_child(s_scroll_layer, text_layer_get_layer(s_output_layer));

  // Over the bottom of the note, taller on round screens so the text clears the edge
  int16_t banner_height = PBL_IF_ROUND_ELSE(30, 18);
  s_processing_layer = text_layer_create(
      GRect(0, window_bounds.size.h - banner_height, window_bounds.size.w, banner_height));
  text_layer_set_font(s_processing_layer, fonts_get_system_font(FONT_KEY_GOTHIC_14_BOLD));
  text_layer_set_text_alignment(s_processing_layer, GTextAlignmentCenter);
  text_layer_set_text_color(s_processing_layer, GColorWhite);
  text_layer_set_background_color(s_processing_layer, GColorBlack);
  text_layer_set_text(s_processing_layer, "Processing...");
  layer_set_hidden(text_layer_get_layer(s_processing_layer), true);
  layer_add_child(window_layer, text_layer_get_layer(s_processing_layer));

  // Show the cached note right away, the phone will replace it once it's ready
  if (load_notes()) {
    display_notes();
  } else {
    display_text("Loading...");
  }
}

static void window_unload(Window *window) {
  // Must run before the lines are freed below
  glance_update();
  for (int i = 0; i < MAX_MESSAGES; i++) {
    text_layer_destroy(messages[i].layer);
    messages[i].layer = NULL;
    free(messages[i].message);
    messages[i].message = NULL;
  }
  text_layer_destroy(s_output_layer);
  text_layer_destroy(s_processing_layer);
  scroll_layer_destroy(s_scroll_layer);
  status_bar_layer_destroy(s_status_bar);
}

void ui_init(ClickConfigProvider click_config) {
  s_main_window = window_create();
  window_set_click_config_provider(s_main_window, click_config);
  window_set_window_handlers(s_main_window, (WindowHandlers){
                                                .load = window_load,
                                                .unload = window_unload,
                                            });
  window_stack_push(s_main_window, true);
}

void ui_deinit(void) { window_destroy(s_main_window); }
