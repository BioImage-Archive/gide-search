import os
from pathlib import Path
from typing import Callable

import requests


class ROCrateFetcher:
    IDR_GITHUB_INFO = {
        "owner": "German-BioImaging",
        "repo": "idr_study_crates",
        "path": "ro-crates",
    }
    BIA_GITHUB_INFO = {
        "owner": "BioImage-Archive",
        "repo": "gide-ro-crate",
        "path": "study_ro_crates",
    }
    SSBD_DATASET_GITHUB_INFO = {
        "owner": "openssbd",
        "repo": "gide-ro-crate",
        "path": "project-ro-crate/database",
    }
    SSBD_REPOSITORY_GITHUB_INFO = {
        "owner": "openssbd",
        "repo": "gide-ro-crate",
        "path": "project-ro-crate/repository",
    }
    GITHUB_FOLDER = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"

    def fetch_idr_ro_crates(
        self,
        output_directory: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ):
        gitub_folder_url = self.GITHUB_FOLDER.format(**self.IDR_GITHUB_INFO)
        self._fetch_ro_crate_from_github(
            gitub_folder_url, output_directory, progress_callback
        )

    def fetch_bia_ro_crates(
        self,
        output_directory: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ):
        gitub_folder_url = self.GITHUB_FOLDER.format(**self.BIA_GITHUB_INFO)
        self._fetch_ro_crate_from_github(
            gitub_folder_url, output_directory, progress_callback
        )

    def fetch_ssbd_ro_crates(
        self,
        output_directory: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ):
        gitub_folder_url = [
            self.GITHUB_FOLDER.format(**self.SSBD_DATASET_GITHUB_INFO),
            self.GITHUB_FOLDER.format(**self.SSBD_REPOSITORY_GITHUB_INFO)
        ]
        self._fetch_ro_crate_from_github(
            gitub_folder_url, output_directory, progress_callback
        )

    @staticmethod
    def _fetch_ro_crate_from_github(
        gitub_folder_urls: str | list[str],
        target_directory: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ):
        if isinstance(gitub_folder_urls, str):
            gitub_folder_urls = [gitub_folder_urls]

        ro_crate_files = []
        for url in gitub_folder_urls:
            os.makedirs(target_directory, exist_ok=True)
            files = requests.get(url).json()

            [
                ro_crate_files.append(file)
                for file in files
                if file["type"] == "file"
                and file["name"].endswith("ro-crate-metadata.json")
            ]

        total = len(ro_crate_files)

        for index, file in enumerate(ro_crate_files, start=1):
            file_data = requests.get(file["download_url"]).content
            with open(target_directory / file["name"], "wb") as f:
                f.write(file_data)

            if progress_callback:
                progress_callback(index, total)
