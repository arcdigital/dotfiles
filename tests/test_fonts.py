import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import zipfile
from unittest.mock import patch
from types import SimpleNamespace
from fonts import font_metadata, patch as patch_fonts, import_zip, validate_fonts, install
from font_patcher_names import preserve_names
from support import Isolated, fake_font, atomic_write, ROOT

class FontTests(Isolated):
    def test_metadata(self):
        self.assertEqual(font_metadata(fake_font()), {"family": "Test Mono", "style": "Regular"})
        with self.assertRaises(ValueError):
            font_metadata(b"not a font")

    def test_missing_inputs_and_docker_fail_clearly(self):
        source = self.base / "originals"
        source.mkdir()
        with self.assertRaisesRegex(ValueError, "No .otf"):
            patch_fonts(source, self.base / "patched")
        (source / "Regular.ttf").write_bytes(fake_font())
        with patch("fonts.shutil.which", return_value=None):
            with self.assertRaisesRegex(ValueError, "Docker Desktop"):
                patch_fonts(source, self.base / "patched")

    def test_validated_pipeline_and_checksum_failure(self):
        source, dest = self.base / "originals", self.base / "patched"
        source.mkdir()
        for style in ("Regular", "Bold", "Italic", "Bold Italic"):
            (source / (style + ".ttf")).write_bytes(fake_font(style=style, version="3.000"))
        calls = []
        def docker(args, **kwargs):
            calls.append(args)
            if args[1:3] == ["image", "inspect"]:
                return subprocess.CompletedProcess(args, 0, stdout="nerdfonts/patcher@sha256:" + "a" * 64)
            if "-v" in args:
                path = next(a[:-5] for a in args if isinstance(a, str) and a.endswith(":/out"))
                for style in ("Regular", "Bold", "Italic", "Bold Italic"):
                    (Path(path) / (style + ".ttf")).write_bytes(fake_font("Test Mono Nerd", style))
            return subprocess.CompletedProcess(args, 0, stdout="fixture patcher\n")
        with patch("fonts.shutil.which", return_value="docker"), patch("fonts.run", side_effect=docker):
            patch_fonts(source, dest, jobs=2)
        manifest = validate_fonts(dest)
        self.assertEqual(manifest["family"], "Test Mono Nerd")
        self.assertEqual(manifest["font_version"], "3.000")
        self.assertEqual(manifest["image_requested"], "nerdfonts/patcher:latest")
        self.assertEqual(manifest["image"], "nerdfonts/patcher@sha256:" + "a" * 64)
        self.assertEqual(len(manifest["outputs"]), 4)
        self.assertEqual(manifest["jobs"], 2)
        self.assertIn("PN=2", calls[-1])
        self.assertEqual(manifest["naming_adapter_sha256"], hashlib.sha256((ROOT / "scripts/font_patcher_names.py").read_bytes()).hexdigest())
        self.assertIn("--network=none", calls[-1])
        writable = Path(next(a[:-4] for a in calls[-1] if a.endswith(":/in")))
        self.assertNotEqual(writable, source)
        self.assertTrue(any(a.endswith(":/font_patcher_names.py:ro") for a in calls[-1]))
        self.assertEqual((source / "Regular.ttf").read_bytes(), fake_font(style="Regular", version="3.000"))
        (dest / "Regular.ttf").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            validate_fonts(dest)

    def test_missing_output_never_publishes(self):
        source, dest = self.base / "originals", self.base / "patched"
        source.mkdir()
        (source / "Regular.ttf").write_bytes(fake_font())
        def docker(args, **kwargs):
            text = "nerdfonts/patcher@sha256:" + "a" * 64 if args[1:3] == ["image", "inspect"] else "version"
            return subprocess.CompletedProcess(args, 0, stdout=text)
        with patch("fonts.shutil.which", return_value="docker"), patch("fonts.run", side_effect=docker):
            with self.assertRaisesRegex(ValueError, "every input"):
                patch_fonts(source, dest)
        self.assertFalse(dest.exists())
        self.assertEqual(len(list(self.base.glob(".patch-font-*"))), 1)

    def test_jobs_validation_precedes_docker(self):
        with patch("fonts.run") as docker:
            for jobs in (0, -1, True, "4"):
                with self.assertRaisesRegex(ValueError, "positive integer"):
                    patch_fonts(self.base / "source", self.base / "dest", jobs=jobs)
        docker.assert_not_called()

    def test_failed_docker_retains_partial_outputs_without_publishing(self):
        source, dest = self.base / "originals", self.base / "patched"
        source.mkdir()
        (source / "Regular.ttf").write_bytes(fake_font())
        def docker(args, **kwargs):
            if "-v" in args:
                self.assertIn("PN=1", args)
                path = Path(next(a[:-5] for a in args if a.endswith(":/out")))
                (path / "Regular.ttf").write_bytes(fake_font("Test Mono Nerd"))
                raise subprocess.CalledProcessError(1, args)
            value = "nerdfonts/patcher@sha256:" + "a" * 64 if args[1:3] == ["image", "inspect"] else "version"
            return subprocess.CompletedProcess(args, 0, stdout=value)
        with patch("fonts.shutil.which", return_value="docker"), patch("fonts.run", side_effect=docker):
            with self.assertRaises(subprocess.CalledProcessError):
                patch_fonts(source, dest)
        self.assertFalse(dest.exists())
        self.assertEqual(len(list(self.base.glob(".patch-font-*/out/Regular.ttf"))), 1)

    def test_explicit_names_preserve_hairline_weights_and_italics(self):
        for style, legacy_family, legacy_style in (
            ("Hairline", "Test Mono Hairline", "Regular"),
            ("ExtraBold", "Test Mono ExtraBold", "Regular"),
            ("Regular Italic", "Test Mono", "Italic"),
            ("Bold", "Test Mono", "Bold"),
        ):
            with self.subTest(style=style):
                names = {"Family": legacy_family, "SubFamily": legacy_style,
                         "Preferred Family": "Test Mono", "Preferred Styles": style,
                         "PostScriptName": "TestMono-" + style.replace(" ", ""),
                         "Version": "Version 3.000;Nerd Fonts 3.5.1", "License": "licensed"}
                font = SimpleNamespace(sfnt_names=tuple(("English (US)", k, v) for k, v in names.items())
                                       + (("French", "Family", "Original name"),))
                font.appendSFNTName = lambda language, key, value: setattr(font, "sfnt_names", font.sfnt_names + ((language, key, value),))
                preserve_names(font)
                output = {key: value for _, key, value in font.sfnt_names}
                self.assertEqual(output["Preferred Family"], "Test Mono Nerd Font Mono")
                self.assertEqual(output["Preferred Styles"], style)
                self.assertEqual(output["SubFamily"], legacy_style)
                self.assertEqual(output["License"], "licensed")
                self.assertEqual(output["Version"], names["Version"])
                self.assertEqual(output["PostScriptName"], names["PostScriptName"] + "NerdFontMono")
                self.assertNotIn(("French", "Family", "Original name"), font.sfnt_names)


def variable_font(family="Test Variable", style="Regular"):
    names = fake_font(family, style)[28:]
    return (struct.pack(">IHHHH", 0x10000, 2, 32, 1, 0)
            + struct.pack(">4sIII", b"name", 0, 44, len(names))
            + struct.pack(">4sIII", b"fvar", 0, 44 + len(names), 4)
            + names + b"test")


class FontCollectionTests(Isolated):
    def test_import_records_embedded_release_and_rejects_mixed_releases(self):
        archive = self.base / "release.zip"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("Regular.ttf", fake_font(version="3.000"))
        destination = self.base / "imported"
        import_zip(archive, destination)
        manifest = validate_fonts(destination)
        self.assertEqual(manifest["font_version"], "3.000")
        manifest["font_version"] = "3.001"
        (destination / "manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "release"):
            validate_fonts(destination)
        with zipfile.ZipFile(archive, "a") as output:
            output.writestr("Bold.ttf", fake_font(style="Bold", version="3.001"))
        with self.assertRaisesRegex(ValueError, "mix font releases"):
            import_zip(archive, self.base / "mixed")
        self.assertFalse((self.base / "mixed").exists())

    def collection(self, directory, name, variable=False):
        archive = self.base / (name + ".zip")
        make = variable_font if variable else fake_font
        with zipfile.ZipFile(archive, "w") as output:
            for style in ("Regular", "Italic"):
                output.writestr("download/" + name + style + ".ttf", make(name, style))
            output.writestr("../../ignored.txt", "ignored")
        import_zip(archive, directory / name)
        return archive

    @patch("fonts.register_fonts")
    def test_unchanged_zip_import_and_multiple_collections(self, register):
        directory = self.base / "private/fonts"
        original = self.collection(directory, "code-variable", True)
        self.collection(directory, "code-static")
        self.collection(directory, "text-variable", True)
        self.collection(directory, "text-static")
        manifest = {"default": "code-variable", "collections": [{"id": n} for n in
                    ("code-variable", "code-static", "text-variable", "text-static")]
                    + [{"id": "code-static-patched", "optional": True}]}
        (directory / "manifest.json").write_text(json.dumps(manifest))
        with zipfile.ZipFile(original) as archive:
            data = archive.read("download/code-variableRegular.ttf")
        self.assertEqual((directory / "code-variable/code-variableRegular.ttf").read_bytes(), data)
        result = validate_fonts(directory)
        self.assertEqual((result["family"], result["kind"]), ("code-variable", "variable"))
        self.assertEqual(result["pending"], ["code-static-patched"])
        self.assertEqual(len(result["outputs"]), 8)
        existing = self.home / "Library/Fonts/code-variableRegular.ttf"
        atomic_write(existing, b"old font")
        install(directory)
        backups = list(existing.parent.glob(existing.name + ".dotbot-backup.*"))
        self.assertEqual(backups[0].read_bytes(), b"old font")
        install(directory)
        self.assertEqual(list(existing.parent.glob(existing.name + ".dotbot-backup.*")), backups)
        self.assertEqual(len(list((self.home / "Library/Fonts").glob("*.ttf"))), 8)
        self.assertEqual(register.call_count, 2)
        self.assertEqual(set(register.call_args.args[0]), set(existing.parent.glob("*.ttf")))

    def test_missing_default_and_duplicate_collection_rejected(self):
        directory = self.base / "fonts"
        self.collection(directory, "static")
        manifest = {"default": "missing", "collections": [{"id": "static"}]}
        path = directory / "manifest.json"
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "Default"):
            validate_fonts(directory)
        manifest["default"] = "static"
        manifest["collections"] += [{"id": "pending", "optional": True}] * 2
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "duplicated"):
            validate_fonts(directory)

    def test_colliding_collections_rejected(self):
        directory = self.base / "fonts"
        self.collection(directory, "static")
        shutil.copytree(directory / "static", directory / "other")
        (directory / "manifest.json").write_text(json.dumps({"default": "static", "collections": [{"id": "static"}, {"id": "other"}]}))
        with self.assertRaisesRegex(ValueError, "collide"):
            validate_fonts(directory)

    def test_variable_patching_rejected_before_docker(self):
        source = self.base / "variable"
        source.mkdir()
        (source / "Variable.ttf").write_bytes(variable_font())
        with patch("fonts.run") as docker:
            with self.assertRaisesRegex(ValueError, "Variable fonts"):
                patch_fonts(source, self.base / "patched")
        docker.assert_not_called()

    def test_zip_rejects_duplicate_files_and_public_output(self):
        archive = self.base / "input.zip"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("a/Regular.ttf", fake_font())
            output.writestr("b/Regular.ttf", fake_font())
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            import_zip(archive, self.base / "dest")
        with self.assertRaisesRegex(ValueError, "outside"):
            import_zip(archive, ROOT / "fonts")
