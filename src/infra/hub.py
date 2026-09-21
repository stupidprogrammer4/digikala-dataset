"""Use the official Hugging Face client for dataset transfers."""

from pathlib import Path

from huggingface_hub import HfApi

from schemas.config import HubSettings


class HubClient:
    def __init__(self, api: HfApi | None = None):
        self.api = api if api is not None else HfApi()

    def download(self, settings: HubSettings) -> str:
        return self.api.snapshot_download(repo_id=settings.repo_id, repo_type="dataset",
                                          revision=settings.revision, local_dir=settings.local_dir)

    def upload(self, folder: Path, repo_id: str, revision: str) -> str:
        if revision in ("main", "master", ""):
            raise ValueError("Publish to an explicit new revision; do not overwrite the frozen release")
        self.api.create_branch(repo_id=repo_id, repo_type="dataset", branch=revision, exist_ok=False)
        commit = self.api.upload_folder(repo_id=repo_id, repo_type="dataset", revision=revision,
                                       folder_path=str(folder), commit_message=f"Publish {revision}")
        return commit.commit_url
