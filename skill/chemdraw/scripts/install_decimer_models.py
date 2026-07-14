from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import zipfile

import requests


MODELS = (
    {
        "name": "DECIMER",
        "url": "https://zenodo.org/records/8300489/files/models.zip?download=1",
        "md5": "de78c966b0d63b290cd3f70bb81a91e7",
        "marker": "DECIMER_model/saved_model.pb",
    },
    {
        "name": "DECIMER_HandDrawn",
        "url": "https://zenodo.org/records/10781330/files/DECIMER_HandDrawn_model.zip?download=1",
        "md5": "1fece9813549417440f7c45d0c51603a",
        "marker": "DECIMER_HandDrawn_model/saved_model.pb",
    },
)


def download(url: str, destination: Path, proxy: str | None) -> None:
    proxies = {"http": proxy, "https": proxy} if proxy else None
    with requests.get(url, stream=True, timeout=(30, 300), proxies=proxies) as response:
        response.raise_for_status()
        with destination.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"Unsafe archive member: {member.filename}")
        bundle.extractall(destination)


def main() -> int:
    parser = argparse.ArgumentParser(description="Install official DECIMER model weights")
    parser.add_argument("--proxy", help="Optional HTTP proxy, for example http://127.0.0.1:7897")
    parser.add_argument("--target", default=str(Path.home() / ".data" / "DECIMER-V2"))
    args = parser.parse_args()

    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    for model in MODELS:
        marker = target / model["marker"]
        if marker.is_file():
            print(f"{model['name']}: already installed")
            continue

        archive = target / f".{model['name']}.zip.part"
        print(f"{model['name']}: downloading {model['url']}")
        try:
            download(model["url"], archive, args.proxy)
            actual = md5(archive)
            if actual != model["md5"]:
                raise RuntimeError(
                    f"MD5 mismatch for {model['name']}: expected {model['md5']}, got {actual}"
                )
            safe_extract(archive, target)
        finally:
            archive.unlink(missing_ok=True)

        if not marker.is_file():
            raise RuntimeError(f"Expected model marker was not installed: {marker}")
        (marker.parent / ".model_url").write_text(model["url"], encoding="utf-8")
        print(f"{model['name']}: installed")

    print(f"DECIMER models ready: {target}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"DECIMER model installation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
