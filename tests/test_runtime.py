import os
from pathlib import Path
import subprocess
from support import Isolated, atomic_write, run

class RuntimeTests(Isolated):
    def test_starship_parses_mocha_configuration(self):
        if not os.environ.get("STARSHIP_BIN"): self.skipTest("Set STARSHIP_BIN for real client checks")
        self.apply()
        env = dict(os.environ, STARSHIP_CONFIG=str(self.home / ".config/starship.toml"),
                   STARSHIP_CACHE=str(self.home / ".cache/starship"), TERM="xterm-256color")
        result = run([os.environ["STARSHIP_BIN"], "prompt"], cwd=self.home, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertNotIn("Error", result.stderr)
        self.assertNotIn("Failed", result.stderr)
        self.assertTrue(result.stdout.strip())

    def test_real_mise_global_and_project_precedence(self):
        if not os.environ.get("MISE_BIN"): self.skipTest("Set MISE_BIN for real runtime selection")
        self.apply()
        mise = os.environ["MISE_BIN"]
        env = dict(os.environ, MISE_DATA_DIR=str(self.home / ".local/share/mise"),
                   MISE_CACHE_DIR=str(self.home / ".cache/mise"), MISE_STATE_DIR=str(self.home / ".local/state/mise"),
                   MISE_CONFIG_DIR=str(self.home / ".config/mise"), MISE_YES="1", MISE_AUTO_INSTALL="0")
        run([mise, "trust", self.home / ".config/mise/config.toml"], env=env, capture_output=True)
        global_version, project_version = "24.0.0", "22.0.0"
        # Resolve the moving LTS alias to a local fixture without downloading Node.
        config = self.home / ".config/mise/config.toml"
        with config.open("a") as target:
            target.write('\n[alias.node.versions]\nlts = "' + global_version + '"\n')
        for version in (global_version, project_version):
            runtime = self.base / ("node-" + version)
            atomic_write(runtime / "bin/node", ("#!/bin/sh\necho v" + version + "\n").encode(), 0o755)
            run([mise, "link", "node@" + version, runtime], cwd=self.home, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        global_node = run([mise, "which", "node"], cwd=self.home, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()
        self.assertTrue(Path(global_node).is_file())
        global_actual = run([mise, "exec", "--", "node", "--version"], cwd=self.home, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()
        self.assertEqual(global_actual, "v" + global_version)
        project = self.home / "project"
        project.mkdir()
        (project / "mise.toml").write_text('[tools]\nnode = "' + project_version + '"\n')
        run([mise, "trust", project / "mise.toml"], env=env, cwd=project, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        project_node = run([mise, "which", "node"], cwd=project, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()
        self.assertIn(project_version, project_node)
        actual = run([mise, "exec", "--", "node", "--version"], cwd=project, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()
        self.assertEqual(actual, "v" + project_version)


class AtuinTests(Isolated):
    def test_real_machine_configs_preserve_default_history(self):
        binary=os.environ.get('ATUIN_BIN')
        if not binary:self.skipTest('Set ATUIN_BIN for real history checks')
        self.apply()
        # Keep fixture history operations in-process without starting a daemon.
        config=self.home/'.config/atuin/config.toml'
        config.write_text(config.read_text().replace('search_mode = "daemon-fuzzy"','search_mode = "fuzzy"').replace('enabled = true','enabled = false').replace('autostart = true','autostart = false').replace('auto_sync = true','auto_sync = false'))
        env=dict(os.environ,ATUIN_CONFIG_DIR=str(self.home/'.config/atuin'),ATUIN_THEME_DIR=str(self.home/'.config/atuin/themes'),ATUIN_SESSION='00000000000000000000000000000001')
        def atuin(*args):
            return run(['bash','-c','source "$HOME/.config/atuin/env.sh"; exec "$@"','atuin',binary,*args],env=env,cwd=self.home,capture_output=True,text=True).stdout.strip()
        # Seed existing history before linking either private machine configuration.
        identifier=atuin('history','start','echo restored-history-fixture')
        atuin('history','end','--exit','0',identifier)
        self.assertTrue((self.home/'.local/share/atuin/history.db').is_file())
        private=self.private()
        self.command('private-setup',private,'--identity','personal')
        for machine in ('personal','work','personal'):
            self.command('brew-profile',machine)
            self.command('link','--private')
            info=atuin('info')
            self.assertIn(str(self.home/'.local/share/atuin/history.db'),info)
            history=atuin('search','--cmd-only')
            self.assertEqual(history,'echo restored-history-fixture')
