# MonoLisa fonts

Licensed font binaries and manifests live in the private repo. The original Code/Text collection contains 44 font files with embedded version **3.000**. Each collection manifest records `font_version`, family/style metadata, and SHA-256 checksums. The importer detects versions automatically; the patcher records the source release separately from its own version.

## Collections

| Private directory | Family | Role |
| --- | --- | --- |
| `fonts/code-variable` | `MonoLisaCode Variable` | Original variable Code; Ghostty default |
| `fonts/code-static` | `MonoLisaCode` | Original fixed-weight Code |
| `fonts/code-static-patched` | Defined by its manifest | Optional Code with Nerd Font symbols |
| `fonts/text-variable` | `MonoLisaText Variable` | Original variable Text |
| `fonts/text-static` | `MonoLisaText` | Original fixed-weight Text |

`fonts/manifest.json` lists all collections and marks static-patched as optional. `dotfiles fonts-install` installs available collections together into `~/Library/Fonts` and registers them persistently with macOS CoreText for the current user. Reruns register unchanged files too. Distinct family names let the originals and patched Code coexist. Text remains unpatched. Public `macos/config/ghostty/config` selects the application's default font; private `config/ghostty/private.conf` accepts optional additions.

Ghostty uses original variable Code at weights 400/700 and its bundled Nerd Font symbol fallback. If MonoLisa is unavailable, Ghostty falls back to bundled JetBrains Mono. The font preference is public; licensed font files remain private. Homebrew also supplies Symbols Nerd Font Mono for applications that need a separate symbol font.

VS Code Settings Sync owns editor and terminal font choices. The editor can use `MonoLisaCode Variable`; a terminal font stack can use `'MonoLisaCode Variable', 'Symbols Nerd Font Mono'`. Apps that require symbols in their primary font use the patched family. Font changes typically require an application reload or restart.

## Original font imports and updates

```sh
./bin/patch-font --import-zip \
  --input /path/to/MonoLisaCode-Variable.zip \
  --output ~/dev/dotfiles/private/fonts/code-variable
```

Use a separate empty output directory for each archive. The importer copies only font files, preserving their bytes, and validates a single family/format with distinct styles. It detects embedded releases and rejects mixed versions. ZIP paths do not control output paths. Download archives stay outside the repositories.

For a font update, import each archive into an empty staging directory, inspect its manifest, and replace the corresponding private collection. Regenerate static-patched from the matching static originals. `dotfiles fonts-install` validates the available manifests and copies the fonts; conflicting installed files receive adjacent timestamped backups. Renamed or unrelated fonts remain available for deliberate removal.

## Static patching

```sh
./bin/patch-font \
  --input ~/dev/dotfiles/private/fonts/code-static \
  --output ~/dev/dotfiles/private/fonts/code-static-patched
```

Patching uses four parallel jobs and displays a progress bar in an interactive terminal. Use `--jobs 2` for a lower CPU load or `--jobs 8` for more concurrency. The 20 static faces include every supplied weight and italic variant.

Docker runs the official **`nerdfonts/patcher`** image. This is the same underlying patcher used by [MonoLisa's monolisa-nerdfonts project](https://github.com/MonoLisaFont/monolisa-nerdfonts). A small naming adapter preserves the original explicit family/style metadata and adds the `Nerd Font Mono` suffix, keeping Hairline and the other weights together. The official engine handles glyph insertion and font generation. `scripts/font-patcher.json` selects `nerdfonts/patcher:latest`. Each generation pulls the image and uses its resolved digest throughout the build. The manifest records that digest, the requested tag, patcher version, flags, naming-adapter checksum, job count, font checksums, family, and source font version.

The flags are `--complete --careful --single-width-glyphs`. Occupied glyph slots remain intact, symbols use single-width glyphs, and the command requests no ligature removal or line-height changes. Static input only is accepted; FontForge's patching path is unsuitable for preserving variable fonts reliably.

Input and output directories are separate and non-nested. Output is empty. Docker sees writable temporary copies of the selected inputs because the official patcher's metrics pass opens input files in read/write mode. The originals are never mounted. Docker uses a temporary output directory and runs without networking. Validation requires matching face counts/styles, a distinct patched family, and static output before publishing files into the output directory.

On failure, the printed working directory retains copied inputs, generated faces, and `out/jobs.tsv` for diagnosis. A fresh invocation uses an empty destination and a new working directory. Successful runs remove their working directory. The final collection is suitable for `dotfiles fonts-install` after validation; incomplete working files are not an installable collection.

## Application checks

`ghostty +list-fonts` reports available families. Rendering checks cover regular/bold/italic text, ligatures, symbol fallback, glyph spacing, and prompt/eza icons in the application's chosen family. Font validation checks metadata and checksums; visual rendering depends on the application.

## Fonts missing from applications

CoreText registration alone does not confirm that Font Book or an already-running editor displays a font. If installed fonts exist in `~/Library/Fonts` but remain absent from Font Book, quit Font Book and refresh the current user's font service:

```sh
killall -u "$(id -un)" fontd
open -a 'Font Book'
```

macOS restarts the service and scans the font directories. This preserves font files and settings. Quit and reopen VS Code or other affected applications after the refresh.
