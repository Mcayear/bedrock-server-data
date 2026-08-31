import hashlib
import json
import logging
import re
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List

import requests
from packaging.version import Version
from pydantic import BaseModel, Field, HttpUrl
from tqdm import tqdm

BASE_URL = "https://net-secondary.web.minecraft-services.net"
API_PATH = "/api/v1.0/download/links"
FULL_URL = f"{BASE_URL}{API_PATH}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0"
}
LINUX_MIRROR_BASE_URL = "https://repo.res.nullatom.com/Minecraft/Server/BDS/Linux/"


class ServerType(str, Enum):
    SERVER_BEDROCK_WINDOWS = "serverBedrockWindows"
    SERVER_BEDROCK_LINUX = "serverBedrockLinux"
    SERVER_BEDROCK_PREVIEW_WINDOWS = "serverBedrockPreviewWindows"
    SERVER_BEDROCK_PREVIEW_LINUX = "serverBedrockPreviewLinux"
    SERVER_JAR = "serverJar"

    @property
    def is_bedrock(self) -> bool:
        return "Bedrock" in self.value

    @property
    def is_preview(self) -> bool:
        return "Preview" in self.value

    @property
    def channel(self) -> str:
        if "serverBedrockPreview" in self.value:
            return "preview"
        elif "serverBedrock" in self.value:
            return "release"
        else:
            raise NotImplementedError

    @property
    def platform(self) -> str:
        if "Windows" in self.value:
            return "windows"
        elif "Linux" in self.value:
            return "linux"
        else:
            raise NotImplementedError


class DownloadLink(BaseModel):
    download_type: ServerType = Field(..., alias="downloadType")
    download_url: HttpUrl = Field(..., alias="downloadUrl")


class DownloadLinksResult(BaseModel):
    links: List[DownloadLink]


def get_download_links() -> dict[ServerType, HttpUrl]:
    response = requests.get(FULL_URL, headers=HEADERS)
    response.raise_for_status()
    result = DownloadLinksResult(**response.json()["result"])
    return {link.download_type: link.download_url for link in result.links}


def download_file(url, filename):
    logging.info(f"Downloading from {url} to {filename}")
    response = requests.get(url, stream=True, allow_redirects=True, headers=HEADERS)
    response.raise_for_status()
    total_size_in_bytes = int(response.headers.get("content-length", 0))
    block_size = 8192

    with tqdm(
            total=total_size_in_bytes,
            unit="iB",
            unit_scale=True,
            desc=f"Downloading {filename.name}",
    ) as progress:
        with filename.open(mode="wb") as file:
            for data in response.iter_content(block_size):
                progress.update(len(data))
                file.write(data)


def compute_checksum(filename):
    with open(filename, "rb") as f:
        file_data = f.read()

    logging.info("Computing SHA256...")
    return hashlib.sha256(file_data).hexdigest()


def update_versions_file(server_type: ServerType, version: str):
    version_file = Path("versions.json")
    if version_file.exists():
        with version_file.open(mode="r") as f:
            data = json.load(f)
    else:
        data = {"release": {"latest": "", "versions": []}, "preview": {"latest": "", "versions": []}}

    versions_list = data[server_type.channel]["versions"]
    if version not in versions_list:
        versions_list.insert(0, version)  # Add new version at the beginning
        data[server_type.channel]["latest"] = version  # Update latest

    with version_file.open(mode="w") as f:
        json.dump(data, f, indent=2)

    logging.info(f"Updated {version_file} with version {version} for {server_type.value}")


def derive_other_platform_url(url: str) -> str:
    """Derive the other platform's download URL from an existing one."""
    # Check preview variants first to avoid partial matching
    replacements = [
        ("bin-win-preview", "bin-linux-preview"),
        ("bin-linux-preview", "bin-win-preview"),
        ("bin-win", "bin-linux"),
        ("bin-linux", "bin-win"),
    ]
    for old, new in replacements:
        if old in url:
            return url.replace(old, new, 1)
    raise ValueError(f"Unable to derive other platform URL from: {url}")


def metadata_download_url(server_type: ServerType, url: str) -> str:
    """Use the mirror URL for Linux metadata while downloading from the source URL."""
    if server_type.platform == "linux":
        return f"{LINUX_MIRROR_BASE_URL}{url.rsplit('/', 1)[-1]}"
    return str(url)


def resolve_server_type(channel: str, platform: str) -> ServerType:
    """Resolve a ServerType from channel and platform strings."""
    mapping = {
        ("release", "windows"): ServerType.SERVER_BEDROCK_WINDOWS,
        ("release", "linux"): ServerType.SERVER_BEDROCK_LINUX,
        ("preview", "windows"): ServerType.SERVER_BEDROCK_PREVIEW_WINDOWS,
        ("preview", "linux"): ServerType.SERVER_BEDROCK_PREVIEW_LINUX,
    }
    return mapping[(channel, platform)]


def process(server_type: ServerType, url: str):
    logging.info(f"Processing {server_type.value} build...")

    regex = r"bedrock-server-(\d+\.\d+(?:\.\d+){1,2})\.zip"
    match = re.search(regex, url)
    if not match:
        raise ValueError("Unable to extract version from URL")

    version_parts = Version(match.group(1)).release
    version = "{}.{}.{}{}".format(
        *version_parts[:3], f"-preview.{version_parts[3]}" if server_type.is_preview else ""
    )

    with TemporaryDirectory() as tmp:
        filename = Path(tmp) / f"bedrock_server.zip"
        download_file(url, filename)
        checksum = compute_checksum(filename)

    version_dir = Path(".") / server_type.channel / version
    version_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = version_dir / "metadata.json"
    if metadata_path.exists():
        with metadata_path.open(mode="r") as f:
            metadata = json.load(f)
    else:
        metadata = {}

    metadata["version"] = version
    if "binary" not in metadata:
        metadata["binary"] = {}

    metadata["binary"][server_type.platform] = {
        "url": metadata_download_url(server_type, url),
        "sha256": checksum,
    }

    with metadata_path.open(mode="w") as f:
        json.dump(metadata, f, indent=2)

    logging.info(f"Saved metadata for {version} in {metadata_path}")

    update_versions_file(server_type, version)
    return version


def backfill_missing_platforms():
    """Scan existing metadata and fill in any missing platform binaries."""
    for channel in ("release", "preview"):
        channel_dir = Path(".") / channel
        if not channel_dir.exists():
            continue

        for version_dir in sorted(channel_dir.iterdir()):
            metadata_path = version_dir / "metadata.json"
            if not metadata_path.exists():
                continue

            with metadata_path.open(mode="r") as f:
                metadata = json.load(f)

            binary = metadata.get("binary", {})
            present = set(binary.keys())
            missing = {"windows", "linux"} - present

            if not missing:
                continue

            if not present:
                logging.warning(f"No platforms in {metadata_path}, skipping")
                continue

            existing_platform = next(iter(present))
            existing_url = binary[existing_platform]["url"]

            for missing_platform in missing:
                derived_url = derive_other_platform_url(existing_url)
                server_type = resolve_server_type(channel, missing_platform)

                logging.info(
                    f"Backfill: {channel}/{version_dir.name} missing {missing_platform}, "
                    f"trying {derived_url}"
                )

                try:
                    head = requests.head(derived_url, headers=HEADERS, allow_redirects=True)
                    if head.status_code != 200:
                        logging.warning(
                            f"Backfill: {derived_url} returned {head.status_code}, skipping"
                        )
                        continue

                    process(server_type, derived_url)
                    logging.info(f"Backfill: filled {missing_platform} for {version_dir.name}")
                except Exception as e:
                    logging.warning(
                        f"Backfill: failed to fill {missing_platform} for {version_dir.name}: {e}"
                    )


def main():
    logging.basicConfig(level=logging.INFO)

    download_links = get_download_links()
    for server_type, url in download_links.items():
        if not server_type.is_bedrock:
            continue

        version = process(server_type, str(url))
        logging.info(
            f"Processed version: {version} ({server_type.value})"
        )

    backfill_missing_platforms()


if __name__ == "__main__":
    main()
