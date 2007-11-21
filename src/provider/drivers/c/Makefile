
LIBS = -lm -lglib-2.0 -lgthread-2.0 -lespeak
FLAGS = -Wall -I/usr/include/glib-2.0 -I/usr/lib/glib-2.0/include
CC = gcc -g $(LIBS) $(FLAGS)
  
DESC_DIR = /usr/local/bin

all: espeak

espeak: espeak.o ttsapi.o 
	$(CC) -o $@ espeak.o ttsapi.o  

ttsapi: ttsapi.o
	$(CC) -c -o $@ ttsapi.o 

clean:
	-rm -f *.o espeak

install:
	cp espeak $(DESC_DIR)

# DO NOT DELETE
ttsapi.o: ttsapi.c
espeak.o: espeak.c
