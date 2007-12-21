#!/usr/bin/env python
from distutils.core import setup
setup(name='tts-api-provider',
      version='0.0',
      packages=['tts-api-provider', 'ttsapi'],
      description = "TTS API Provider",
      author = "Hynek Hanke, Brailcom o.p.s.",
      author_email = "hanke@brailcom.org",
      url = "http://www.freebsoft.org/tts-api-provider/",
      package_dir = {'': 'src'}
      )
