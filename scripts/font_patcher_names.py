#!/usr/bin/env python3
"""Run the official Nerd Fonts engine with the source font's explicit styles."""
import importlib.machinery
import importlib.util
import sys


def preserve_names(font, single=True):
    names = {key: value for language, key, value in font.sfnt_names if language == "English (US)"}
    family = names.get("Preferred Family", names["Family"])
    style = names.get("Preferred Styles", names["SubFamily"])
    suffix = " Nerd Font Mono" if single else " Nerd Font"
    postscript = names["PostScriptName"] + suffix.replace(" ", "")
    if len(postscript) > 63:
        raise ValueError("Patched PostScript name exceeds 63 characters: " + postscript)
    replacements = {
        "Family": names["Family"] + suffix,
        "SubFamily": names["SubFamily"],
        "UniqueID": postscript + ";" + names.get("Version", ""),
        "Fullname": family + suffix + " " + style,
        "PostScriptName": postscript,
        "Preferred Family": family + suffix,
        "Preferred Styles": style,
    }
    font.familyname = replacements["Family"]
    font.fullname = replacements["Fullname"]
    font.fontname = postscript
    # Remove localized copies of naming fields so no original-family alias remains.
    obsolete = set(replacements) | {"Compatible Full", "WWS Family", "WWS Subfamily"}
    font.sfnt_names = tuple(record for record in font.sfnt_names if record[1] not in obsolete)
    for key, value in replacements.items():
        font.appendSFNTName("English (US)", key, value)


def main():
    # Keep the engine, glyph assets, metrics corrections and version from the image.
    sys.argv[0] = "/nerd/font-patcher"
    loader = importlib.machinery.SourceFileLoader("nerd_patcher", sys.argv[0])
    spec = importlib.util.spec_from_loader(loader.name, loader)
    engine = importlib.util.module_from_spec(spec)
    loader.exec_module(engine)
    engine.__dir__ = "/nerd"

    class NamedPatcher(engine.font_patcher):
        def setup_font_names(self, font):
            preserve_names(font, self.args.single)
            credit = "Patched with Nerd Fonts " + engine.version + " (https://github.com/ryanoasis/nerd-fonts)"
            font.comment = (font.comment or "") + "\n" + credit
            font.fontlog = (font.fontlog or "") + "\n" + credit

    engine.font_patcher = NamedPatcher
    engine.main()


if __name__ == "__main__":
    main()
