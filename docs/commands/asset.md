# asset

Files on the current ref: images, PDF, audio and video (`coho-data` doc 40). An asset
is a node like an entry, so it branches, merges and promotes with the content that uses
it. Its bytes, addressed by their SHA-256, do not branch at all, so a branch with
gigabytes of media costs nothing.

⚠️ **Asset URLs are public to anyone holding them**, in every project:

- an asset only a draft branch uses is as private as its URL, and a leaked URL cannot be
  revoked;
- deleting an asset does not stop its URL working, because history and released tags
  still point at the bytes;
- someone who already has a file can tell whether a project holds it, since the URL is
  the file's hash.

The URL cannot be guessed. Upload nothing that must stay private.

Every command but `upload` takes an asset's id or its slug.

## `coho asset upload FILE… [--slug SLUG] [--title T] [--alt A] [--focal X,Y] [--tag T]…`

`POST …/refs/{ref}/assets/uploads`, a `PUT` of the bytes to the presigned URL it
returns, then `POST …/assets/uploads/{id}/complete`. The bytes go straight to object
storage, never through the API, and are not sent at all when the project already holds
them.

The slug comes from the filename without its extension, in kebab-case
(`Hero Shot.jpg` → `hero-shot`); `--slug` sets it for a single file. Slugs share the
branch's namespace with entries, so a clash is `SLUG_CONFLICT`. `--focal` is where crops
centre, as fractions of the width and height (`0.5,0.3`). What a file is comes from its
bytes, not its name: anything but an image, PDF, audio or video is
`ASSET_TYPE_NOT_ALLOWED`. The limit is 1 GiB per file.

With `-o json`, one file prints its asset; several print `{"assets": […]}`.

## `coho asset list [--limit N] [--offset N] [--all]`

In slug order, with type, size and pixel dimensions.

## `coho asset get ASSET`

Everything about one asset, including its `url` and, for raster images, its
`image url`, and the ETag `put` sends.

## `coho asset url ASSET [--width W] [--height H] [--fit FIT] [--format FMT] [--quality Q]`

The original's URL, or with any option the image URL that resizes on request:
`--fit` is `scale` (the default), `pad`, `fill`, `crop` or `thumb`, and `--format` is
`auto`, `avif`, `webp`, `jpg` or `png`. A `fill`, `crop` or `thumb` centres on the
asset's focal point. The edge rounds sizes up to its fixed steps, so `--width 799`
serves 828. SVG, PDF, audio and video are served only as uploaded.

## `coho asset put ASSET [--title T] [--alt A] [--focal X,Y] [--tag T]… [--clear FIELD]…`

Reads the asset, changes what is given, and writes it back with its own ETag, so it
fails with `VERSION_CONFLICT` if somebody else wrote in between. `--tag` replaces the
tags; `--clear` takes `title`, `alt`, `focal` or `tags`. The file itself never changes:
upload a new one.

## `coho asset delete ASSET`

A tombstone on this branch, after asking (`--yes` skips the question). ⚠️ The asset's
URL keeps working.
