import hashlib
import json
import logging
import re
from enum import Enum
from packaging.version import Version
from pathlib import Path
from tempfile import TemporaryDirectory

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


class BuildType(Enum):
    RELEASE = "release"
    PREVIEW = "preview"


class Platform(Enum):
    WINDOWS = "windows"
    LINUX = "linux"


URL = "https://www.minecraft.net/en-us/download/server/bedrock"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0"
}


def get_download_url(build_type: BuildType, platform: Platform) -> str:
    response = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(response.content, "html.parser")

    platform_map = {
        (BuildType.RELEASE, Platform.WINDOWS): "serverBedrockWindows",
        (BuildType.RELEASE, Platform.LINUX): "serverBedrockLinux",
        (BuildType.PREVIEW, Platform.WINDOWS): "serverBedrockPreviewWindows",
        (BuildType.PREVIEW, Platform.LINUX): "serverBedrockPreviewLinux",
    }

    link = soup.find("a", {"data-platform": platform_map[(build_type, platform)]})
    if link:
        return link.get("href")
    raise ValueError(
        f"Could not find download URL for {build_type.value} {platform.value}"
    )


def download_file(url, filename):
    logging.info(f"Downloading from {url} to {filename}")
    response = requests.get(url, stream=True, allow_redirects=True, headers=HEADERS)
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


def update_versions_file(build_type: BuildType, version: str):
    version_file = Path("versions.json")
    if version_file.exists():
        with version_file.open(mode="r") as f:
            data = json.load(f)
    else:
        data = {"release": {"latest": "", "versions": []}, "preview": {"latest": "", "versions": []}}

    versions_list = data[build_type.value]["versions"]
    if version not in versions_list:
        versions_list.insert(0, version)  # Add new version at the beginning
        data[build_type.value]["latest"] = version  # Update latest

    with version_file.open(mode="w") as f:
        json.dump(data, f, indent=2)

    logging.info(f"Updated {version_file} with version {version} for {build_type.value}")


def process(build_type: BuildType, platform: Platform):
    logging.info(f"Processing {build_type.value} build for {platform.value}...")
    url = get_download_url(build_type, platform)

    regex = r"bedrock-server-(\d+\.\d+(?:\.\d+){1,2})\.zip"
    match = re.search(regex, url)
    if not match:
        raise ValueError("Unable to extract version from URL")

    version_parts = Version(match.group(1)).release
    version = "{}.{}.{}{}".format(
        *version_parts[:3], "" if build_type == BuildType.RELEASE else f"-preview.{version_parts[3]}"
    )

    with TemporaryDirectory() as tmp:
        filename = Path(tmp) / f"bedrock_server_{platform.value}.zip"
        download_file(url, filename)
        checksum = compute_checksum(filename)

    version_dir = Path(".") / build_type.value / version
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

    metadata["binary"][platform.value] = {
        "url": url,
        "sha256": checksum,
    }

    with metadata_path.open(mode="w") as f:
        json.dump(metadata, f, indent=2)

    logging.info(f"Saved metadata for {version} in {metadata_path}")

    update_versions_file(build_type, version)
    return version


def main():
    logging.basicConfig(level=logging.INFO)

    for build_type in BuildType:
        for platform in Platform:
            try:
                version = process(build_type, platform)
                logging.info(
                    f"Processed version: {version} ({build_type.value}) for {platform.value}"
                )
            except Exception as e:
                logging.error(
                    f"Failed to process {build_type.value} build for {platform.value}: {e}"
                )


if __name__ == "__main__":
    main()
