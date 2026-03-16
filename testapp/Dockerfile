FROM emscripten/emsdk:3.1.51

ARG UID=1000
ARG GID=1000

RUN groupadd -f -g ${GID} worker && \
    useradd -m -u ${UID} -g ${GID} -o worker

USER worker
WORKDIR /home/worker/source

CMD ["bash", "/home/worker/source/testapp/build.sh"]