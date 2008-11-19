
// C API of TTS API implementation

#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/tcp.h>
#include <netinet/in.h>
#include <arpa/inet.h>


#include "ttsapi.h"

// GLOBAL VARIABLES
_ttsapi_asynchro_request_t _ttsapi_asynchro_request;
GThread *_driver_lateral_thread;

GMutex *_driver_output_mutex;

ttsapi_driver_settings_t driver_settings;

// GLib helper functions
GList*
_g_list_from_array(void **array)
{
  /*
    Create a GList* from a NULL terminated array.
   */
  int i;
  GList *list = NULL;

  for (i=0; ;i++){
    if (array[i] != NULL)
      list = g_list_append(list, array[i]);    
    else
      break;
  }

  return list;
}


// COMMUNICATION

#define NEWLINE "\r\n"

char*
com_read_line(void)
{
  char *line = NULL;
  size_t buf_size = 0;
  getline(&line, &buf_size, stdin);
  return line;
}

GList*
com_read_command(void)
{
  char *line;
  char *stripped, **result;

  /* Read one line of input and strip whitespaces (\r\n...)*/
  line = com_read_line();
      
  stripped = g_strstrip(line);

  /* Split line of input into a null-terminated array */
  result = g_strsplit(stripped,  " ", 0);

  // Create a GList* and return it
  return _g_list_from_array((void **) result);
}

int
com_write_reply(TReply *reply)
{
  GString *reply_string;
  int i;
  
  assert (reply->code > 0);
  assert (reply->text != NULL);

  reply_string = g_string_new("");
  // Construct the reply
  if (reply->data != NULL){
    for (i=0; i<=g_list_length(reply->data)-1; i++){
      g_string_append_printf(reply_string, "%d-%s" NEWLINE, 
			     reply->code,
			     (char*) g_list_nth_data(reply->data, i));
    }
  }

  g_string_append_printf(reply_string, "%d %s" NEWLINE, reply->code,
			 reply->text);
  
  // Write it out and flush
  printf(reply_string->str);
  g_string_free(reply_string, TRUE);
  fflush(stdout);


  return 0;
}


TReply*
_construct_reply(int code, char* text, GList *data)
{
  TReply *reply;

  assert ((code>100) && (code < 1000));
  assert ((text != NULL) && (strlen(text)>0));

  reply = malloc(sizeof(TReply));
  reply->code = code;
  reply->text = strdup(text);
  reply->data = g_list_copy(data);

  return reply;
}

TReply*
_construct_reply_strarg(int code, char* text, char *arg)
{
  TReply *reply;
  GList *args_list = NULL;
  args_list = g_list_append(args_list, strdup(arg));
  reply =  _construct_reply(code, text, args_list);
  g_list_free(args_list);
  return reply;
}


void
_free_reply(TReply *reply){
  g_free(reply->text);
  g_list_free(reply->data);
  g_free(reply);
}


void*
_ttsapi_get_function(char *key, GHashTable *table)
{
  return g_hash_table_lookup(table, key);
}


TReply*
_ttsapi_init(GHashTable *driver_functions)
{
  int (*driver_init)(char**);
  char *status_info;

  driver_init = _ttsapi_get_function("init", driver_functions);

  if (driver_init != NULL){
    GList *status_data = NULL;
    int ret = driver_init(&status_info);
    status_data = g_list_append(status_data, status_info);
    
    if (ret != 0)
      return _construct_reply(304, "DRIVER NOT LOADED", NULL);
  }

  return _construct_reply(200, "OK INITALIZED", NULL);
}

TReply*
_ttsapi_list_drivers (GHashTable *driver_functions)
{
  ttsapi_driver_description_t* (*driver_list_drivers)(void);
  ttsapi_driver_description_t *dscr;
  GList *reply = NULL;

  driver_list_drivers = \
    _ttsapi_get_function("list_drivers", driver_functions);

  if (driver_list_drivers != NULL){
    char *driver_str;
    dscr = driver_list_drivers();
    if (dscr == NULL)
      return _construct_reply(300, "UNKNOWN ERROR", NULL);
    driver_str = g_strdup_printf("%s %s \"%s\" %s",
				 dscr->driver_id,
				 dscr->driver_version,
				 dscr->synthesizer_name,
				 dscr->synthesizer_version);
    reply = g_list_append(reply, driver_str);
  }

  return _construct_reply(200, "OK DRIVER LIST SENT", reply);
}

TReply*
_ttsapi_list_voices (GHashTable *driver_functions)
{
  GList* (*driver_list_voices)(void);
  GList *reply = NULL;
  GList *dscr_list;

  driver_list_voices = \
    _ttsapi_get_function("list_voices", driver_functions);

  if (driver_list_voices != NULL){
    dscr_list = driver_list_voices();
    if (dscr_list == NULL)
      return _construct_reply(300, "UNKNOWN ERROR", NULL);
    
    int i;
    for (i=0;i<=g_list_length(dscr_list)-1; i++){
      ttsapi_voice_description_t *dscr;
      char *voice_str, *gender;
      dscr = g_list_nth_data(dscr_list, i);
      
      if (dscr->gender == TTSAPI_MALE)
	gender = strdup("MALE");
      else
	gender = strdup("FEMALE");
      
	voice_str = g_strdup_printf("\"%s\" %s \"%s\" %s %d",
				    dscr->name,
				    dscr->language,
				    dscr->dialect,
				    gender,
				    dscr->age);
      reply = g_list_append(reply, voice_str);
      g_free(gender);
    }
  }

  return _construct_reply(200, "OK DRIVER LIST SENT", reply);
}

#define ADD_LINE_BOOL(field) \
  if (result->field == TRUE){ \
    capabilities = g_list_append(capabilities, g_strdup_printf(#field" true")); \
  }else{ \
    capabilities = g_list_append(capabilities, g_strdup_printf(#field" false")); \
  } 


TReply*
_ttsapi_driver_capabilities (GHashTable *driver_functions)
{
  GList *capabilities = NULL;
  ttsapi_driver_capabilities_t *result;
  
  ttsapi_driver_capabilities_t* (*driver_capabilities)(void);

  char *settings_str;

  driver_capabilities = _ttsapi_get_function("driver_capabilities",
					     driver_functions);
  
  if (driver_capabilities != NULL){
    result = driver_capabilities();
    if (result == NULL)
      return _construct_reply(300, "CANT REPORT DRIVER CAPABILITIES", NULL);
  }else{
    result = malloc(sizeof(driver_capabilities));
    
    result->can_list_voices = FALSE;
    result->can_set_voice_by_properties = FALSE;
    result->can_get_current_voice = FALSE;
    result->can_set_rate_relative = FALSE;
    result->can_set_rate_absolute = FALSE;
    result->can_get_default_rate = FALSE;

    result->can_set_pitch_relative = FALSE;
    result->can_set_pitch_absolute = FALSE;
    result->can_get_default_pitch = FALSE;
  
    result->can_set_pitch_range_relative = FALSE;
    result->can_set_pitch_range_absolute = FALSE;
    result->can_get_default_pitch_range = FALSE;
  
    result->can_set_volume_relative = FALSE;
    result->can_set_volume_absolute = FALSE;
    result->can_get_default_volume = FALSE;
  
    result->can_set_punctuation_mode_all = FALSE;
    result->can_set_punctuation_mode_none = FALSE;
    result->can_set_punctuation_mode_some = FALSE;
    result->can_set_punctuation_detail = FALSE;
  
    result->can_set_capital_letters_mode_spelling = FALSE;;
    result->can_set_capital_letters_mode_icon = FALSE;
    result->can_set_capital_letters_mode_pitch = FALSE;
  
    result->can_set_number_grouping = FALSE;
  
    result->can_say_text_from_position = FALSE;
    result->can_say_char = FALSE;
    result->can_say_key = FALSE;
    result->can_say_icon = FALSE;
    
    result->can_set_dictionary = FALSE;
    
    result->can_retrieve_audio = FALSE;
    result->can_play_audio = FALSE;
    
    result->can_report_events_by_message = FALSE;
    result->can_report_events_by_sentences = FALSE;
    result->can_report_events_by_words = FALSE;
    result->can_report_custom_index_marks = FALSE;
   
    result->honors_performance_guidelines = 0;
    result->can_defer_message = FALSE;    
   
    result->can_parse_ssml = FALSE;
    result->can_parse_plain = FALSE;
    result->supports_multilingual_utterances = FALSE;   
  }

  ADD_LINE_BOOL(can_list_voices);
  ADD_LINE_BOOL(can_set_voice_by_properties);
  ADD_LINE_BOOL(can_get_current_voice);

  settings_str = g_strdup("");
  if (result->can_set_rate_relative)
    settings_str = g_strconcat(settings_str, " relative", NULL);
  if (result->can_set_rate_absolute)
    settings_str = g_strconcat(settings_str, " absolute", NULL);
  if (strlen(settings_str) == 0)
    settings_str = g_strconcat(settings_str, " none", NULL);
  capabilities = g_list_append(capabilities,
			       g_strdup_printf("rate_settings %s", settings_str));
  
  settings_str = g_strdup("");
  if (result->can_set_pitch_relative)
    settings_str = g_strconcat(settings_str, " relative", NULL);
  if (result->can_set_pitch_absolute)
    settings_str = g_strconcat(settings_str, " absolute", NULL);
  if (strlen(settings_str) == 0)
    settings_str = g_strconcat(settings_str, " none", NULL);
  capabilities = g_list_append(capabilities,
			       g_strdup_printf("pitch_settings %s", settings_str));

  settings_str = g_strdup("");
  if (result->can_set_volume_relative)
    settings_str = g_strconcat(settings_str, " relative", NULL);
  if (result->can_set_volume_absolute)
    settings_str = g_strconcat(settings_str, " absolute", NULL);
  if (strlen(settings_str) == 0)
    settings_str = g_strconcat(settings_str, " none", NULL);
  capabilities = g_list_append(capabilities,
			       g_strdup_printf("pitch_range_settings %s", settings_str));


  settings_str = g_strdup("");
  if (result->can_set_pitch_range_relative)
    settings_str = g_strconcat(settings_str, " relative", NULL);
  if (result->can_set_pitch_range_absolute)
    settings_str = g_strconcat(settings_str, " absolute", NULL);
  if (strlen(settings_str) == 0)
    settings_str = g_strconcat(settings_str, " none", NULL);
  capabilities = g_list_append(capabilities,
			       g_strdup_printf("volume_settings %s", settings_str));

  settings_str = g_strdup("");
  if (result->can_set_capital_letters_mode_spelling)
    settings_str = g_strconcat(settings_str, " spelling", NULL);
  if (result->can_set_capital_letters_mode_icon)
    settings_str = g_strconcat(settings_str, " icon", NULL);
  if (result->can_set_capital_letters_mode_pitch)
    settings_str = g_strconcat(settings_str, " pitch", NULL);
  if (strlen(settings_str) == 0)
    settings_str = g_strconcat(settings_str, " none", NULL);
  capabilities = g_list_append(capabilities,
			       g_strdup_printf("capital_letters_modes %s", settings_str));


  ADD_LINE_BOOL(can_get_default_rate);
  ADD_LINE_BOOL(can_get_default_pitch);
  ADD_LINE_BOOL(can_get_default_volume);
  ADD_LINE_BOOL(can_get_default_pitch_range);
  
  settings_str = g_strdup("");
  if (result->can_set_punctuation_mode_all)
    settings_str = g_strconcat(settings_str, " all", NULL);
  if (result->can_set_punctuation_mode_none)
    settings_str = g_strconcat(settings_str, " none", NULL);
  if (result->can_set_punctuation_mode_some)
    settings_str = g_strconcat(settings_str, " some", NULL);
  if (strlen(settings_str) == 0)
    settings_str = g_strconcat(settings_str, " none", NULL);
  capabilities = g_list_append(capabilities,
			       g_strdup_printf("punctuation_modes %s", settings_str));


  ADD_LINE_BOOL(can_set_punctuation_detail);
  ADD_LINE_BOOL(can_set_number_grouping);
  ADD_LINE_BOOL(can_say_text_from_position);
  ADD_LINE_BOOL(can_say_key);
  ADD_LINE_BOOL(can_say_char);
  ADD_LINE_BOOL(can_say_icon);

  ADD_LINE_BOOL(can_set_dictionary);

  settings_str = g_strdup("");
  if (result->can_retrieve_audio)
    settings_str = g_strconcat(settings_str, " retrieval", NULL);
  if (result->can_play_audio)
    settings_str = g_strconcat(settings_str, " playback", NULL);
  if (strlen(settings_str) == 0)
    settings_str = g_strconcat(settings_str, " none", NULL);
  capabilities = g_list_append(capabilities,
			       g_strdup_printf("audio_methods %s", settings_str));


  settings_str = g_strdup("");
  if (result->can_report_events_by_message)
    settings_str = g_strconcat(settings_str, " message", NULL);
  if (result->can_report_events_by_sentences)
    settings_str = g_strconcat(settings_str, " sentences", NULL);
  if (result->can_report_events_by_words)
    settings_str = g_strconcat(settings_str, " words", NULL);
  if (result->can_report_custom_index_marks)
    settings_str = g_strconcat(settings_str, " index_mark", NULL);
  if (strlen(settings_str) == 0)
    settings_str = g_strconcat(settings_str, " none", NULL);
  capabilities = g_list_append(capabilities,
			       g_strdup_printf("events %s", settings_str));


  if (result->honors_performance_guidelines == 0)
    capabilities = g_list_append(capabilities, "performance_level none");   
  else if (result->honors_performance_guidelines == 1)
    capabilities = g_list_append(capabilities, "performance_level good");   
  else if (result->honors_performance_guidelines == 2)
    capabilities = g_list_append(capabilities, "performance_level excelent");   


  settings_str = g_strdup("");
  if (result->can_parse_ssml)
    settings_str = g_strconcat(settings_str, " ssml", NULL);
  if (result->can_parse_plain)
    settings_str = g_strconcat(settings_str, " plain", NULL);
  if (strlen(settings_str) == 0)
    settings_str = g_strconcat(settings_str, " none", NULL);
  capabilities = g_list_append(capabilities,
			       g_strdup_printf("message_format %s", settings_str));


  ADD_LINE_BOOL(can_defer_message);


  ADD_LINE_BOOL(supports_multilingual_utterances);
  
  return _construct_reply(200, strdup("OK DRIVER CAPABILITIES SENT"),
			  capabilities);
}

void
_ttsapi_say_asynchro(char *request, ttsapi_msg_format format, char *data)
{
  // Post on semaphore_request_ready
  g_mutex_lock (_ttsapi_asynchro_request._mutex);
  _ttsapi_asynchro_request.request = strdup(request);
  _ttsapi_asynchro_request.data = strdup(data);
  _ttsapi_asynchro_request.format = format;
  g_cond_signal (_ttsapi_asynchro_request._cond);
  g_mutex_unlock (_ttsapi_asynchro_request._mutex);
}

TReply*
_ttsapi_say_text(GList* args, GHashTable *driver_functions, char* data){
  /* Parse arguments */
  /* Call the appropriate function */
  /* Construct reply */
  int (*driver_say_text)(ttsapi_msg_format, char*);
  int (*driver_say_text_asynchro)(ttsapi_msg_format, char*);
  ttsapi_msg_format format;
  GList *id_data = NULL;

  TIMESTAMP("Say text request");

  driver_say_text = \
    _ttsapi_get_function("say_text", driver_functions);

  driver_say_text_asynchro = \
    _ttsapi_get_function("say_text_asynchro", driver_functions);

  if (g_list_length(args) >= 1){
    char *format_str;
    /* Parse the other arguments */
    format_str = g_list_nth_data(args, 0);
    if (!strcmp(format_str, "plain")){
      format = TTSAPI_PLAIN;
    }else if (!strcmp(format_str, "ssml")){
      format = TTSAPI_SSML;
    }else{
      // Unknown format
      return _construct_reply(400, "INVALID PARAMETER", NULL);
    }
  }else{
    return _construct_reply(300, "MISSING ARGUMENT", NULL);
  }
  
  if (driver_say_text != NULL){
    int ret;
    ret = driver_say_text(format, data);
    if (ret != 0)
      return _construct_reply(300, "UNKNOWN ERROR IN DRIVER CODE", NULL);
  }else  if (driver_say_text_asynchro != NULL){
    if (data != NULL){
      _ttsapi_say_asynchro("say_text_asynchro", format, data);
    }
  }else
    return _construct_reply(300, "NOT IMPLEMENTED IN DRIVER", NULL);
  

  id_data = g_list_append(id_data, strdup("1"));

  TIMESTAMP("End of say_text");
 
  return _construct_reply(204, "OK MESSAGE RECEIVED", id_data);
}

TReply*
_ttsapi_say_deferred(GList* args, GHashTable *driver_functions){
  /* Parse arguments */
  /* Call the appropriate function */
  /* Construct reply */
  return NULL;
}

TReply*
_ttsapi_say_key(GList* args, GHashTable *driver_functions)
{
  char *key;
  int (*driver_say_key)(char*);
  int (*driver_say_key_asynchro)(char*);
  driver_say_key =					\
    _ttsapi_get_function("say_key", driver_functions);
  
  driver_say_key_asynchro =					\
    _ttsapi_get_function("say_key_asynchro", driver_functions);
  
   if (g_list_length(args) >= 1){
    /* Parse the other arguments */
    key = g_list_nth_data(args, 0);
   }else{
     return _construct_reply(300, "MISSING ARGUMENT", NULL);
   }
  
  if (driver_say_key != NULL){
    int ret = driver_say_key(key);
    if (ret != 0)
      return _construct_reply(300, "UNKNOWN ERROR IN DRIVER CODE", NULL);
  }else  if (driver_say_key_asynchro != NULL){
    if (key != NULL){
      _ttsapi_say_asynchro("say_key_asynchro", 0, key);
    }
  }else
    return _construct_reply(300, "NOT IMPLEMENTED IN DRIVER", NULL);
  
  return _construct_reply(204, "OK MESSAGE RECEIVED", NULL);
}

TReply*
_ttsapi_say_char(GList* args, GHashTable *driver_functions){
  /* Parse arguments */
  /* Call the appropriate function */
  /* Construct reply */
  char *ch;
  int (*driver_say_char)(char*);
  int (*driver_say_char_asynchro)(char*);
  driver_say_char =	\
    _ttsapi_get_function("say_char", driver_functions);
  
  driver_say_char_asynchro =					\
    _ttsapi_get_function("say_char_asynchro", driver_functions);
  
  if (g_list_length(args) >= 1){
    /* Parse the other arguments */
    ch = g_list_nth_data(args, 0);
  }else{
    return _construct_reply(300, "MISSING ARGUMENT", NULL);
  }
  
  if (driver_say_char != NULL){
    int ret = driver_say_char(ch);
    if (ret != 0)
      return _construct_reply(300, "UNKNOWN ERROR IN DRIVER CODE", NULL);
  }else  if (driver_say_char_asynchro != NULL){
    if (ch != NULL){
      _ttsapi_say_asynchro("say_char_asynchro", 0, ch);
    }
  }else
    return _construct_reply(300, "NOT IMPLEMENTED IN DRIVER", NULL);
  
  return _construct_reply(204, "OK MESSAGE RECEIVED", NULL);
}

TReply*
_ttsapi_say_icon(GList* args, GHashTable *driver_functions){
  /* Parse arguments */
  /* Call the appropriate function */
  /* Construct reply */
  char *icon;
  int (*driver_say_icon)(char*);
  int (*driver_say_icon_asynchro)(char*);
  driver_say_icon =					\
    _ttsapi_get_function("say_icon", driver_functions);
  
  
  driver_say_icon_asynchro =						\
    _ttsapi_get_function("say_icon_asynchro", driver_functions);
  
   if (g_list_length(args) >= 1){
    /* Parse the other arguments */
    icon = g_list_nth_data(args, 0);
   }else{
     return _construct_reply(300, "MISSING ARGUMENT", NULL);
   }
  
  if (driver_say_icon != NULL){
    int ret = driver_say_icon(icon);
    if (ret != 0)
      return _construct_reply(300, "UNKNOWN ERROR IN DRIVER CODE", NULL);
  }else  if (driver_say_icon_asynchro != NULL){
    if (icon != NULL){
      _ttsapi_say_asynchro("say_icon_asynchro", 0, icon);
    }
  }else
    return _construct_reply(300, "NOT IMPLEMENTED IN DRIVER", NULL);
  
  return _construct_reply(204, "OK MESSAGE RECEIVED", NULL);

}

TReply*
_ttsapi_cancel(GHashTable *driver_functions)
{
  int (*driver_cancel)(void);

  driver_cancel = _ttsapi_get_function("cancel", driver_functions);

  if (driver_cancel != NULL){
    int ret = driver_cancel();
    if (ret != 0)
      return _construct_reply(300, "CANT CANCEL MESSAGE", NULL);
  }

  return _construct_reply(200, "OK CANCELED", NULL);
}

TReply*
_ttsapi_defer(GList *args, GHashTable *driver_functions){
  /* Parse arguments */
  /* Call the appropriate function */
  /* Construct reply */
  return NULL;
}

TReply*
_ttsapi_discard(GList* args, GHashTable *driver_functions){
  /* Parse arguments */
  /* Call the appropriate function */
  /* Construct reply */
  return NULL;
}

TReply*
_ttsapi_set_voice_parameter(char* par, GList *args, GHashTable *driver_functions)
{
  int (*driver_set_func)(ttsapi_setting_mode, int);
  char *arg1, *arg2;
  ttsapi_setting_mode mode;
  int value;
  char *func_str;

  func_str = g_strdup_printf("set_%s", par);
  driver_set_func = _ttsapi_get_function(func_str, driver_functions);
  g_free(func_str);

  if (g_list_length(args) >= 3){
    /* Parse the other arguments */
    arg1 = g_list_nth_data(args, 0);
    arg2 = g_list_nth_data(args, 2);
  }else
    return _construct_reply(300, "MISSING ARGUMENT", NULL);
  
  if (!strcmp(arg1, "absolute"))
    mode = TTSAPI_ABSOLUTE;
  else if (!strcmp(arg1, "relative"))
    mode = TTSAPI_RELATIVE;
  else
    return _construct_reply(300, "INVALID ARGUMENT", NULL);

  value = strtol(arg2, NULL, 0);

  if (driver_set_func != NULL){
    int ret = driver_set_func(mode, value);
    if (ret != 0)
      return _construct_reply(300, "CANT SET GIVEN PARAMETER", NULL);
  }

  return _construct_reply(200, "OK PARAMETER SET", NULL);
}


void
_ttsapi_quit(GHashTable *driver_functions)
{
  void (*driver_quit)(void);
  driver_quit = _ttsapi_get_function("quit", driver_functions);

  if (driver_quit != NULL)
    driver_quit();

  exit(0);
}


/*
TODO:\
Functions for:
SET VOICE
SET PUNCTUATION MODE
SET PUNCTUATION DETAIL
SET CAPITAL LETTERS MODE
SET NUMBER GROUPING


GET CURRENT VOICE
GET DEFAULT ABSOLUTE RATE
GET DEFAULT ABSOLUTE PITCH
GET DEFAULT ABSOLUTE VOLUME
*/

TReply*
_ttsapi_set_audio_retrieval_destination(GList *params,
					GHashTable *driver_functions)
 {
  char *host;
  int port;
  int (*driver_func)(char*, int);

  host = g_list_nth_data (params, 0);
  port = (int) g_strtod(g_list_nth_data (params, 1), NULL);

  DBG("Setting audio retrieval host to '%s' and port to '%d'", host, port);

  driver_func = _ttsapi_get_function("set_audio_retrieval_destination",
				     driver_functions);

  driver_settings.audio_retrieval_host = host;
  driver_settings.audio_retrieval_port = port;

  if (driver_func != NULL){
    int ret = driver_func(host, port);
    if (ret != 0)
      return _construct_reply(400, "ERR CANT SET AUDIO RETRIEVAL DESTINATION", NULL);
  }

  return _construct_reply(200, "OK AUDIO RETRIEVAL SET", NULL);
}


// HELPER FUNCTIONS

void
ttsapi_driver_description_free(ttsapi_driver_description_t *dscr)
{
  g_free(dscr->driver_id);
  g_free(dscr->driver_version);
  g_free(dscr->synthesizer_name);
  g_free(dscr->synthesizer_version);
  g_free(dscr);
}


// LATERAL THREAD MAIN FUNCTION

void
_driver_lateral_thread_handler(GHashTable *driver_functions)
{
  char *req_request;
  char *req_data;
  int (*driver_say_text_asynchro)(ttsapi_msg_format, char*);
  int (*driver_say_key_asynchro)(char*);
  ttsapi_msg_format req_format;
  int ret;

  /* Terminate the thread if there are no registered functions */
  if (driver_functions == NULL)
    return;

  while (1)
    {
      // Wait for _ttsapi_asynchro_request.data to become non NULL
      g_mutex_lock(_ttsapi_asynchro_request._mutex);
      while (_ttsapi_asynchro_request.request == NULL)
	g_cond_wait (_ttsapi_asynchro_request._cond,
		     _ttsapi_asynchro_request._mutex);
      
      // Transfer request and data pointers to req_data, req_request
      req_request = _ttsapi_asynchro_request.request;
      req_data = _ttsapi_asynchro_request.data;
      req_format = _ttsapi_asynchro_request.format;
      // Clean the request (we only rely on 
      _ttsapi_asynchro_request.request = NULL;
      _ttsapi_asynchro_request.data = NULL;
      g_mutex_unlock(_ttsapi_asynchro_request._mutex);

      // Call the request in this thread
      if (!strcmp(req_request, "say_text_asynchro")){
	driver_say_text_asynchro =				\
	  _ttsapi_get_function(req_request, driver_functions);
	ret = driver_say_text_asynchro(req_format, req_data);
      }else if (!strcmp(req_request, "say_key_asynchro")){
	driver_say_key_asynchro =				\
	  _ttsapi_get_function(req_request, driver_functions);
	ret = driver_say_key_asynchro(req_data);
      }else if (!strcmp(req_request, "say_char_asynchro")){
      }else if (!strcmp(req_request, "say_icon_asynchro")){
      }
      /* Free helper variables */
      g_free(req_request);
      g_free(req_data);
      
    }
}

void
driver_send_event(event_type_t event,
		  int id,
		  signed int n,
		  int text_pos,
		  int audio_pos,
		  char *name)
{
  char *arg;

  g_mutex_lock(_driver_output_mutex);  
  if (event == EVENT_MESSAGE_BEGIN){
    arg = g_strdup_printf("message_start %d %d %d", id, (int) text_pos, (int) audio_pos);
    com_write_reply(_construct_reply_strarg(701, "MESSAGE EVENT", arg));
    g_free(arg);
  }
  else if (event == EVENT_MESSAGE_END){
    arg = g_strdup_printf("message_end %d %d %d", id, (int) text_pos, (int) audio_pos);
    com_write_reply(_construct_reply_strarg(701, "MESSAGE EVENT", arg));
    g_free(arg);
  }
  else if (event == EVENT_SENTENCE_BEGIN){
    arg = g_strdup_printf("sentence_start %d %d %d %d", id, n, (int) text_pos, (int) audio_pos);
    com_write_reply(_construct_reply_strarg(701, "SENTENCE OR WORD EVENT", arg));
    g_free(arg);
  }
  else if (event == EVENT_SENTENCE_END){
    arg = g_strdup_printf("sentence_end %d %d %d %d", id, n, (int) text_pos, (int) audio_pos);
    com_write_reply(_construct_reply_strarg(702, "SENTENCE OR WORD EVENT"
					    , arg));
    g_free(arg);
  }
  else if (event == EVENT_WORD_BEGIN){
    arg = g_strdup_printf("word_start %d %d %d %d", id, n, (int) text_pos, (int) audio_pos);
    com_write_reply(_construct_reply_strarg(702, "SENTENCE OR WORD EVENT", arg));
    g_free(arg);
  }
  else if (event == EVENT_WORD_END){
    arg = g_strdup_printf("word_end %d %d %d %d", id, n, (int) text_pos, (int) audio_pos);
    com_write_reply(_construct_reply_strarg(702, "SENTENCE OR WORD EVENT", arg));
    g_free(arg);
  }
  else if (event == EVENT_INDEX_MARK){
    assert(name != NULL);
    arg = g_strdup_printf("index_mark %d \"%s\" %d %d", id, name, (int) text_pos, (int) audio_pos);
    com_write_reply(_construct_reply_strarg(702, "INDEX MARK EVENT", arg));
    g_free(arg);
  }else if (event == EVENT_NONE){
    ;
  }else{
    /* Unknown callback */
    assert(0);
  }
  g_mutex_unlock(_driver_output_mutex);  
}

FILE*
driver_audio_connection_init(char *host, int port)
{
  struct sockaddr_in address;
  char tcp_no_delay = 1;
  int sock;
  int ret;
  FILE *stream;

  /* Connect to socket */
  address.sin_addr.s_addr = inet_addr(host);
  address.sin_port = htons(port);
  address.sin_family = AF_INET;
  sock = socket(AF_INET, SOCK_STREAM, 0);

  ret = connect(sock, (struct sockaddr *)&address, sizeof(address));
  if (ret == -1){
    DBG("ERROR: Can't connect to audio server on %s %d: %s",
	host, port, strerror(errno));
    return NULL;
  }

  /* Disable Nagles's algorithm (performance reasons) */
  setsockopt(sock, IPPROTO_TCP, TCP_NODELAY, &tcp_no_delay, sizeof(int));

  /* Create a stream */
  stream = fdopen(sock, "w");
  if (!stream){
    DBG("ERROR: Can't create a stream for socket, fdopen() failed.");
    return NULL;
  }

  /* Switch to line buffering mode */
  ret = setvbuf(stream, NULL, _IONBF, 4096);
  if (ret){
    DBG("ERROR: Can't set buffering, setvbuf failed.");
    return NULL;
  }

  return stream;
}


int
driver_send_audio(FILE* audio_server_stream, ttsapi_audio_block_t *block)
{
  GString *output;
  int ret;

  assert(audio_server_stream != NULL);

  TIMESTAMP("Request to send audio block %d for message %d", block->number, block->msg_id);

  output = g_string_new("");

  if (block == NULL) return -1;

  g_string_append_printf(output, "BLOCK %d %d"NEWLINE, block->msg_id, block->number);

  g_string_append_printf(output, "PARAMETERS"NEWLINE);
  /* Construct and write out data format */
  {
    char *data_format_str;
    switch(block->data_format){
    case TTSAPI_RAW: data_format_str = strdup("raw"); break;
    case TTSAPI_WAV: data_format_str = strdup("wav"); break;
    case TTSAPI_OGG: data_format_str = strdup("ogg"); break;
    default: 
      DBG("Invalid audio format passed to driver_send_audio()");
      return -1;
    }
    g_string_append_printf(output, "data_format %s"NEWLINE, data_format_str);
    g_free(data_format_str);
  }
  DBG("INCOMMING Data length: %ld", block->data_length);
  g_string_append_printf(output, "data_length %ld"NEWLINE, block->data_length);
  g_string_append_printf(output, "audio_length %ld"NEWLINE, block->audio_length);
  g_string_append_printf(output, "sample_rate %d"NEWLINE, block->sample_rate);
  g_string_append_printf(output, "channels %d"NEWLINE, block->channels);
  
  {
    GString *encoding_str;
    encoding_str = g_string_new("");

    if (block->encoding_sign > 0)
      g_string_append_printf(encoding_str, "s");
    else
      g_string_append_printf(encoding_str, "u");

    g_string_append_printf(encoding_str, "%d", block->encoding_bpw);
    
    if (block->encoding_endian == TTSAPI_LE)
      g_string_append_printf(encoding_str, "LE");
    else
      g_string_append_printf(encoding_str, "BE");

    g_string_append_printf(output, "encoding %s"NEWLINE, encoding_str->str);
    g_string_free(encoding_str, 1);
  }

  g_string_append_printf(output, "END OF PARAMETERS"NEWLINE);
  g_string_append_printf(output, "EVENTS"NEWLINE);
  /* TODO: EVENTS */
  g_string_append_printf(output, "END OF EVENTS"NEWLINE);
  DBG("Sending to audio server |%s| (data section ommited)", output->str);
  g_string_append_printf(output, "DATA"NEWLINE);
  if (block->data){
    DBG("Appending data");
    g_string_append_len(output, (char*) block->data, block->data_length);
  }
  g_string_append_printf(output, "END OF DATA"NEWLINE);

  DBG("OUTPUTING: ||%s||", output->str);
  ret = fwrite(output->str, output->len, 1, audio_server_stream);
  if (ret <= 0){
    DBG("Written 0 or -1 bytes, error: %s", strerror(errno));
  }
  DBG("Written %d bytes out of %ld into audio socket", ret, output->len);
  fflush(audio_server_stream);

  TIMESTAMP("Data block sent to audio");  

  g_string_free(output, 1);

  return 0;
}



// MAIN LOOP


int
driver_main_loop(GHashTable* function_dictionary){
  /* Main server loop

     function_dictionary: Dictionary of all TTS API functions to call
     on the associated request. All of these functions are called
     in a blocking mode (in the same thread where main_loop() is
     executed.
   */

  // Raad a command as a Glist* of atoms
  
  char *c1, *c2, *c3;
  GList *command;

  TTSAPI_DRIVER_DEBUGGING = 0;
  TTSAPI_DRIVER_TIMING = 1;

  /* Init _ttsapi_asynchro_request */
  g_thread_init(NULL);
  _ttsapi_asynchro_request._cond = g_cond_new();
  _ttsapi_asynchro_request._mutex = g_mutex_new();
  _ttsapi_asynchro_request.request = NULL;
  
  /* Initialize the lateral thread */
  _driver_lateral_thread =  g_thread_create((GThreadFunc) _driver_lateral_thread_handler,
					    (gpointer) function_dictionary,
					    0, NULL);

  _driver_output_mutex = g_mutex_new();
  
  while (TRUE){
    TReply *result = NULL;
    
    // Read command
    command = com_read_command();

    g_mutex_lock(_driver_output_mutex);    
    // Call the appropriate function with the given arguments
    if (g_list_length(command) == 1){
      c1 = g_list_nth_data (command, 0);
      if (!strcmp(c1,"INIT")){
	result = _ttsapi_init(function_dictionary);
      }
      else if (!strcmp(c1, "CANCEL")){     
	result = _ttsapi_cancel(function_dictionary);
      }else if (!strcmp(c1,"DEFER"))
	result = _ttsapi_defer(g_list_nth(command, 1), function_dictionary);    
      else if (!strcmp(c1,"DISCARD"))
	result = _ttsapi_discard(g_list_nth(command, 1), function_dictionary);    
      else if (!strcmp(c1, "QUIT")){
	_ttsapi_quit(function_dictionary);
      }
    } else if (g_list_length(command) >= 2){ 
      c1 = g_list_nth_data (command, 0);
      c2 = g_list_nth_data (command, 1);
      if (!strcmp(c1, "LIST") && (!strcmp(c2, "DRIVERS")))
	result = _ttsapi_list_drivers(function_dictionary);
      if (!strcmp(c1, "LIST") && (!strcmp(c2, "VOICES")))
	result = _ttsapi_list_voices(function_dictionary);
      if (!strcmp(c1, "DRIVER") && (!strcmp(c2, "CAPABILITIES")))
	result = _ttsapi_driver_capabilities(function_dictionary);
      if (!strcmp(c1, "SAY") && !strcmp(c2, "TEXT")){
	GString *data;
	/* Write reply on first part */
	com_write_reply(_construct_reply(299, "OK RECEIVING DATA", NULL));
	/* Read data */
	data = g_string_new("");
	while(1){
	  char *line;
	  line = com_read_line();
	  /* Terminate on single dot, otherwise read the data */
	  if (!strcmp(g_strstrip(line), ".")){
	    break;
	  }else{
	    g_string_append(data, line);
	    g_free(line);
	  }
	}
	/* Continue with command processing */
	
	/* TODO: Resolve all SAY TEXT variants and call the appropriate functions */
	result = _ttsapi_say_text(g_list_nth(command, 2), function_dictionary, data->str);
	g_string_free(data, 1);
      }else if (!strcmp(c1, "SAY") && !strcmp(c2, "CHAR")){
	result = _ttsapi_say_char(g_list_nth(command, 2), function_dictionary);
      }else if (!strcmp(c1, "SAY") && !strcmp(c2, "KEY")){
	result = _ttsapi_say_key(g_list_nth(command, 2), function_dictionary);
      }else if (!strcmp(c1, "SAY") && !strcmp(c2, "ICON")){
	result = _ttsapi_say_icon(g_list_nth(command, 2), function_dictionary);
      }

    }
    if (g_list_length(command) >= 3){ 
      c1 = g_list_nth_data (command, 0);
      c2 = g_list_nth_data (command, 1);
      c3 = g_list_nth_data (command, 2);

      if (!strcmp(c1, "SET") && (!strcmp(c2, "MESSAGE")) && (!strcmp(c3, "ID"))){
	// TODO:	  
	result = _construct_reply(200, strdup("OK ID SET"), NULL);
      }
      else if (!strcmp(c1, "SET") && (!strcmp(c2, "AUDIO")) && (!strcmp(c3, "OUTPUT"))){
	// TODO:	  
	result = _construct_reply(200, strdup("OK AUDIO OUTPUT SET"), NULL);
      }
      else if (!strcmp(c1, "SET") && (!strcmp(c3, "RATE"))){
	result = _ttsapi_set_voice_parameter("rate",
					     g_list_nth(command, 1),
					     function_dictionary);
      }
      else if (!strcmp(c1, "SET") && (!strcmp(c3, "PITCH"))){
	result = _ttsapi_set_voice_parameter("pitch",
					     g_list_nth(command, 1),
					     function_dictionary);
      }
      else if (!strcmp(c1, "SET") && (!strcmp(c3, "PITCH_RANGE"))){
	result = _ttsapi_set_voice_parameter("pitch_range",
					     g_list_nth(command, 1),
					     function_dictionary);
      }
      else if (!strcmp(c1, "SET") && (!strcmp(c3, "VOLUME"))){
	result = _ttsapi_set_voice_parameter("volume",
					     g_list_nth(command, 1),
					     function_dictionary);
      }     
      if (!strcmp(c1, "SET") && !strcmp(c2, "AUDIO") 
	  && !strcmp(c3, "RETRIEVAL")){       
	result = _ttsapi_set_audio_retrieval_destination(g_list_nth(command, 3),
							 function_dictionary);
      }
    }
    
    if (result == NULL){
      result = _construct_reply(400, strdup("INVALID COMMAND"), NULL);
    }
    
    // Write command reply
    com_write_reply(result);
    _free_reply(result);

    //Unlock output mutex
    g_mutex_unlock(_driver_output_mutex);
  }
}

