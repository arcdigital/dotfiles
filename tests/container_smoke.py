"""Real container acceptance checks, run as a non-root user after bootstrap."""
import os
from pathlib import Path
import subprocess

home = Path.home()
repo = Path(__file__).resolve().parents[1]
os.environ["PATH"] = str(home / ".local/bin") + ":" + os.environ["PATH"]
assert os.getuid() != 0
assert not (home / ".config/mise/config.toml").exists()
for path in (".aws/config", ".ssh/config", ".config/ghostty", ".config/atuin-machine"):
    assert not (home / path).exists(), path
backups = sorted(home.glob(".zshrc.dotbot-backup.*"))
assert any(p.read_text() == "export DOTFILES_OLD_CONFIG=1\n" for p in backups)
subprocess.run([str(repo / "install-container.sh")], check=True)
assert sorted(home.glob(".zshrc.dotbot-backup.*")) == backups
for command in (["zsh", "-d", "-i", "-c", "command -v mise; command -v starship"],
                [str(repo / "bin/dotfiles"), "doctor"], ["starship", "prompt"]):
    subprocess.run(command, check=True)
print("Container smoke checks passed.")
