"""Load only the active, hashed prompt parts from package resources."""

from importlib.resources import files
import tomllib

from tools.serialization import digest


class PromptStore:
    def load(self, task: str) -> tuple[str, str]:
        root = files("tools.prompts")
        manifest = tomllib.loads(root.joinpath("manifest.toml").read_text(encoding="utf-8"))
        parts = []
        for name in manifest["tasks"][task]["system_parts"]:
            raw = root.joinpath(name).read_bytes()
            if digest(raw) != manifest["files"][name]["sha256"]:
                raise ValueError("Prompt changed without a manifest update")
            parts.append(raw.decode())
        prompt = "\n\n".join(parts)
        return prompt, digest(prompt.encode())
