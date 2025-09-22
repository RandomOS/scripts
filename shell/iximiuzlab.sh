#!/bin/bash

# curl -fsSL https://gitlab.com/RandomK/scripts/raw/master/shell/iximiuzlab.sh | sudo bash

STARSHIP_VERSION="1.8.0"

install_pkg() {
    apt-get install -y fish lftp tmux tmuxp >/dev/null 2>&1

    mkdir -p /tmp/install \
        && cd /tmp/install \
        && wget -q -O data.tar.gz https://github.com/starship/starship/releases/download/v${STARSHIP_VERSION}/starship-x86_64-unknown-linux-musl.tar.gz \
        && tar -xf data.tar.gz \
        && cp -f starship /usr/local/bin/
}

init_root_config() {
    mkdir -p /root/.config/htop /root/.config/fish /root/.config/tmuxp
    curl -4sk -o /root/.bashrc https://gist.githubusercontent.com/RandomOS/09ad75edaf5e27548f7314c11cb9d30c/raw/f7209c5f8c6641f155e529a80e887573e15e8b2c/.bashrc
    curl -4sk -o /root/.vimrc https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.vimrc
    curl -4sk -o /root/.tmux.conf https://cdn.jsdelivr.net/gh/randomos/dockerfiles@master/alpine-lab/root/.tmux.conf
    curl -4sk -o /root/.config/htop/htoprc https://gist.githubusercontent.com/RandomOS/09ad75edaf5e27548f7314c11cb9d30c/raw/8a10b2f2cfa23af0cf0ad320458869a64e58d0e8/htoprc

    cat <<'EOF' >/root/.config/fish/config.fish
# Aliases
alias ll='ls -lha'
alias gocache='cd /run/shm'
alias csearch='apt-cache search'
alias mps='ps -u $USER -f f'

# starship
starship init fish | source
EOF

    cat <<'EOF' >/root/.config/tmuxp/dev.yaml
session_name: dev
start_directory: /dev/shm
windows:
  - window_name: fish
    focus: true
    panes:
    - shell_command:
      - fish
      - clear
      focus: true
  - window_name: bash
    panes:
    - shell_command:
      - clear
      focus: true
  - window_name: bash
    panes:
    - shell_command:
      - clear
      focus: true
EOF
}

init_user_config() {
    mkdir -p /home/laborant/.config/fish
    cp -f /root/.config/fish/config.fish /home/laborant/.config/fish/
    cp -f /root/.vimrc /home/laborant/
    cp -f /root/.tmux.conf /home/laborant/
    chown -R laborant:laborant /home/laborant
}

init_config() {
    init_root_config
    init_user_config
}

init_system() {
    chmod u+s /bin/ping
    chown -R root:root /usr/local/bin /usr/local/share/btop
    timedatectl set-timezone Asia/Shanghai
}

main() {
    install_pkg
    init_config
    init_system
}

main "$@"
