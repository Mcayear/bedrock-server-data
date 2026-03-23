# Bedrock Server Data

Structured metadata for Minecraft Bedrock Dedicated Server versions, including release and
preview builds. Each version entry contains download URLs and SHA256 hashes for Windows and
Linux binaries.

Used by [Endstone](https://github.com/EndstoneMC/endstone) tooling (e.g.
[bedrock-dumper](https://github.com/EndstoneMC/bedrock-dumper)) to download specific BDS
versions.

## Repository Structure

```
release/
  1.21.84/
    metadata.json       Download URLs and SHA256 hashes
  ...

preview/
  1.21.100-preview.20/
    metadata.json
  ...

versions.json           Centralized registry of all available versions
scripts/
  update.py             Automated updater (fetches new versions from Mojang)
  requirements.txt
```

## Metadata Format

Each version has a `metadata.json`:

```json
{
  "version": "1.21.84",
  "binary": {
    "windows": {
      "url": "https://www.minecraft.net/bedrockdedicatedserver/bin-win/bedrock-server-1.21.84.1.zip",
      "sha256": "a63ddc9e32641fe27531fe33315a47b366c67931deececadab142163ddb490a3"
    },
    "linux": {
      "url": "https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-1.21.84.1.zip",
      "sha256": "c0622b396fb12286c1d86d10a8d90e2e474ae9bd6668a83cfd15f2c6304a83ba"
    }
  }
}
```

## Version Registry

`versions.json` lists all available versions:

```json
{
  "release": {
    "latest": "1.21.84",
    "versions": ["1.21.84", "1.21.83", "..."]
  },
  "preview": {
    "latest": "1.21.100-preview.20",
    "versions": ["1.21.100-preview.20", "..."]
  }
}
```

## Automatic Updates

The `update.yml` workflow runs daily, fetches the latest BDS download links from Mojang,
computes SHA256 hashes, and commits any new versions automatically.

## License

[MIT License](LICENSE)