#include "glance.h"

#include "notes.h"

// Maximum length of an AppGlance template string, including the terminator
#define SUBTITLE_MAX_LEN 150

static void glance_reload_callback(AppGlanceReloadSession *session, size_t limit, void *context) {
  if (limit < 1 || numberOfMessages == 0) {
    return;
  }

  // The subtitle is a template string, so braces must be escaped
  char subtitle[SUBTITLE_MAX_LEN];
  const char *text = messages[selectedNote].message;
  size_t out = 0;
  for (size_t i = 0; text[i] != '\0' && out < sizeof(subtitle) - 2; i++) {
    if (text[i] == '{' || text[i] == '}' || text[i] == '\\') {
      subtitle[out++] = '\\';
    }
    subtitle[out++] = text[i];
  }
  subtitle[out] = '\0';

  const AppGlanceSlice slice = {
      .layout = {.subtitle_template_string = subtitle},
      .expiration_time = APP_GLANCE_SLICE_NO_EXPIRATION,
  };
  AppGlanceResult result = app_glance_add_slice(session, slice);
  if (result != APP_GLANCE_RESULT_SUCCESS) {
    APP_LOG(APP_LOG_LEVEL_ERROR, "app_glance_add_slice() returned %d", (int)result);
  }
}

void glance_update(void) {
  app_glance_reload(glance_reload_callback, NULL);
}
