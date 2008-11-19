
AM_CFLAGS = -Wall -I/usr/include/ $(inc_local) @glib_include@ 
driverbin_PROGRAMS = 

if espeak_support
driverbin_PROGRAMS += espeak
endif

espeak_SOURCES = espeak.c ttsapi.c ttsapi.h

espeak_LDADD = -lm @glib_libs@ @gthread_libs@ -lespeak
