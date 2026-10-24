#include <pebble.h>

#include "comm.h"
#include "input.h"
#include "ui.h"

static void init() {
  comm_init();
  ui_init(input_click_config_provider);
}

static void deinit() {
  comm_deinit();
  ui_deinit();
}

int main() {
  init();
  app_event_loop();
  deinit();
}
