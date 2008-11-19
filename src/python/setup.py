#!/usr/bin/env python
from distutils.core import setup
setup(name='tts-api-provider',
      version='0.0',
      requires=[],
      packages=['provider', 'ttsapi', 'drivers', 'clients'],
      description = "TTS API Provider",
      author = "Hynek Hanke, Brailcom o.p.s.",
      author_email = "hanke@brailcom.org",
      url = "http://www.freebsoft.org/tts-api-provider/"
      )
