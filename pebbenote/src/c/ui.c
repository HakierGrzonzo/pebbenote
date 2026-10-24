#include "ui.h"

#include <string.h>

#include "glance.h"
#include "notes.h"

static Window *s_main_window;
static TextLayer *s_output_layer;
static ScrollLayer *s_scroll_layer;
static char s_last_text[512];
static GRect s_bounds;

static void set_longer_text_hidden(bool hide) {
  for (int i = 0; i < MAX_MESSAGES; i++) {
    layer_set_hidden(text_layer_get_layer(messages[i].layer), hide);
  }
}

void display_text(char* text) {
    Layer* layer = text_layer_get_layer(s_output_layer);
    layer_set_hidden(layer, false);
    set_longer_text_hidden(true);

    layer_set_frame(layer,
                    GRect(s_bounds.origin.x, s_bounds.size.h / 2 - 24, s_bounds.size.w, s_bounds.size.h / 3));
    strncpy(s_last_text, text, sizeof(s_last_text) - 1);

    text_layer_set_text_alignment(s_output_layer, GTextAlignmentCenter);
    GFont big_font = fonts_get_system_font(FONT_KEY_GOTHIC_28);

    text_layer_set_font(s_output_layer, big_font);
    text_layer_set_text(s_output_layer, s_last_text);

    GSize text_size = text_layer_get_content_size(s_output_layer);
    layer_set_frame(layer,
                    GRect(s_bounds.origin.x, s_bounds.size.h / 2 - 24, s_bounds.size.w, text_size.h));
    scroll_layer_set_content_size(s_scroll_layer, text_size);
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
    layer_set_frame(
        text_layer_get_layer(message.layer),
        GRect(prefixOffset, yOffset, s_bounds.size.w - prefixOffset, s_bounds.size.h)
    );
    text_layer_set_text(message.layer, message.message ? message.message : "");

    GFont* fontToSet;
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
        GRect(prefixOffset, yOffset, s_bounds.size.w - prefixOffset, text_size.h + 2 + margin)
    );
    messages[i].yOffset = yOffset;

    yOffset += text_size.h + 2 + margin;
  }
  scroll_layer_set_content_size(
      s_scroll_layer,
      GSize(s_bounds.size.w, yOffset)
  );
}

void scroll_to_selected_note(void) {
  display_notes();

  GPoint offset = GPoint(0, -messages[selectedNote].yOffset + 10);
  scroll_layer_set_content_offset(s_scroll_layer, offset, true);
}

static void window_load(Window *window) {
  Layer *window_layer = window_get_root_layer(window);
  s_bounds = layer_get_bounds(window_layer);
  GRect content_size = GRect(s_bounds.origin.x, s_bounds.origin.y, s_bounds.size.w, s_bounds.size.h * 4);
  GRect scroll_content_size = GRect(s_bounds.origin.x, s_bounds.origin.y, s_bounds.size.w, s_bounds.size.h);
  s_scroll_layer = scroll_layer_create(scroll_content_size);

  layer_add_child(window_layer, scroll_layer_get_layer(s_scroll_layer));

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
  scroll_layer_destroy(s_scroll_layer);
}

void ui_init(ClickConfigProvider click_config) {
  s_main_window = window_create();
  window_set_click_config_provider(s_main_window, click_config);
  window_set_window_handlers(s_main_window, (WindowHandlers) {
    .load = window_load,
    .unload = window_unload,
  });
  window_stack_push(s_main_window, true);
}

void ui_deinit(void) {
  window_destroy(s_main_window);
}
