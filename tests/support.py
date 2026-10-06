import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def atomic_write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)


def fake_font(family="Test Mono", style="Regular", version=None):
    strings = [family.encode("utf-16-be"), style.encode("utf-16-be")]
    ids = [1, 2]
    if version:
        strings.append(("Version " + version).encode("utf-16-be")); ids.append(5)
    table = struct.pack(">HHH", 0, len(strings), 6 + 12 * len(strings))
    offset = 0
    for name_id, text in zip(ids, strings):
        table += struct.pack(">HHHHHH", 3, 1, 0x409, name_id, len(text), offset)
        offset += len(text)
    table += b"".join(strings)
    return struct.pack(">IHHHH", 0x10000, 1, 16, 0, 0) + struct.pack(">4sIII", b"name", 0, 28, len(table)) + table


class Isolated(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dotbot-tests-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.home = self.base / "home with spaces"
        self.home.mkdir()
        self.source = self.base / "public checkout"
        shutil.copytree(ROOT, self.source, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        self.tools = self.base / "tools"; self.tools.mkdir()
        atomic_write(self.tools / "uname", b'#!/bin/sh\ncase "$1" in -sm) echo "Darwin arm64";; -m) echo arm64;; *) echo Darwin;; esac\n', 0o755)
        self.env = patch.dict(os.environ, {
            "HOME": str(self.home), "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_CACHE_HOME": str(self.home / ".cache"), "XDG_DATA_HOME": str(self.home / ".local/share"),
            "XDG_STATE_HOME": str(self.home / ".local/state"),
            "PATH": str(self.tools) + ":" + str(self.home / ".local/bin") + ":/usr/bin:/bin:/usr/sbin:/sbin",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0", "PYTHONDONTWRITEBYTECODE": "1",
        })
        self.env.start(); self.addCleanup(self.env.stop)

    def command(self, *args, check=True):
        return subprocess.run([str(self.source / "bin/dotfiles"), *map(str,args)], check=check, capture_output=True, text=True)

    def apply(self):
        return self.command("link")

    def private(self):
        source = self.base / "private checkout"
        source.mkdir()
        shutil.copy2(ROOT.parent / "private/install.conf.yaml", source / "install.conf.yaml") if (ROOT.parent / "private/install.conf.yaml").exists() else (source / "install.conf.yaml").write_text('''- defaults:
    link: {create: true, relink: true, backup: true}
- link:
    ~/.config/: {glob: true, path: 'config/**'}
    ~/.ssh/: {glob: true, path: 'ssh/**', exclude: ['ssh/config', 'ssh/hosts']}
    ~/.ssh/config.private: {path: 'machines/$DOTFILES_MACHINE_PROFILE/ssh/config'}
    ~/.ssh/hosts: {path: 'machines/$DOTFILES_MACHINE_PROFILE/ssh/hosts'}
    ~/.aws/config: {path: 'machines/$DOTFILES_MACHINE_PROFILE/aws/config'}
    ~/.config/atuin-machine/env.sh: {path: 'machines/$DOTFILES_MACHINE_PROFILE/atuin/env.sh'}
    ~/.config/atuin-machine/ai-token-reference: {path: 'machines/$DOTFILES_MACHINE_PROFILE/atuin/ai-token-reference'}
''')
        for name in ("personal", "work", "client"):
            atomic_write(source / "config/git/identities" / name, (
                f'[user]\nname = {name}\nemail = {name}@example.test\nsigningKey = ssh-ed25519 AAAATEST\n'
                '[commit]\ngpgsign = true\n[gpg]\nformat = ssh\n'
                '[gpg "ssh"]\nprogram = /Applications/1Password.app/Contents/MacOS/op-ssh-sign\n').encode(), 0o600)
        atomic_write(source / "config/git/private", b'[include]\npath = ~/.config/git/default-identity\n[includeIf "gitdir:~/Code/work/"]\npath = identities/work\n[includeIf "gitdir:~/Code/work/client/"]\npath = identities/client\n', 0o600)
        atomic_write(source / "ssh/allowed_signers", b'fixture@example.test ssh-ed25519 AAAATEST\n', 0o600)
        for name in ('personal','work'):
            machine=source/'machines'/name
            atomic_write(machine / "atuin/env.sh", (
                f'export ATUIN_SYNC_ADDRESS="http://127.0.0.1:1/{name}"\n'
                f'export ATUIN_AI__ENDPOINT="http://127.0.0.1:1/{name}"\n').encode(), 0o600)
            atomic_write(machine / "atuin/ai-token-reference", b'\n', 0o600)
            atomic_write(machine / "ssh/config", ('Include "' + str(self.home / '.ssh/hosts') + '"\n').encode(), 0o600)
            atomic_write(machine / "ssh/hosts", ('Host fixture\n    HostName '+name+'.example.test\n').encode(), 0o600)
            atomic_write(machine / "aws/config", ('[profile '+name+']\nregion = us-west-2\n').encode(), 0o600)
        return source
