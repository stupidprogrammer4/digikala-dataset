# digikala-gold-products-fa

A Persian dataset of **7,763 Digikala gold-product listings**, together with the
code, annotation prompts and release records used to build and maintain it.
The product domain covers gold jewelry, coins, bars and melted gold. Prices are
recorded in Iranian rials (`IRR`).

**Published dataset:** [Digikala Gold Products (Persian) on Hugging Face](https://huggingface.co/datasets/amupouya/digikala-gold-products-fa)

## What we built

- Collected product listings and normalized explicit source facts.
- Created evidence-backed semantic annotations through an iterative,
  OpenAI-assisted workflow of interactive annotation sessions, independent AI
  review and coordinator corrections.
- Published and froze **v2.1: 7,763 products**, including **600 evaluation records**.
- Audited historical reservations locally and built family-grouped partitions:
  **4,803 train**, **1,214 validation**, **600 evaluation**, and **1,146 reserved**.
  These later partitions are separate from the published v2.1 membership.
- Packaged collection, normalization, API annotation, validation, export and
  maintenance code so future runs can follow a documented process.

Gold refers to the **product domain**, not a human gold standard. Historical
labels and independent reviews were AI-generated; coordinator corrections do not
establish human verification. Exact historical teacher model versions were not
recorded and remain unknown. The evaluation is an AI-reviewed reference.

The current API pipeline is a later implementation of that process. It does not
recreate the historical interactive model sessions or guarantee identical labels.
Fine-tuning and model serving are outside this project's scope.

## Published dataset

The frozen reference is **v2.1**, containing **7,763 products** at revision
[`ac32109d617722eea34c1ff69f5d0b086afe82fc`](https://huggingface.co/datasets/amupouya/digikala-gold-products-fa/tree/ac32109d617722eea34c1ff69f5d0b086afe82fc).
See the [dataset card](https://huggingface.co/datasets/amupouya/digikala-gold-products-fa/blob/ac32109d617722eea34c1ff69f5d0b086afe82fc/README.md)
for the published fields, annotation history, quality reports, and source-data terms.

| Published partition | Products | Purpose |
| --- | ---: | --- |
| `train_candidates` | 1,553 | Original candidate pool |
| `evaluation` | 600 | Frozen AI-reviewed reference |
| `reserved_context` | 5,610 | Original contextual and family reservations |

Each product combines source facts, evidence-backed semantic labels, annotation
provenance, and release membership. Prices use **Iranian rials (`IRR`)**.

Semantic annotations cover:

| Field | Meaning |
| --- | --- |
| `taxonomy` | Canonical product type, separate from marketplace category IDs |
| `audience` | Supported wearer audience |
| `styles` | Explicitly supported style descriptors |
| `motifs` | Motif family and concept |
| `use_cases` | Supported uses such as daily wear, gifts, or investment |
| `design_details` | Features such as chain pattern, form, finish, or decoration |
| `abstentions` | Reasons a field remains unknown or unsupported |
| `vocabulary_gaps` | Source concepts absent from the controlled vocabulary |

Predictions include source quotes and subjective confidence. The confidence
values are not calibrated probabilities. Passing schema and quote checks does
not establish semantic correctness.

After installing this project, load the published evaluation with Hugging Face:

```python
from datasets import load_dataset

evaluation = load_dataset(
    "amupouya/digikala-gold-products-fa",
    revision="ac32109d617722eea34c1ff69f5d0b086afe82fc",
    split="evaluation",
)
```

## Pipeline

```mermaid
flowchart LR
    A[Configured Digikala categories] --> B[Raw pages and hash receipts]
    B --> C[Explicit product facts]
    C --> D[Fixed-prompt AI annotation]
    C --> E[Independent AI review]
    D --> F[Schema and evidence checks]
    F --> G[Versioned dataset export]
    E --> H[Separate review proposals]
    G --> I[Explicit Hugging Face publication]
```

1. **Collect:** fetch configured pages with bounded concurrency, access-policy
   checks, and checkpoints. Requests stop on access or rate-limit errors.
2. **Normalize:** parse IDs, titles, prices, availability, selected attributes,
   and image URLs. Deduplicate by product ID while retaining page observations.
3. **Annotate:** send source fields, a shared policy, and one task prompt to a
   configured model. Existing labels are excluded from the input.
4. **Validate:** require the correct record ID, response schema, abstention
   consistency, and quotes present in allowed source fields.
5. **Review:** run a source-only review independently and retain its proposals
   separately. Review results cannot overwrite dataset labels through export.
6. **Export:** require a complete successful annotation run and retain source
   records, prompt hashes, available model metadata, and null human review.
7. **Maintain:** audit reservations and create family-based splits against a
   frozen reference, without rewriting evaluation labels.

Successful annotations resume only when source, prompt, and model settings
match. Failed items remain visible and make the label/review command exit with
a nonzero status. A later explicit rerun retries failed items. Export refuses
incomplete results and existing output files.

## Quick start

The local package and primary command are named `digikala-gold-products-fa`.
The GitHub repository is currently still `stupidprogrammer4/digikala-dataset`;
`digikala-dataset` remains an installed command alias for existing scripts.

Requires Python **3.11+**. The current offline checks were run with Python 3.13.
No GPU is required for API-based annotation.

```bash
git clone https://github.com/stupidprogrammer4/digikala-dataset.git digikala-gold-products-fa
cd digikala-gold-products-fa
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cp config.toml.sample config.toml
digikala-gold-products-fa --help
```

For model annotation, also install the optional provider SDK:

```bash
python -m pip install -e '.[labeling]'
```

Edit `config.toml` before a live run:

- `[crawl]`: endpoint, category IDs, output folder, page limit, concurrency,
  delay, and timeout. The sample includes the historical eight category IDs.
  `pages_per_category = 0` follows all pages reported by the API.
- `[annotation]`: LiteLLM provider-qualified model, credential environment
  variable, optional `api_base`, concurrency, timeout, and token limit.
  Enable `json_mode` only if the chosen provider/model supports it.
- `[hub]`: dataset repository, pinned revision, and local download directory.

`config.toml` is local and ignored. Only `config.toml.sample` belongs in Git.
Set credentials in the environment named by `api_key_env` (by default
`LLM_API_KEY`). `.env.example` documents the variable names; `.env` files are
not loaded automatically. `HF_TOKEN` is used by the Hugging Face SDK when needed.
Run commands from the repository root; paths are relative to the working directory.

## Commands

Start with a small page limit in your local configuration when checking access.
Live collection depends on the source API remaining available and compatible.
Use only authorized access; the collector respects robots.txt and stops on
HTTP 401, 403, or 429 rather than retrying around restrictions.

```bash
# Collect and normalize. Adjust paths if you changed crawl.output.
digikala-gold-products-fa crawl
digikala-gold-products-fa normalize artifacts/crawl/gold-v1/manifest.json artifacts/products.jsonl

# Set your model and credentials before these commands.
digikala-gold-products-fa label artifacts/products.jsonl artifacts/label-run-v1
digikala-gold-products-fa review artifacts/products.jsonl artifacts/review-run-v1
digikala-gold-products-fa export artifacts/products.jsonl artifacts/label-run-v1 artifacts/export/dataset.jsonl

# Download the published dataset at the configured revision.
digikala-gold-products-fa download

# Publish an explicitly selected folder to a new branch of an existing dataset repo.
digikala-gold-products-fa publish artifacts/export --repo-id YOUR_ACCOUNT/YOUR_DATASET --revision release-new
```

The publish command creates a new branch, refusing `main`, `master`, and existing
branches. It uploads the selected folder; prepare its dataset card and metadata
before publishing. Labeling and export never publish automatically.

For a different local configuration, place the global option before the command:

```bash
digikala-gold-products-fa --config path/to/local-config.toml crawl
```

## Frozen release maintenance

The later local reservation audit released **4,464 snapshot-only exclusions**
back into the candidate pool. A shared listing page alone does not make two
products members of the same family. Identity and evaluation-family exclusions
remain protected. The resulting 6,017 candidates were split by detected family:

| Local maintenance partition | Products |
| --- | ---: |
| `train` | 4,803 |
| `validation` | 1,214 |
| `evaluation` | 600 |
| `reserved_context` | 1,146 |

These are **local maintenance results**, distinct from the published v2.1
partitions above. They have not been published to the linked Hugging Face
revision. The evaluation export is byte-identical to the frozen reference.
The grouping uses existing family IDs, product identities, normalized titles,
numeric title variants, and shared image paths with NetworkX. Hugging Face
Datasets splits sorted family IDs with seed 42; this is not category stratification.

Metadata and original-file hashes are in [releases/](releases/), including the
[freeze reference](releases/v2.1.freeze.toml),
[pool report](releases/v2.1-pool-v1/manifest.toml),
[split report](releases/v2.1-family-split-v1/manifest.toml), and
[artifact index](releases/artifacts.toml).

```bash
digikala-gold-products-fa audit-pool
digikala-gold-products-fa split
```

These two commands require the historical frozen snapshot under
`artifacts/frozen/v2.1/`. Restore it from a trusted archive and verify it against
the freeze metadata first. The public Hub download alone does not reconstruct
the historical combined export required by these commands. Pool and split
metadata outputs use `artifacts/releases/`; data exports use `artifacts/splits/`.
Existing output directories are never overwritten. Newly collected products
are not automatically assigned this historical release's split policy.

## Project structure

```text
src/
  services/       Small classes coordinating collection, annotation and maintenance
  infra/          HTTP/model/Hub clients, stores and settings
    contracts/    Packaged JSON Schema response contract
  schemas/        Standard-library dataclasses for application records
  tools/          Pure transformations, family policies and versioned prompts
  presentation/   CLI and concrete dependency wiring
tests/            Offline tests, opt-in live API checks and synthetic examples
releases/         Versioned release metadata and original artifact hashes
artifacts/        Ignored datasets, raw JSON pages, JSONL exports and live results
config.toml.sample
pyproject.toml
```

HTTPX, Hugging Face Hub, NetworkX, Datasets, jsonschema and optional LiteLLM
provide the external integrations and graph/dataset operations. Application-owned
records use standard-library dataclasses. Services coordinate stages; infrastructure
owns network and file I/O; tools implement pure transformations; the CLI wires them.

File formats follow their purpose:

| Content | Location and format | Tracked / packaged |
| --- | --- | --- |
| Model response contract | `src/infra/contracts/gold-semantic.json` (JSON Schema) | Both |
| Active prompts and metadata | `src/tools/prompts/` (Markdown / TOML) | Both |
| Historical prompts and alias policy | `src/tools/prompts/history/` (Markdown / JSON / TOML) | Both; excluded from model context |
| Synthetic examples | `tests/fixtures/` (Python) | Git and source distribution; excluded from wheel |
| Release references and hashes | `releases/` (TOML) | Git and source distribution |
| Raw pages, receipts, runs and datasets | `artifacts/` (JSON / JSONL and other outputs) | Neither |
| Local settings / safe template | `config.toml` / `config.toml.sample` (TOML) | Only the template |

JSON and JSONL are allowed in Git and package resources when they belong there.
There is no extension-wide exclusion. Bulk data and generated outputs stay in
ignored directories; secrets, environments and caches also stay out of Git.
Frozen dataset files retain their original bytes and hashes. Existing TOML
metadata does not need conversion merely because JSON is allowed again.

Active prompts are in [src/tools/prompts/](src/tools/prompts/). Each request uses
only the shared policy, one task prompt, and product evidence. Historical
instructions remain separately identified, and their original hashes are
recorded. Synthetic examples belong to the tests and are not added to model context.

## Verification and limitations

```bash
python -m unittest discover -s tests -v
python -m pip check
```

The offline tests cover collection/resume, access restrictions, normalization,
response identity and evidence, annotation resume/export, file-write failures,
Hub revision handling, reservation policy, and family separation. They run from
a clean copy against an installed wheel without private/local data. The frozen
maintenance outputs have also been replayed and compared byte-for-byte locally.

Run the optional public API checks explicitly (no API key or model call):

```bash
GOLD_DATASET_LIVE=1 python -m unittest discover -s tests -p test_live.py -v
```

The live tests use the sample configuration, constrain collection to its first
category and one page, and save evidence under `artifacts/live-tests/`. They also
force-download the pinned public Hub card and response schema and compare their
hashes to the freeze manifest. Failures remain failures; network checks are skipped
only when not explicitly enabled. The Hub check does not download the full dataset.

Verified on **2026-09-23**: all 26 offline tests passed; both public API tests
passed. One live Digikala page produced **23 normalized products**, and both
pinned Hub files matched their frozen hashes. This verifies one current page,
not all categories, pagination or sustained crawling.

Live model annotation remains unverified. Offline model tests use mocked
responses; they do not establish model quality. A live annotation test needs the
optional labeling SDK and a configured provider/model with available credentials
and confirmed free quota. The archived original raw pages were unavailable during
the refactor, so a historical raw-to-label replay is not claimed.

Dataset limitations include first-page/ranking sampling bias, sparse positive
style/use-case labels, severe class imbalance, uncalibrated confidence, unknown
teacher revisions, and possible undetected near-duplicates. Family checks protect
detected relationships, not every possible product variant. The local family
split has no set/half-set examples in train or validation. AI-reviewed evaluation
measures agreement with that reference, not independently verified human accuracy.

## License and attribution

The software and accompanying original project documentation are licensed under
the [MIT License](LICENSE). This license does not grant rights to Digikala product
texts, images, trademarks, or other third-party source data. The dataset has its
own [dataset card and source-data terms](https://huggingface.co/datasets/amupouya/digikala-gold-products-fa);
its source-data redistribution permission remains unresolved in the frozen card.

Maintained by [stupidprogrammer4](https://github.com/stupidprogrammer4), with
OpenAI-assisted development and annotation. When referencing the dataset, include
its Hugging Face repository ID and exact revision; when referencing this pipeline,
include the Git commit and relevant prompt/schema versions.
