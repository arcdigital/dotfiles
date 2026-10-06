import os
import subprocess

from support import run, Isolated


class GitPruneTests(Isolated):
    def setUp(self):
        super().setUp()
        self.apply()
        self.repo = self.home / "repository"
        self.repo.mkdir()
        self.git("init", "--initial-branch=main")
        self.commit("base.txt", "base\n", "initial")
        self.git("checkout", "-b", "merged")
        self.commit("merged.txt", "merged\n", "regular change")
        self.git("checkout", "main")
        self.git("merge", "--ff-only", "merged")
        self.git("checkout", "-b", "squashed")
        self.commit("squashed.txt", "first\n", "first change")
        self.commit("squashed.txt", "first\nsecond\n", "second change")
        self.git("checkout", "main")
        self.commit("main-only.txt", "main\n", "main moves forward")
        self.git("merge", "--squash", "squashed")
        self.git("commit", "-m", "squash feature")
        self.git("checkout", "-b", "unmerged")
        self.commit("unmerged.txt", "keep\n", "unfinished change")

    def git(self, *args):
        env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_AUTHOR_EMAIL="fixture@example.test",
                   GIT_COMMITTER_NAME="Fixture", GIT_COMMITTER_EMAIL="fixture@example.test")
        return run(["git", "-C", self.repo, *args], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()

    def commit(self, filename, contents, message):
        (self.repo / filename).write_text(contents)
        self.git("add", filename)
        self.git("commit", "-m", message)

    def refs(self):
        return self.git("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/")

    def test_check_lists_both_merge_types_without_deleting_refs(self):
        before = self.refs()
        result = self.git("prune-check")
        self.assertIn("merged is merged into main and can be deleted", result)
        self.assertIn("squashed is squash-merged into main and can be deleted", result)
        self.assertNotIn("unmerged", result)
        self.assertEqual(self.refs(), before)
        self.assertEqual(self.git("branch", "--show-current"), "main")

    def test_all_deletes_both_merge_types_preserves_unmerged_and_needs_no_signer(self):
        self.git("config", "commit.gpgsign", "true")
        self.git("config", "gpg.program", str(self.home / "nonexistent-signer"))
        self.git("prune-all")
        remaining = self.git("for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines()
        self.assertEqual(remaining, ["main", "unmerged"])
        self.assertEqual(self.git("branch", "--show-current"), "main")
        self.assertEqual(self.git("prune-all"), "")  # An empty cleanup is successful.

    def test_explicit_target_is_used_in_comparison_and_messages(self):
        self.git("branch", "-m", "main", "develop")
        result = self.git("prune-check", "develop")
        self.assertIn("into develop", result)
        self.assertNotIn("into main", result)
        self.git("prune-all", "develop")
        self.assertEqual(self.git("for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines(), ["develop", "unmerged"])

    def test_failed_checkout_preserves_branches_and_working_tree(self):
        before = self.refs()
        with self.assertRaises(subprocess.CalledProcessError):
            self.git("prune-all", "missing-target")
        (self.repo / "unmerged.txt").write_text("uncommitted edit\n")
        with self.assertRaises(subprocess.CalledProcessError):
            self.git("prune-all")
        self.assertEqual(self.refs(), before)
        self.assertEqual(self.git("branch", "--show-current"), "unmerged")
        self.assertEqual((self.repo / "unmerged.txt").read_text(), "uncommitted edit\n")
