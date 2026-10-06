ARG BASE_IMAGE=ubuntu:24.04
FROM ${BASE_IMAGE}
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3 zsh git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/zsh dotfiles-test
COPY . /opt/dotfiles
USER dotfiles-test
ENV HOME=/home/dotfiles-test TERM=xterm-256color
WORKDIR /home/dotfiles-test
RUN printf '%s\n' 'export DOTFILES_OLD_CONFIG=1' > .zshrc \
    && /opt/dotfiles/install-container.sh
CMD ["python3", "/opt/dotfiles/tests/container_smoke.py"]
