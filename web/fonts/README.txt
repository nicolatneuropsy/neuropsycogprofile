Bundled fonts
=============

This folder is reserved for locally bundled fonts so that the user
interface never needs to reach the network for a webfont.

Default behaviour
-----------------
Out of the box the interface uses a local "system font stack" (the
fonts already installed on the operating system: San Francisco on
macOS, Segoe UI on Windows, and so on). Nothing is downloaded at any
time, which fully satisfies the offline / no-network requirement.

This was chosen as the simplest sensible default because a font binary
cannot be fetched without network access at build time. See the README
for the note on this decision.

Bundling your own font (optional)
---------------------------------
If you want a single consistent typeface on every machine:

1. Drop a .woff2 (or .ttf) file in this folder, for example
   "Inter.woff2".
2. At the very top of ../styles.css add an @font-face rule pointing at
   the local file, for example:

       @font-face {
         font-family: "App UI";
         src: url("fonts/Inter.woff2") format("woff2");
         font-weight: 100 900;
         font-display: swap;
       }

3. Put "App UI" first in the --font-sans variable in styles.css.

The matplotlib figures use matplotlib's own bundled font (DejaVu Sans),
which is installed with the matplotlib package and is fully local.
