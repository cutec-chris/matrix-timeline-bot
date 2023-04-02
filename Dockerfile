FROM alpine
RUN mkdir /bot
RUN mkdir /bot/source
RUN mkdir /data
COPY source/* /bot/source/
RUN apk add py3-pip py3-lxml py3-cryptography py3-aiohttp py3-yaml py3-pillow py3-beautifulsoup4 py3-urllib3 py3-future py3-pycryptodomex py3-feedparser gcc g++ make libffi-dev openssl-dev build-base python3-dev
RUN export PIP_DEFAULT_TIMEOUT=100 && pip3 install -r /bot/source/requirements.txt
WORKDIR /data/
CMD [ "python3", "/bot/source/bot.py" ]
