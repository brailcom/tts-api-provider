#!/bin/bash

makeinfo tts-api-provider.texi &&
texi2dvi tts-api-provider.texi &&
texi2dvi --pdf tts-api-provider.texi &&
makeinfo --html --no-split tts-api-provider.texi
