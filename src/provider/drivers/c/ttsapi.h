
// C API of TTS API implementation header file

// Standard library
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <assert.h>
#include <sys/time.h>

// GLib
#include <glib.h>

// GETLINE
//TODO: Why is this not imported via stdio.h??
size_t getline (char **__lineptr, size_t *__n, FILE *__stream);

// COMMUNICATION

#define NEWLINE "\r\n"

typedef struct{
  int code;
  char* text;
  GList *data;
}TReply;


char* com_read_line(void);
int com_write_reply(TReply *reply);

TReply* _ttsapi_init(GHashTable *driver_functions);
TReply* _ttsapi_list_drivers (GHashTable *driver_functions);
TReply* _ttsapi_list_voices (GHashTable *driver_functions);
TReply* _ttsapi_driver_capabilities (GHashTable *driver_functions);
TReply* _ttsapi_say_text(GList* args, GHashTable *driver_functions, char* data);
TReply* _ttsapi_say_deferred(GList* args, GHashTable *driver_functions);
TReply* _ttsapi_say_key(GList* args, GHashTable *driver_functions);
TReply* _ttsapi_say_char(GList* args, GHashTable *driver_functions);
TReply* _ttsapi_say_icon(GList* args, GHashTable *driver_functions);
TReply* _ttsapi_cancel(GHashTable *driver_functions);
TReply* _ttsapi_defer(GList* args, GHashTable *driver_functions);
TReply* _ttsapi_discard(GList* args, GHashTable *driver_functions);
void _ttsapi_quit(GHashTable *driver_functions);


// MAIN LOOP
int driver_main_loop(GHashTable* function_dictionary);


typedef struct {
    char*           driver_id;
    char*           driver_version;
    char*           synthesizer_name;
    char*           synthesizer_version;
} ttsapi_driver_description_t;

typedef enum {
  TTSAPI_NONE = 0,
  TTSAPI_MALE = 1,
  TTSAPI_FEMALE = 2
} ttsapi_voice_gender;

typedef enum {
  TTSAPI_ABSOLUTE = 0,
  TTSAPI_RELATIVE = 1
} ttsapi_setting_mode;

typedef struct {
  char *name;
  char *language;
  char *dialect;
  ttsapi_voice_gender gender;
  unsigned int age;
} ttsapi_voice_description_t;


typedef enum {
  TTSAPI_PLAIN = 0,
  TTSAPI_SSML = 1
} ttsapi_msg_format;


typedef struct {
  /* Voice discovery */ 
  gboolean can_list_voices;
  gboolean can_set_voice_by_properties;
  gboolean can_get_current_voice;
  
  /* Prosody parameters */
  gboolean can_set_rate_relative;
  gboolean can_set_rate_absolute;
  gboolean can_get_default_rate;
  
  gboolean can_set_pitch_relative;
  gboolean can_set_pitch_absolute;
  gboolean can_get_default_pitch;
  
  gboolean can_set_pitch_range_relative;
  gboolean can_set_pitch_range_absolute;
  gboolean can_get_default_pitch_range;
  
  gboolean can_set_volume_relative;
  gboolean can_set_volume_absolute;
  gboolean can_get_default_volume;
  
  /* Style parameters */
  gboolean can_set_punctuation_mode_all;
  gboolean can_set_punctuation_mode_none;
  gboolean can_set_punctuation_mode_some;
  gboolean can_set_punctuation_detail;
  
  gboolean can_set_capital_letters_mode_spelling;
  gboolean can_set_capital_letters_mode_icon;
  gboolean can_set_capital_letters_mode_pitch;
  
  gboolean can_set_number_grouping;
  
  /* Synthesis */
  gboolean can_say_text_from_position;
  gboolean can_say_char;
  gboolean can_say_key;
  gboolean can_say_icon;
  
  /* Dictionaries */
  gboolean can_set_dictionary;
  
  /* Audio playback/retrieval */
  gboolean can_retrieve_audio;
  gboolean can_play_audio;
  
  /* Events and index marking */
  gboolean can_report_events_by_message;
  gboolean can_report_events_by_sentences;
  gboolean can_report_events_by_words;
  gboolean can_report_custom_index_marks;
  
  /* Performance guidelines */
  int honors_performance_guidelines;
  
  /* Defering messages */
  gboolean can_defer_message;
   
  /* Message format Support */
  gboolean can_parse_ssml;
  gboolean can_parse_plain;
   
  /* Multilingual utterences */ 
  gboolean supports_multilingual_utterances;
} ttsapi_driver_capabilities_t;


typedef struct {
  char *request;
  char *data;
  ttsapi_msg_format format;
  GMutex *_mutex;
  GCond *_cond;
} _ttsapi_asynchro_request_t;


/* Debugging */
#define DBG(arg...) \
  {		    \
    time_t t; \
    struct timeval tv; \
    char *tstr; \
    t = time(NULL); \
    tstr = strdup(ctime(&t)); \
    tstr[strlen(tstr)-1] = 0; \
    gettimeofday(&tv,NULL); \
    fprintf(stderr," %s [%d]",tstr, (int) tv.tv_usec); \
    fprintf(stderr, ": "); \
    fprintf(stderr, arg); \
    fprintf(stderr, "\n"); \
    fflush(stderr); \
    g_free(tstr); \
  }

/* Helper macros for the main driver function */

#define DRIVER_INIT_FUNCTIONS_LIST(func) \
  GHashTable *driver_functions; \
  driver_functions = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, NULL);

#define DRIVER_REGISTER_FUNCTION(func) \
  g_hash_table_insert(driver_functions, strdup(#func), func);

#define  DRIVER_RUN() \
  driver_main_loop(driver_functions);


typedef enum {
  EVENT_MESSAGE_BEGIN,
  EVENT_MESSAGE_END,    
  EVENT_SENTENCE_BEGIN,
  EVENT_SENTENCE_END,
  EVENT_WORD_BEGIN,
  EVENT_WORD_END,
  EVENT_INDEX_MARK,
  EVENT_NONE
} event_type_t;

// EVENT HANDLER
void driver_send_event(event_type_t event, int id,
		       signed int n, int text_pos, int audio_pos, 
		       char *name);

typedef enum {
  TTSAPI_RAW,
  TTSAPI_WAV,
  TTSAPI_OGG
} ttsapi_audio_data_format;

typedef enum {
  TTSAPI_LE,
  TTSAPI_BE
} ttsapi_endian;

typedef struct{
  int msg_id;
  int number;
  ttsapi_audio_data_format data_format;
  size_t data_length;
  size_t audio_length;
  int sample_rate;
  int channels;
  int encoding_sign;
  int encoding_bpw;
  ttsapi_endian encoding_endian;
  GList *events_list;
  void *data;
}ttsapi_audio_block_t;

typedef struct{
  char *audio_retrieval_host;
  int audio_retrieval_port;
}ttsapi_driver_settings_t;


FILE* driver_audio_connection_init(char *host, int port);
int driver_send_audio(FILE* audio_server_stream, ttsapi_audio_block_t *block);

