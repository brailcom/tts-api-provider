
#include <assert.h>
#include "ttsapi.h"

/* eSpeak API Include */
#include <espeak/speak_lib.h>


/* eSpeak API revision */
#ifndef ESPEAK_API_REVISION
#define ESPEAK_API_REVISION 1
#endif

int message_id = 1;

FILE *audio_connection;
int espeak_sample_rate;

int
event_callback(short *wav, int num_samples, espeak_EVENT *events)
{
  int i, ret;
  ttsapi_audio_block_t *block;
  
  if (events == NULL) return 0;
  
  if (wav != NULL){
    DBG("Received %d samples", num_samples);
    block = (ttsapi_audio_block_t*) malloc(sizeof(ttsapi_audio_block_t));
    block->msg_id = 1; // TODO: Correct msg_id
    block->number = 0;
    block->data_format = TTSAPI_RAW;
    block->data_length = num_samples * 2;
    block->audio_length = 0;
    block->sample_rate = espeak_sample_rate;
    block->channels = 1;
    block->encoding_sign = 0;
    block->encoding_bpw = 16;
    block->encoding_endian = TTSAPI_LE;
    block->events_list = NULL;
    block->data = (void*) wav;

    ret = driver_send_audio(audio_connection, block);
    if (ret != 0){
      DBG("Can't send audio data");
      return -1;
    }
  }

  DBG("Audio data block sent");

  /* Dispatch all given events */
  for (i=0; ; i++){

    if (events[i].type == espeakEVENT_LIST_TERMINATED)
      break;
    else if (events[i].type == espeakEVENT_MSG_TERMINATED)
      driver_send_event(EVENT_MESSAGE_END, message_id, 0,
			events[i].text_position, events[i].audio_position, NULL);
    else if (events[i].type == espeakEVENT_WORD)
      driver_send_event(EVENT_WORD_BEGIN, message_id, events[i].id.number,
			events[i].text_position, events[i].audio_position, NULL);
    else if (events[i].type == espeakEVENT_SENTENCE)
      driver_send_event(EVENT_SENTENCE_BEGIN, message_id, events[i].id.number,
			events[i].text_position, events[i].audio_position, NULL);
    else if (events[i].type == espeakEVENT_END)
      driver_send_event(EVENT_SENTENCE_END, message_id, events[i].id.number,
			events[i].text_position, events[i].audio_position, NULL);
    else if (events[i].type == espeakEVENT_MARK)
      driver_send_event(EVENT_INDEX_MARK, message_id, 0,
			events[i].text_position, events[i].audio_position, 
			(char*) events[i].id.name);
  }

  return 0;
}


int
init(char **status_info)
{
  int EspeakAudioChunkSize = 2000;

  /* Initialize eSpeak API */
#if ESPEAK_API_REVISION == 1
  DBG("eSpeak API revision is 1");
  espeak_sample_rate = espeak_Initialize(AUDIO_OUTPUT_RETRIEVAL,
					 EspeakAudioChunkSize, NULL);
#else
  DBG("eSpeak API revision is not 1");
  espeak_sample_rate = espeak_Initialize(AUDIO_OUTPUT_RETRIEVAL,
					 EspeakAudioChunkSize, NULL, 0);
#endif
  DBG("eSpeak initialization succesfull");

  if (espeak_sample_rate == EE_INTERNAL_ERROR) {
    DBG("Espeak: Could not initialize engine.");
    *status_info = strdup("Could not initialize engine.");
    return -1;
  }

  /* Set events and data retrieval callback */
  espeak_SetSynthCallback(event_callback);

  return 0;
}


ttsapi_driver_description_t*
list_drivers(void)
{
  ttsapi_driver_description_t *dscr;

  dscr = malloc(sizeof(ttsapi_driver_description_t));
  dscr->driver_id = strdup("espeak");
  dscr->driver_version = strdup("0.0");
  dscr->synthesizer_name = strdup("eSpeak Synthesizer");
  dscr->synthesizer_version = strdup("unknown");

  return dscr;
}

ttsapi_driver_capabilities_t*
driver_capabilities(void)
{
  ttsapi_driver_capabilities_t *capabilities;
  
  capabilities = malloc(sizeof(ttsapi_driver_capabilities_t));
  
  capabilities->can_list_voices = FALSE;
  capabilities->can_set_voice_by_properties = FALSE;
  capabilities->can_get_current_voice = FALSE;

  capabilities->can_set_rate_relative = TRUE;
  capabilities->can_set_rate_absolute = TRUE;
  capabilities->can_get_default_rate = FALSE;
  
  capabilities->can_set_pitch_relative = TRUE;
  capabilities->can_set_pitch_absolute = TRUE;
  capabilities->can_get_default_pitch = FALSE;
  
  capabilities->can_set_pitch_range_relative = TRUE;
  capabilities->can_set_pitch_range_absolute = TRUE;
  capabilities->can_get_default_pitch_range = FALSE;
  
  capabilities->can_set_volume_relative = TRUE;
  capabilities->can_set_volume_absolute = TRUE;
  capabilities->can_get_default_volume = FALSE;
  
  capabilities->can_set_punctuation_mode_all = FALSE;
  capabilities->can_set_punctuation_mode_none = FALSE;
  capabilities->can_set_punctuation_mode_some = FALSE;
  capabilities->can_set_punctuation_detail = FALSE;
  
  capabilities->can_set_capital_letters_mode_spelling = FALSE;;
  capabilities->can_set_capital_letters_mode_icon = FALSE;
  capabilities->can_set_capital_letters_mode_pitch = FALSE;
  
  capabilities->can_set_number_grouping = FALSE;
  
  capabilities->can_say_text_from_position = FALSE;
  capabilities->can_say_char = TRUE;
  capabilities->can_say_key = TRUE;
  capabilities->can_say_icon = TRUE;
  
  capabilities->can_set_dictionary = FALSE;
  
  capabilities->can_retrieve_audio = TRUE;
  capabilities->can_play_audio = TRUE;
  
  capabilities->can_report_events_by_message = FALSE;
  capabilities->can_report_events_by_sentences = FALSE;
  capabilities->can_report_events_by_words = FALSE;
  capabilities->can_report_custom_index_marks = FALSE;
  
  capabilities->honors_performance_guidelines = 2;
  capabilities->can_defer_message = FALSE;    
  
  capabilities->can_parse_ssml = FALSE;
  capabilities->can_parse_plain = TRUE;

  capabilities->supports_multilingual_utterances = FALSE;   

  return capabilities;
}

GList*
list_voices(void)
{
  ttsapi_voice_description_t *dscr;
  GList *list = NULL;
  espeak_VOICE **voices;
  int i;

  voices = (espeak_VOICE**) espeak_ListVoices(NULL);
  
  for (i=0; ;i++){
    if (voices[i] == NULL) break;
    dscr = malloc(sizeof(ttsapi_voice_description_t));
    dscr->name = strdup(voices[i]->identifier);
    dscr->language = strdup(voices[i]->languages);
    if (voices[i]->gender == 1)
      dscr->gender = TTSAPI_MALE;
    else if (voices[i]->gender == 2)
      dscr->gender = TTSAPI_FEMALE;
    else
      dscr->gender = TTSAPI_NONE;
    dscr->age = voices[i]->age;
    dscr->name = strdup(voices[i]->name);
    dscr->dialect = strdup("nil");
    list = g_list_append(list, dscr);

    //TODO: FREE voices[i]
  }

  return list;
}


/* Say text is declared as asynchronous because although
   the eSpeak documentation says that espeak_Synth should
   return immediatelly, it actually takes around 40ms for
   it to return. */
int
say_text_asynchro(ttsapi_msg_format format, char* text)
{
  /* TODO: Full implementation of say_text */

  DBG("Speaking text: |%s|", text);
  espeak_Synth(text, strlen(text)-1,
               0, POS_CHARACTER, 0,
	       espeakCHARS_AUTO,
	       NULL, NULL);
  return 0;
}

int
say_key(char* key)
{
  espeak_Key(key);

  return 0;
}

int
say_char(char *character)
{
  espeak_Char((wchar_t) g_utf8_to_ucs4(character, 1, NULL, NULL, NULL)[0]);

  return 0;
}

int
say_icon(char* icon)
{
  // TODO: Espeak doesn't support sound icons, use emulation here

  // For now, speak the icon name
  espeak_Synth(icon,strlen(icon),
	       0, POS_CHARACTER,0,
	       espeakCHARS_AUTO,
	       NULL, NULL);
  return 0;
}

int
_set_voice_parameter(espeak_PARAMETER param, ttsapi_setting_mode mode, int value)
{
  int relative;

  if (mode == TTSAPI_ABSOLUTE)
    relative = 0;
  else if (mode == TTSAPI_RELATIVE)
    relative = 1;
  else
    assert(0);

  espeak_SetParameter(param, value, relative);
  
  return 0;
}

int
set_rate(ttsapi_setting_mode mode, int rate)
{
  return _set_voice_parameter(espeakRATE, mode, rate);
}

int
set_pitch(ttsapi_setting_mode mode, int pitch)
{
  return _set_voice_parameter(espeakPITCH, mode, pitch);
}

int
set_pitch_range(ttsapi_setting_mode mode, int range)
{
  return _set_voice_parameter(espeakRANGE, mode, range);
}

int
set_volume(ttsapi_setting_mode mode, int volume)
{
  return _set_voice_parameter(espeakVOLUME, mode, volume);
}



int
set_audio_retrieval_destination(char *host, int port)
{
  DBG("Connecting to audio server %s:%d", host, port);

  audio_connection = driver_audio_connection_init(host, port);
  if (audio_connection == NULL)
    return -1;

  DBG("Connected to audio server %s:%d", host, port);
  return 0;
}

int
cancel(void)
{

  espeak_Cancel();
  return 0;
}


int
main(void)
{

  DRIVER_INIT_FUNCTIONS_LIST();

  DRIVER_REGISTER_FUNCTION(init);
  DRIVER_REGISTER_FUNCTION(driver_capabilities);
  DRIVER_REGISTER_FUNCTION(list_drivers);
  DRIVER_REGISTER_FUNCTION(list_voices);

  DRIVER_REGISTER_FUNCTION(say_text_asynchro);
  DRIVER_REGISTER_FUNCTION(say_key);
  DRIVER_REGISTER_FUNCTION(say_char);
  DRIVER_REGISTER_FUNCTION(say_icon);

  DRIVER_REGISTER_FUNCTION(set_rate);
  DRIVER_REGISTER_FUNCTION(set_pitch);
  DRIVER_REGISTER_FUNCTION(set_pitch_range);
  DRIVER_REGISTER_FUNCTION(set_volume);

  DRIVER_REGISTER_FUNCTION(set_audio_retrieval_destination);

  DRIVER_REGISTER_FUNCTION(cancel);

  DRIVER_RUN();

  return 0;
}
