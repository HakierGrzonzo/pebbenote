#pragma once

#include <pebble.h>

void input_click_config_provider(void *context);
// Switches notes on horizontal swipes, on watches with a touchscreen
void input_swipe_handler(const Recognizer *recognizer, RecognizerEvent event);
