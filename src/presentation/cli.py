"""Stage commands; orchestration stays in services."""

import argparse
import asyncio
import json
from pathlib import Path

from infra.settings import SettingsLoader


def main() -> None:
    parser = argparse.ArgumentParser(prog="digikala-gold-products-fa")
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("crawl", help="Collect configured categories; resume existing raw pages")
    normal = commands.add_parser("normalize", help="Normalize a completed collection manifest")
    normal.add_argument("manifest", type=Path)
    normal.add_argument("output", type=Path)
    for name in ("label", "review"):
        command = commands.add_parser(name)
        command.add_argument("input", type=Path)
        command.add_argument("output", type=Path)
    export = commands.add_parser("export")
    export.add_argument("input", type=Path)
    export.add_argument("run", type=Path)
    export.add_argument("output", type=Path)
    commands.add_parser("download", help="Download the configured pinned Hugging Face dataset")
    publish = commands.add_parser("publish", help="Upload an explicit folder to a new Hub branch")
    publish.add_argument("folder", type=Path)
    publish.add_argument("--repo-id", required=True)
    publish.add_argument("--revision", required=True)
    commands.add_parser("audit-pool", help="Reproduce the frozen v2.1 reservation audit")
    commands.add_parser("split", help="Reproduce the frozen v2.1 family split")
    args = parser.parse_args()

    if args.command == "crawl":
        from services.collection import CollectionService
        from infra.digikala import DigikalaClient
        from infra.collection_store import CollectionStore
        settings = SettingsLoader().load(args.config).crawl
        service = CollectionService(settings, DigikalaClient(settings), CollectionStore(Path(settings.output)))
        result = asyncio.run(service.run())
        result = {"pages": len(result["pages"])}
    elif args.command == "normalize":
        from services.normalization import NormalizationService
        from infra.dataset_files import DatasetFiles
        result = NormalizationService(DatasetFiles()).run(args.manifest, args.output)
    elif args.command in ("label", "review"):
        from services.annotation import AnnotationService
        from infra.annotation_store import AnnotationStore
        from infra.annotation_contract import AnnotationContract
        from infra.model_client import ModelClient
        from infra.prompts import PromptStore
        task = "labeling" if args.command == "label" else "blind_review"
        service = AnnotationService(ModelClient(SettingsLoader().load(args.config).annotation),
                                    AnnotationStore(args.output), AnnotationContract(), PromptStore())
        result = asyncio.run(service.run(args.input, task))
        print(json.dumps(result))
        if result["failed"]:
            raise SystemExit(1)
        return
    elif args.command == "export":
        from services.export import ExportService
        from infra.dataset_files import DatasetFiles
        from infra.annotation_contract import AnnotationContract
        result = ExportService(DatasetFiles(), AnnotationContract()).run(args.input, args.run, args.output)
    elif args.command == "download":
        from infra.hub import HubClient
        result = {"directory": HubClient().download(SettingsLoader().load(args.config).hub)}
    elif args.command == "publish":
        from infra.hub import HubClient
        result = {"commit": HubClient().upload(args.folder, args.repo_id, args.revision)}
    elif args.command == "audit-pool":
        from services.reservations import ReservationService
        from infra.releases import ReleaseStore
        result = ReservationService(ReleaseStore()).run()["counts"]
    else:
        from services.splitting import SplitService
        from infra.releases import ReleaseStore
        result = SplitService(ReleaseStore()).run()["counts"]
    print(json.dumps(result))
