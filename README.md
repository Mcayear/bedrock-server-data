# 📦 Bedrock Server Data

This repository contains structured metadata and dumped data for **Minecraft: Bedrock Dedicated Server** versions,
including **release** and **preview** builds. Each version is organized with metadata containing download links,
hashes, and relevant details, as well as extracted game data such as **block palette**, **item tags**, **creative items
**, and more.

## 📂 Repository Structure

```
📦 bedrock-server-data
├── 📂 release
│   ├── 📂 1.20.70
│   │   ├── 📜 metadata.json
│   │   ├── 📜 block_palette.json
│   │   ├── 📜 item_tags.json
│   │   └── 📜 creative_items.json
│   ├── 📂 ...
│   └── 🔗 latest -> 1.20.50          # Symlink/reference to the latest release version
├── 📂 preview
│   ├── 📂 1.21.70-preview.26
│   │   ├── 📜 metadata.json
│   │   └── ...
│   ├── 📂 ...
│   └── 🔗 latest -> 1.21.70-preview.26  # Symlink/reference to the latest preview version
├── 📂 scripts
│   └── 📝 update.py
├── 📜 versions.json                     # A centralized file listing all versions and metadata
├── 📜 README.md
└── 📜 .gitignore
```

## 📜 Metadata Format (`metadata.json`)

Each version has a `metadata.json` file with the following structure:

```json
{
  "version": "1.21.70-preview.26",
  "binary": {
    "windows": {
      "url": "https://www.minecraft.net/bedrockdedicatedserver/bin-win-preview/bedrock-server-1.21.70.26.zip",
      "sha256": "746e99e494a77eea61fe6e4f30023d3370c7d0ad3d73c6d6dae9de5e483a87c0"
    },
    "linux": {
      "url": "https://www.minecraft.net/bedrockdedicatedserver/bin-linux-preview/bedrock-server-1.21.70.26.zip",
      "sha256": "cce936ff72f1061d8b92b4a00955f3e0348f807ba1da040f0dd9130278d22d95"
    }
  }
}
```

## 📂 Extracted Game Data

Each version contains extracted game data alongside its `metadata.json` file.

- **`block_palette.json`** – Lists all registered blocks and their properties.
- **`item_tags.json`** – Contains tag information for different items.
- **`creative_items.json`** – Represents the creative inventory layout.
- (More data files may be added as needed.)

## 📜 `versions.json`

This file contains a centralized registry of available versions.

```json
{
  "release": {
    "latest": "1.21.70",
    "versions": [
      "1.21.70",
      "1.21.61"
    ]
  },
  "preview": {
    "latest": "1.21.70-preview.26",
    "versions": [
      "1.21.70-preview.26",
      "1.21.70-preview.23"
    ]
  }
}
```

## 🎯 Contribution

If you want to contribute by adding new metadata, extracted data, or improving scripts, feel free to open an issue or
submit a PR!

## 📄 License

This repository is licensed under MIT.

