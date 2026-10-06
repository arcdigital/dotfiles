import json
import os
from pathlib import Path
import shutil
import subprocess
from support import Isolated, ROOT, atomic_write, run


class LinkTests(Isolated):
    def test_shared_skill_links_preserve_existing_skills_and_backups(self):
        source = self.source/'skills/find-skills'
        old = self.home/'.agents/skills/find-skills'
        atomic_write(old/'SKILL.md', b'original skill\n')
        system = self.home/'.codex/skills/.system/fixture/SKILL.md'
        atomic_write(system, b'bundled skill\n')
        unrelated = self.home/'.claude/skills/unmanaged/SKILL.md'
        atomic_write(unrelated, b'unmanaged skill\n')
        self.command('diff')
        self.assertFalse(old.is_symlink())
        self.apply()
        for agent in ('.agents', '.claude'):
            target = self.home/agent/'skills/find-skills'
            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), source)
        self.assertFalse((source/'SKILL.md').is_symlink())
        backup_root = self.home/'.local/state/dotfiles/skill-backups'
        backups = list(backup_root.glob('*/find-skills/SKILL.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), 'original skill\n')
        self.assertFalse(list(old.parent.glob('*.dotbot-backup.*')))
        (old/'SKILL.md').write_text('edited through link\n')
        self.assertEqual((source/'SKILL.md').read_text(), 'edited through link\n')
        self.apply()
        self.assertEqual(list(backup_root.glob('*/find-skills/SKILL.md')), backups)
        self.assertEqual(system.read_text(), 'bundled skill\n')
        self.assertEqual(unrelated.read_text(), 'unmanaged skill\n')

    def test_skill_conflicts_fail_before_linking_and_broken_links_are_saved(self):
        original = self.home/'.zshrc'
        original.write_text('keep\n')
        elsewhere = self.base/'elsewhere'
        elsewhere.mkdir()
        (self.home/'.agents').symlink_to(elsewhere)
        self.assertNotEqual(self.command('link', check=False).returncode, 0)
        self.assertEqual(original.read_text(), 'keep\n')
        self.assertEqual(list(elsewhere.iterdir()), [])
        (self.home/'.agents').unlink()
        target = self.home/'.agents/skills/find-skills'
        target.parent.mkdir(parents=True)
        target.symlink_to('old-missing-skill')
        self.apply()
        saved = next((self.home/'.local/state/dotfiles/skill-backups').glob('*/find-skills'))
        self.assertEqual(os.readlink(saved), 'old-missing-skill')
        self.assertEqual(target.resolve(), self.source/'skills/find-skills')

    def fixture_shell(self, command):
        # Keep Homebrew tools installed on the host out of missing-tool/mock checks.
        with (self.source/'home/.zprofile').open('a') as profile:
            profile.write('\npath=(${path:#/opt/homebrew/*})\n')
        return run(['zsh','-d','-f','-i','-c',command],capture_output=True,text=True)

    def test_live_edits_backups_reruns_and_symlink_launcher(self):
        original = self.home / '.zshrc'; original.write_text('original\n')
        self.apply()
        backups = list(self.home.glob('.zshrc.dotbot-backup.*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), 'original\n')
        self.assertTrue(original.is_symlink())
        original.write_text('# edited through home path\n')
        self.assertEqual((self.source / 'home/.zshrc').read_text(), original.read_text())
        (self.source / 'home/.zshrc').write_text('# edited through repo\n')
        self.assertEqual(original.read_text(), '# edited through repo\n')
        self.apply()
        self.assertEqual(list(self.home.glob('.zshrc.dotbot-backup.*')), backups)
        result=run([self.home / '.local/bin/dotfiles', 'help'],capture_output=True,text=True)
        self.assertIn('private-setup',result.stdout)

    def test_conflicting_broken_symlink_preserved(self):
        (self.home/'.zshrc').symlink_to('old-missing-file')
        self.apply()
        backups=list(self.home.glob('.zshrc.dotbot-backup.*'))
        self.assertEqual(len(backups),1)
        self.assertEqual(os.readlink(backups[0]),'old-missing-file')

    def test_parent_and_directory_conflicts_stop_before_replacements(self):
        original=self.home/'.zshrc';original.write_text('keep')
        elsewhere=self.base/'elsewhere';elsewhere.mkdir()
        (self.home/'.config').symlink_to(elsewhere)
        self.assertNotEqual(self.command('link',check=False).returncode,0)
        self.assertEqual(original.read_text(),'keep');self.assertEqual(list(elsewhere.iterdir()),[])
        (self.home/'.config').unlink();original.unlink();original.mkdir()
        self.assertNotEqual(self.command('link',check=False).returncode,0)
        self.assertTrue(original.is_dir())

    def test_dry_run_does_not_apply(self):
        self.command('diff')
        self.assertEqual(list(self.home.iterdir()),[])

    def test_interrupted_link_can_be_retried_with_backup_intact(self):
        (self.home/'.zshrc').symlink_to('missing-old-target')
        broken=self.tools/'broken-dotbot';atomic_write(broken,b'#!/bin/sh\nexit 1\n',0o755)
        saved=os.environ['DOTBOT_BIN'];os.environ['DOTBOT_BIN']=str(broken)
        self.assertNotEqual(self.command('link',check=False).returncode,0)
        os.environ['DOTBOT_BIN']=saved
        self.apply()
        self.assertEqual(os.readlink(next(self.home.glob('.zshrc.dotbot-backup.*'))),'missing-old-target')

    def test_linux_has_no_mac_tools_or_private_authentication(self):
        atomic_write(self.tools/'uname',b'#!/bin/sh\necho Linux\n',0o755)
        self.apply()
        self.assertFalse((self.home/'.config/mise/config.toml').exists())
        self.assertFalse((self.home/'.config/ghostty').exists())
        self.assertFalse((self.home/'.ssh').exists())
        self.assertNotEqual(self.command('private-setup', self.private(), '--identity','personal',check=False).returncode,0)
        self.assertNotEqual(self.command('brew-install',check=False).returncode,0)
        for key in ('user.email','commit.gpgsign'):
            self.assertEqual(subprocess.run(['git','config','--global','--get',key],capture_output=True).returncode,1)
        if shutil.which('zsh'):
            result=run(['zsh','-d','-f','-c','OSTYPE=linux-gnu; export SSH_AUTH_SOCK=/tmp/forwarded-agent.sock; source "$HOME/.zprofile"; print -r -- "$SSH_AUTH_SOCK"'],capture_output=True,text=True)
            self.assertEqual(result.stdout.strip(),'/tmp/forwarded-agent.sock')

    def test_public_ssh_default_private_override_and_backups(self):
        target=self.home/'.ssh/config'
        atomic_write(target,b'Host *\n    ServerAliveInterval 30\n',0o600)
        self.apply()
        self.assertEqual(target.resolve(),self.source/'macos/ssh/config')
        self.assertEqual(target.parent.stat().st_mode & 0o777,0o700)
        backups=list(target.parent.glob('config.dotbot-backup.*'))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_text(),'Host *\n    ServerAliveInterval 30\n')
        self.apply()
        self.assertEqual(list(target.parent.glob('config.dotbot-backup.*')),backups)
        # OpenSSH expands ~ using the account database, not the fixture's HOME.
        config=self.base/'ssh-eval.conf'
        config.write_text(target.read_text().replace('~/.ssh/config.private','"'+str(self.home/'.ssh/config.private')+'"'))
        def options(host):
            result=run(['ssh','-G','-F',config,host],capture_output=True,text=True)
            return dict(line.split(' ',1) for line in result.stdout.splitlines())
        self.assertIn('2BUA8C4S2C.com.1password/t/agent.sock',options('fixture')['identityagent'])
        private=self.private()
        with (private/'machines/personal/ssh/config').open('a') as output:
            output.write('Host fixture\n    IdentityAgent /tmp/custom-agent.sock\n')
        self.command('private-setup',private,'--identity','personal')
        self.assertEqual((self.home/'.ssh/config.private').resolve(),private/'machines/personal/ssh/config')
        self.assertEqual((self.home/'.ssh/config.private').stat().st_mode & 0o777,0o600)
        self.apply()
        self.assertEqual(options('fixture')['hostname'],'personal.example.test')
        self.assertEqual(options('fixture')['identityagent'],'/tmp/custom-agent.sock')
        self.assertIn('2BUA8C4S2C.com.1password/t/agent.sock',options('other.example.test')['identityagent'])
        config_source=private/'machines/personal/ssh/config'
        config_source.write_text(config_source.read_text().replace('/tmp/custom-agent.sock','/tmp/updated-agent.sock'))
        self.assertEqual(options('fixture')['identityagent'],'/tmp/updated-agent.sock')

    def test_container_rejects_mac_profile_before_any_install(self):
        result=subprocess.run([self.source/'install.sh','--container','--profile','work'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Mac-only',result.stderr)
        self.assertEqual(list(self.home.iterdir()),[])

    def test_shell_helpers_and_mise_precedence_over_herd(self):
        if not shutil.which('zsh'): self.skipTest('zsh unavailable')
        self.apply()
        herd=self.home/'Library/Application Support/Herd/bin'
        runtime=self.home/'fixture-mise-bin'
        for directory in (herd,runtime):
            atomic_write(directory/'node',b'#!/bin/sh\nexit 0\n',0o755)
        atomic_write(herd/'php',b'#!/bin/sh\nexit 0\n',0o755)
        for tool in ('bat','eza','rg','fd'):
            atomic_write(self.home/'.local/bin'/tool,b'#!/bin/sh\nexit 0\n',0o755)
        atomic_write(self.home/'.local/bin/mise',b'#!/bin/sh\necho \'export PATH="$HOME/fixture-mise-bin:$PATH"\'\n',0o755)
        result=self.fixture_shell('source "$HOME/.zshrc"; alias cat ls grep find; command -v node; command -v php || true')
        self.assertIn('bat --paging=never',result.stdout)
        self.assertIn(str(runtime/'node'),result.stdout)
        if os.uname().sysname=='Darwin': self.assertIn(str(herd/'php'),result.stdout)

    def test_shell_missing_optional_tools(self):
        if not shutil.which('zsh'):self.skipTest('zsh unavailable')
        self.apply()
        result=self.fixture_shell('source "$HOME/.zshrc"; print READY')
        self.assertIn('READY',result.stdout)
        self.assertEqual(result.stderr,'')


class PrivateTests(Isolated):
    def test_machine_aws_and_ssh_selection_backups_and_live_edits(self):
        self.apply();private=self.private()
        atomic_write(self.home/'.aws/config',b'# existing AWS config\n',0o600)
        atomic_write(self.home/'.aws/credentials',b'# local credentials fixture\n',0o600)
        atomic_write(self.home/'.aws/sso/cache/fixture.json',b'{"fixture":true}\n',0o600)
        atomic_write(private/'machines/personal/aws/credentials',b'# ignored fixture file\n',0o600)
        self.command('brew-profile','personal')
        self.command('private-setup',private,'--identity','personal')
        targets={'.aws/config':'aws/config','.ssh/config.private':'ssh/config','.ssh/hosts':'ssh/hosts',
                 '.config/atuin-machine/env.sh':'atuin/env.sh',
                 '.config/atuin-machine/ai-token-reference':'atuin/ai-token-reference'}
        for target,relative in targets.items():
            self.assertEqual((self.home/target).resolve(),private/'machines/personal'/relative)
        self.assertNotIn('[profile work]',(self.home/'.aws/config').read_text())
        self.assertNotIn('work.example.test',(self.home/'.ssh/hosts').read_text())
        self.assertEqual((self.home/'.ssh/allowed_signers').resolve(),private/'ssh/allowed_signers')
        self.command('brew-profile','work')
        self.command('diff','--private')
        self.assertEqual((self.home/'.aws/config').resolve(),private/'machines/personal/aws/config')
        self.command('link','--private')
        for target,relative in targets.items():
            self.assertEqual((self.home/target).resolve(),private/'machines/work'/relative)
        work=private/'machines/work/ssh/hosts'
        work.write_text(work.read_text().replace('work.example.test','updated.example.test'))
        self.assertIn('updated.example.test',(self.home/'.ssh/hosts').read_text())
        backups=sorted(self.home.rglob('*.dotbot-backup.*'))
        self.assertTrue(any(p.read_text()=='# existing AWS config\n' for p in (self.home/'.aws').glob('config.dotbot-backup.*')))
        self.command('link','--private')
        self.assertEqual(sorted(self.home.rglob('*.dotbot-backup.*')),backups)
        self.assertEqual((self.home/'.aws/credentials').read_text(),'# local credentials fixture\n')
        self.assertEqual((self.home/'.aws/sso/cache/fixture.json').read_text(),'{"fixture":true}\n')
        self.assertFalse((self.home/'.aws/machines').exists())
        self.assertFalse((self.home/'.ssh/machines').exists())

    def test_missing_or_invalid_machine_selection_stops_before_linking(self):
        self.apply();private=self.private()
        self.command('private-setup',private,'--identity','work')
        self.assertEqual((self.home/'.aws/config').resolve(),private/'machines/personal/aws/config')
        (private/'machines/work/aws/config').unlink()
        self.command('brew-profile','work')
        result=self.command('link','--private',check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Missing machine configuration',result.stderr)
        self.assertEqual((self.home/'.ssh/hosts').resolve(),private/'machines/personal/ssh/hosts')
        atomic_write(self.home/'.config/dotfiles/brew-profile',b'../work\n')
        result=self.command('link','--private',check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Select personal or work',result.stderr)
        self.assertEqual((self.home/'.aws/config').resolve(),private/'machines/personal/aws/config')

    def test_ssh_targets_cannot_overlap_in_either_direction(self):
        self.apply();private=self.private()
        atomic_write(self.source/'macos/ssh/hosts',b'Host collision\n')
        result=self.command('private-setup',private,'--identity','personal',check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('overlap',result.stderr)
        self.assertEqual((self.home/'.ssh/config').resolve(),self.source/'macos/ssh/config')
        (self.source/'macos/ssh/hosts').unlink()
        self.command('private-setup',private,'--identity','personal')
        atomic_write(self.source/'macos/ssh/config.private',b'Host collision\n')
        result=self.command('link',check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('overlap',result.stderr)
        self.assertEqual((self.home/'.ssh/config').resolve(),self.source/'macos/ssh/config')
        self.assertEqual((self.home/'.ssh/config.private').resolve(),private/'machines/personal/ssh/config')

    def test_installer_profile_supplies_private_defaults(self):
        self.apply();private=self.private()
        sibling=self.source.parent/'private';private.rename(sibling)
        for profile in ('personal','work'):
            with self.subTest(profile=profile):
                (self.home/'.config/dotfiles/git-identity').unlink(missing_ok=True)
                self.command('brew-profile',profile)
                self.command('private-setup')
                self.assertEqual((self.home/'.config/dotfiles/git-identity').read_text().strip(),profile)
                self.assertFalse((self.home/'.config/dotfiles/atuin-profile').exists())
                self.assertEqual((self.home/'.config/atuin-machine/env.sh').resolve(),sibling/'machines'/profile/'atuin/env.sh')
                self.assertEqual(run(['git','config','--global','--includes','user.email'],capture_output=True,text=True).stdout.strip(),profile+'@example.test')
                self.assertEqual((self.home/'.aws/config').resolve(),sibling/'machines'/profile/'aws/config')
                self.assertEqual((self.home/'.ssh/hosts').resolve(),sibling/'machines'/profile/'ssh/hosts')

    def test_private_overrides_take_precedence_and_survive_reruns(self):
        self.apply();private=self.private()
        self.command('brew-profile','work')
        self.command('private-setup',private,'--identity','personal')
        self.command('private-setup',private)
        self.assertEqual((self.home/'.config/dotfiles/git-identity').read_text().strip(),'personal')
        self.assertEqual((self.home/'.config/atuin-machine/env.sh').resolve(),private/'machines/work/atuin/env.sh')
        self.command('private-setup',private,'--identity','work')
        self.assertEqual((self.home/'.config/dotfiles/git-identity').read_text().strip(),'work')
        self.assertEqual((self.home/'.config/atuin-machine/env.sh').resolve(),private/'machines/work/atuin/env.sh')

    def test_installer_defaults_require_matching_private_configs(self):
        self.apply();private=self.private()
        self.command('brew-profile','work')
        (private/'config/git/identities/work').unlink()
        self.assertNotEqual(self.command('private-setup',private,check=False).returncode,0)
        self.command('private-setup',private,'--identity','personal')
        self.assertEqual((self.home/'.config/atuin-machine/env.sh').resolve(),private/'machines/work/atuin/env.sh')

    def test_identity_default_overrides_and_signing_live(self):
        self.apply();private=self.private()
        sibling=self.source.parent/'private';private.rename(sibling);private=sibling
        self.command('private-setup','--identity','personal')
        self.command('private-setup')
        self.assertEqual((self.home/'.config/dotfiles/private-source').read_text().strip(),str(private))
        for relative,identity in [('unmatched','personal'),('Code/work/project','work'),('Code/work/client/project','client')]:
            path=self.home/relative;path.mkdir(parents=True)
            run(['git','init','-q',path],capture_output=True)
            for key,value in [('user.email',identity+'@example.test'),('commit.gpgsign','true')]:
                self.assertEqual(run(['git','-C',path,'config',key],capture_output=True,text=True).stdout.strip(),value)
        self.command('git-identity','work')
        self.assertEqual(run(['git','-C',self.home/'unmatched','config','user.email'],capture_output=True,text=True).stdout.strip(),'work@example.test')
        identity=private/'config/git/identities/work';identity.write_text(identity.read_text().replace('work@example.test','updated@example.test'))
        self.assertEqual(run(['git','-C',self.home/'unmatched','config','user.email'],capture_output=True,text=True).stdout.strip(),'updated@example.test')
        self.assertEqual((self.home/'.ssh/hosts').stat().st_mode & 0o777,0o600)

    def test_private_collision_rejected_before_public_changes(self):
        self.apply();private=self.private()
        atomic_write(private/'config/starship.toml',b'bad')
        result=self.command('private-setup',private,'--identity','personal',check=False)
        self.assertNotEqual(result.returncode,0);self.assertIn('overlap',result.stderr)
        self.assertEqual((self.home/'.config/starship.toml').resolve(),self.source/'config/starship.toml')
        self.assertFalse((self.home/'.ssh/hosts').exists())
        self.assertEqual((self.home/'.ssh/config').resolve(), self.source/'macos/ssh/config')

    def test_public_cannot_take_over_private_target(self):
        self.apply(); private=self.private()
        self.command('private-setup',private,'--identity','personal')
        atomic_write(self.source/'config/git/private',b'overlap')
        result=self.command('link',check=False)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('overlap',result.stderr)
        self.assertEqual((self.home/'.config/git/private').resolve(),private/'config/git/private')

    def test_missing_private_and_unknown_identity_do_not_change_home(self):
        self.assertNotEqual(self.command('link','--private',check=False).returncode,0)
        missing=self.command('private-setup',check=False)
        self.assertNotEqual(missing.returncode,0)
        self.assertIn('Private checkout not found',missing.stderr)
        self.assertNotEqual(self.command('private-setup',self.private(),'--identity','unknown',check=False).returncode,0)
        self.assertEqual(list(self.home.iterdir()),[])

    def test_relocation_preserves_choices_and_relinks(self):
        self.apply();private=self.private()
        self.command('private-setup',private,'--identity','work')
        self.command('brew-profile','personal')
        parent=self.home/'dev/dotfiles';parent.mkdir(parents=True)
        moved=parent/'public';self.source.rename(moved);self.source=moved
        moved_private=parent/'private';private.rename(moved_private)
        self.command('private-setup')
        self.apply()
        self.assertEqual((self.home/'.zshrc').resolve(),moved/'home/.zshrc')
        self.assertEqual((self.home/'.config/git/default-identity').resolve(),moved_private/'config/git/identities/work')
        self.assertEqual((self.home/'.config/atuin-machine/env.sh').resolve(),moved_private/'machines/personal/atuin/env.sh')
        self.assertEqual((self.home/'.config/dotfiles/brew-profile').read_text().strip(),'personal')
        self.assertEqual((self.home/'.aws/config').resolve(),moved_private/'machines/personal/aws/config')
        self.assertEqual((self.home/'.ssh/config.private').resolve(),moved_private/'machines/personal/ssh/config')

    def test_atuin_follows_machine_and_token_only_on_explicit_ai(self):
        self.apply();private=self.private()
        self.command('brew-profile','work')
        atomic_write(self.home/'.config/dotfiles/atuin-profile',b'personal\n')
        self.command('private-setup',private,'--identity','personal')
        (private/'machines/work/atuin/ai-token-reference').write_text('op://Work/Atuin/token\n')
        atomic_write(self.tools/'op',b'#!/bin/sh\necho called >> "$HOME/op-log"\necho fixture-token\n',0o755)
        atomic_write(self.tools/'atuin',b'#!/bin/sh\nprintf "%s|%s" "$ATUIN_CONFIG_DIR" "${ATUIN_AI__API_TOKEN:-unset}"\n',0o755)
        self.command('link','--private')
        self.assertFalse((self.home/'op-log').exists())
        result=self.command('atuin-ai')
        self.assertIn('/atuin|fixture-token',result.stdout)
        self.command('brew-profile','personal')
        self.command('link','--private')
        self.assertIn('/atuin|unset',self.command('atuin-ai').stdout)
        self.assertEqual((self.home/'op-log').read_text(),'called\n')
        self.assertNotEqual(self.command('atuin-profile','work',check=False).returncode,0)
        self.assertNotEqual(self.command('private-setup',private,'--atuin-profile','work',check=False).returncode,0)
        for path in private.rglob('*'):
            if path.is_file():self.assertNotIn('fixture-token',path.read_text())

    def test_atuin_machine_shell_selection_and_target_separation(self):
        self.apply();private=self.private()
        def directory(platform):
            return run(['zsh','-d','-f','-c','OSTYPE='+platform+'; source "$HOME/.zprofile"; print -r -- "$ATUIN_CONFIG_DIR|${ATUIN_AI__ENDPOINT:-default}"'],capture_output=True,text=True).stdout.strip()
        self.assertEqual(directory('darwin'),str(self.home/'.config/atuin')+'|default')
        self.command('private-setup',private,'--identity','personal')
        self.assertEqual(directory('darwin'),str(self.home/'.config/atuin')+'|http://127.0.0.1:1/personal')
        self.assertEqual(directory('linux-gnu'),str(self.home/'.config/atuin')+'|default')
        atomic_write(self.source/'config/atuin-machine/env.sh',b'# collision\n')
        for args in (('link',),('link','--private')):
            result=self.command(*args,check=False)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('overlap',result.stderr)


class BrewTests(Isolated):
    def test_only_shared_and_selected_profile_no_upgrades(self):
        atomic_write(self.tools/'brew',b'#!/bin/sh\nprintf "%s\\n" "$@" >> "$HOME/brew-log"\n',0o755)
        self.command('brew-install','--profile','work')
        text=(self.home/'brew-log').read_text()
        self.assertIn(str(self.source/'Brewfile')+'\n',text)
        self.assertIn(str(self.source/'Brewfile.work'),text)
        self.assertNotIn('Brewfile.personal',text)
        self.assertEqual(text.count('--no-upgrade'),2)
        self.assertNotIn('cleanup',text)

    def test_failed_install_retains_choice(self):
        atomic_write(self.tools/'brew',b'#!/bin/sh\nexit 1\n',0o755)
        self.assertNotEqual(self.command('brew-install','--profile','personal',check=False).returncode,0)
        self.assertEqual((self.home/'.config/dotfiles/brew-profile').read_text(),'personal\n')
        self.assertEqual(self.command('brew-profile').stdout.strip(),'personal')

    def test_unattended_selection_is_required(self):
        self.assertNotEqual(self.command('brew-install',check=False).returncode,0)
        self.assertEqual(list(self.home.iterdir()),[])


class UpdateTests(Isolated):
    def git(self,*args):
        return run(['git',*args],capture_output=True,text=True,env=dict(os.environ,GIT_AUTHOR_NAME='Fixture',GIT_AUTHOR_EMAIL='fixture@example.test',GIT_COMMITTER_NAME='Fixture',GIT_COMMITTER_EMAIL='fixture@example.test'))

    def setup_remote(self):
        remote=self.base/'remote.git';self.git('init','--bare',remote)
        self.git('-C',self.source,'init','-b','main');self.git('-C',self.source,'add','.')
        self.git('-C',self.source,'commit','-m','initial')
        self.git('-C',self.source,'remote','add','origin',remote);self.git('-C',self.source,'push','-u','origin','main')
        peer=self.base/'peer';self.git('clone','-b','main',remote,peer)
        return peer

    def test_fast_forward_configuration_only_and_dirty_diverged_refusals(self):
        peer=self.setup_remote();self.apply()
        for tool in ('brew','mise','curl'):
            atomic_write(self.tools/tool,b'#!/bin/sh\necho Unexpected software operation >&2\nexit 90\n',0o755)
        (peer/'home/.zshrc').write_text('# changed upstream\n')
        self.git('-C',peer,'add','.');self.git('-C',peer,'commit','-m','update');self.git('-C',peer,'push')
        self.command('update')
        self.assertEqual((self.home/'.zshrc').read_text(),'# changed upstream\n')
        (self.source/'dirty').write_text('dirty')
        self.assertIn('Commit or stash',self.command('update',check=False).stderr)
        self.git('-C',self.source,'add','.');self.git('-C',self.source,'commit','-m','local')
        (peer/'remote-only').write_text('remote');self.git('-C',peer,'add','.');self.git('-C',peer,'commit','-m','remote');self.git('-C',peer,'push')
        self.assertIn('Diverged',self.command('update',check=False).stderr)
