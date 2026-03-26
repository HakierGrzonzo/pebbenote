#include <pebble.h>
#include <string.h>

static Window *s_main_window;
static TextLayer *s_output_layer;
static ScrollLayer *s_scroll_layer;

static DictationSession *s_dictation_session;
static char s_last_text[512];

// Largest expected inbox and outbox message sizes
const uint32_t inbox_size = 2048;
const uint32_t outbox_size = 512;

#define min(a, b) a > b ? b : a

GRect s_bounds;

struct MessageWithPrefix {
  int8_t prefix;
  char* message;
  TextLayer* layer;
};

#define MAX_MESSAGES 20

static struct MessageWithPrefix messages[MAX_MESSAGES];

static void set_longer_text_hidden(bool hide) {
  for (int i = 0; i < MAX_MESSAGES; i++) {
    layer_set_hidden(text_layer_get_layer(messages[i].layer), hide);
  }
}

static void display_text(char* text) {
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

static void display_longer_text(uint8_t number_of_messages) {
  layer_set_hidden(text_layer_get_layer(s_output_layer), true);
  set_longer_text_hidden(true);


  int yOffset = 0;
  for (int i = 0; i < number_of_messages; i++) {
    struct MessageWithPrefix message = messages[i];
    layer_set_hidden(text_layer_get_layer(message.layer), false);
    int prefixOffset = min(message.prefix * 2, 40);
    layer_set_frame(
        text_layer_get_layer(message.layer), 
        GRect(prefixOffset, yOffset, s_bounds.size.w - prefixOffset, s_bounds.size.h)
    );
    text_layer_set_text(message.layer, message.message);
    GSize text_size = text_layer_get_content_size(message.layer);
    layer_set_frame(
        text_layer_get_layer(message.layer), 
        GRect(prefixOffset, yOffset, s_bounds.size.w - prefixOffset, text_size.h + 2)
    );
    yOffset += text_size.h + 2;
  }
  scroll_layer_set_content_size(
      s_scroll_layer, 
      GSize(s_bounds.size.w, yOffset)
  );
}

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
  display_text("Done!");
} 

static void inbox_received_handler(DictionaryIterator *iter, void *context) {
  Tuple *number_on_lines = dict_find(iter, MESSAGE_KEY_NumberOfLines);


  if(!number_on_lines) {
    Tuple *note_tuple = dict_find(iter, MESSAGE_KEY_Result);
    if (note_tuple && note_tuple->type == TUPLE_CSTRING) {
      display_text(note_tuple->value->cstring);
    } else {
      display_text("Failed to load notes?");
    }
    return;
  }

  if (number_on_lines->type != TUPLE_INT && number_on_lines->length != 4) {
    display_text("tuple is not int32");
    return;
  }

  APP_LOG(APP_LOG_LEVEL_DEBUG, "Got %d messages", (int)number_on_lines->value->int32);

  int32_t number_or_messages_to_receive = min(number_on_lines->value->int32, MAX_MESSAGES);

  for (int i = 0; i < number_or_messages_to_receive; i++) {
    Tuple *note_tuple = dict_find(iter, MESSAGE_KEY_Result + i);

    if(!number_on_lines || note_tuple->type != TUPLE_CSTRING) {
      display_text("Failed to load notes!");
      return;
    }
    
    // Format is first byte is indent, the rest is the actual cstring
    int8_t prefix = note_tuple->value->int8;

    if (messages[i].message != NULL) {
      free(messages[i].message);
    }

    int newStringLength = sizeof(char) * note_tuple->length;

    char* newString = malloc(newStringLength);

    APP_LOG(APP_LOG_LEVEL_DEBUG, "Got %s in %d byte long message", note_tuple->value->cstring + 1, note_tuple->length);
    strncpy(newString, note_tuple->value->cstring + 1, newStringLength);

    messages[i].prefix = prefix;
    messages[i].message = newString;

  }
  display_longer_text(number_or_messages_to_receive);


  Tuple *vibe_tuple = dict_find(iter, MESSAGE_KEY_Vibe);
  if (vibe_tuple) {
    vibes_short_pulse();
  }
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

/************************************ App *************************************/

static void select_click_handler(ClickRecognizerRef recognizer, void *context) {
  // Start voice dictation UI
  dictation_session_start(s_dictation_session);
}

static void down_click_handler(ClickRecognizerRef recognizer, void *context) {
  scroll_layer_scroll_down_click_handler(recognizer, s_scroll_layer);
}
static void up_click_handler(ClickRecognizerRef recognizer, void *context) {
  scroll_layer_scroll_up_click_handler(recognizer, s_scroll_layer);
}

static void click_config_provider(void *context) {
  window_single_click_subscribe(BUTTON_ID_SELECT, select_click_handler);
  window_single_repeating_click_subscribe(BUTTON_ID_DOWN, 100, down_click_handler);
  window_single_repeating_click_subscribe(BUTTON_ID_UP, 100, up_click_handler);
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
  display_text("Loading...");
}

static void window_unload(Window *window) {
  text_layer_destroy(s_output_layer);
  scroll_layer_destroy(s_scroll_layer);
}

static void init() {
  app_message_open(inbox_size, outbox_size);
  app_message_register_inbox_received(inbox_received_handler);
  s_main_window = window_create();
  window_set_click_config_provider(s_main_window, click_config_provider);
  window_set_window_handlers(s_main_window, (WindowHandlers) {
    .load = window_load,
    .unload = window_unload,
  });
  window_stack_push(s_main_window, true);

  // Create new dictation session
  s_dictation_session = dictation_session_create(sizeof(s_last_text), dictation_session_callback, NULL);
}

static void deinit() {
  // Free the last session data
  dictation_session_destroy(s_dictation_session);

  window_destroy(s_main_window);
}

int main() {
  init();
  app_event_loop();
  deinit();
}
