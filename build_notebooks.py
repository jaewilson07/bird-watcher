"""Build the 10 bird-watcher tutorial notebooks.

Run from the repo root:

    python build_notebooks.py

Design contract (in collaboration with the user):
- nbdev: notebooks are the source of truth. `#| export` directives become .py.
- **One module per notebook**: every module file (.py) is generated from exactly
  one notebook. If two notebooks try to write the same module, the later one
  overwrites the earlier — that's a footgun we avoid by grouping all functions
  for a given module into a single notebook.
- `_FILE` / `_FOLDER` suffixes on file/folder constants.
- Plain-English docstrings + type hints on every exported function.
- `config.yaml` loader cell at the top of every notebook from #2 onward.
- Kid-friendly function names: `get_image_from_camera`, `find_birds_in_image`,
  `name_bird_in_image`, `save_sighting_to_db`, `list_sightings_from_db`,
  `send_alert_to_slack`, `build_sighting_alert`, `build_daily_summary`,
  `send_daily_summary`, `schedule_daily_summary`, `create_app`, `crop_bird_from_image`.
"""

from __future__ import annotations

import nbformat as nbf

# ############################################################################
# Cell builders
# ############################################################################


def md(text: str) -> nbf.NotebookNode:
    return nbf.v4.new_markdown_cell(text)


def code(
    source: str,
    *,
    export: bool = False,
    default_exp: str | None = None,
    imports: str = "",
) -> nbf.NotebookNode:
    """Build a code cell.

    If `default_exp` is set, this cell ALSO sets the nbdev export target — only
    use on its own at the top of a notebook (or where the target module changes).
    If `export` is True, add `#| export` so the cell lands in the package.
    If `imports` is set, those import statements are prepended to the cell so the
    generated .py file has everything it needs (nbdev doesn't auto-carry imports).
    """
    prefixes: list[str] = []
    if default_exp is not None:
        prefixes.append(f"#| default_exp {default_exp}\n")
    if export:
        prefixes.append("#| export\n")
    if prefixes or imports:
        body = source if source.strip() else ""
        # imports go AFTER directives but BEFORE function code
        injected = "".join(prefixes)
        if imports:
            injected += imports.rstrip() + "\n\n"
        source = injected + body
    return nbf.v4.new_code_cell(source)


# ############################################################################
# Shared preamble: config.yaml + _FILE / _FOLDER constants.
# Hardcoded fallbacks so notebooks still run if config.yaml is missing.
# ############################################################################

ENV_PREAMBLE = """\
from pathlib import Path

import yaml

ROOT_CANDIDATES = [Path.cwd(), Path.cwd().parent]
PROJECT_ROOT = next(
    (root for root in ROOT_CANDIDATES if (root / "tutorials").exists()),
    Path.cwd(),
)
CONFIG_FILE = PROJECT_ROOT / "config.yaml"

CONFIG = {}
if CONFIG_FILE.exists():
    CONFIG = yaml.safe_load(CONFIG_FILE.read_text()) or {}
    if not isinstance(CONFIG, dict):
        raise TypeError(f"{CONFIG_FILE} must contain a top-level mapping")
else:
    print(f"Config file not found at {CONFIG_FILE}; using defaults.")

# Folder + file constants. _FOLDER = a directory, _FILE = a single file.
TUTORIALS_FOLDER = PROJECT_ROOT / "tutorials"
DATA_FOLDER = PROJECT_ROOT / "data"
SNAPSHOT_FOLDER = DATA_FOLDER / "snapshots"
CROP_FOLDER = DATA_FOLDER / "crops"
DB_FILE = DATA_FOLDER / "birds.db"
SAMPLE_BIRD_FILE = DATA_FOLDER / "samples" / "sample-bird.jpg"
MODEL_FILE = PROJECT_ROOT / "yolov8n.pt"

# From config.yaml (or hardcoded fallback)
PHONE_IP = str(CONFIG.get("phone_ip", "192.168.1.42"))
PHONE_URL = f"http://{PHONE_IP}:8080/photo.jpg"
SLACK_WEBHOOK = str(CONFIG.get("slack_webhook", ""))
HUGGINGFACE_API_KEY = str(CONFIG.get("huggingface_api_key", ""))

SNAPSHOT_FOLDER.mkdir(parents=True, exist_ok=True)
CROP_FOLDER.mkdir(parents=True, exist_ok=True)
print(f"Snapshot folder: {SNAPSHOT_FOLDER}")
print(f"Config file: {CONFIG_FILE}")
print(f"Phone URL: {PHONE_URL}")
"""


# ############################################################################
# Notebook 1 — Setup (no exports)
# ############################################################################


def build_01_setup() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        code("", default_exp="bird_watcher"),  # silences the no-default_exp warning
        md(
            "# Step 1: Setup\n\n"
            "![Step 1 diagram](https://raw.githubusercontent.com/jaewilson07/bird-watcher/main/docs/diagrams/01-step.png)\n\n"
            "**Goal:** make sure Python and the `bird-watcher` package are ready to go.\n\n"
            "No fancy parts in this step — just install and verify. If something breaks here, fix it before moving on."
        ),
        md("## Step 1.1 — Check Python\n\nWe need Python 3.10 or newer."),
        code("import sys\n\nprint(\"Python version:\", sys.version)\nassert sys.version_info >= (3, 10), \"Need Python 3.10+\""),
        md("## Step 1.2 — Say hello to `bird-watcher`\n\nImport the package and print its version."),
        code("import bird_watcher\nprint(\"bird-watcher version:\", bird_watcher.__version__)"),
        md(
            "## Step 1.3 — Load config.yaml\n\n"
            "We use `config.yaml` for local settings like the Slack webhook, your phone's IP, "
            "and the Hugging Face token. The shared setup cell reads that file once so every "
            "notebook gets the same values."
        ),
        code(ENV_PREAMBLE),
        md(
            "## Acceptance criterion\n\n"
            "The three print lines below should show real values (not errors)."
        ),
        code(
            "assert SNAPSHOT_FOLDER.exists(), f\"{SNAPSHOT_FOLDER} should exist after the setup cell\"\n"
            "assert isinstance(PHONE_IP, str) and PHONE_IP, \"PHONE_IP should be a non-empty string\"\n"
            "assert PHONE_URL.startswith(\"http\"), \"PHONE_URL should look like http://...\"\n"
            "print(\"✅ Setup complete\")"
        ),
        md(
            "## What's next\n\n"
            "**Step 2:** open [02-stream.ipynb](02-stream.ipynb) — we'll grab one photo from the camera and save it to disk."
        ),
    ]
    return nb


# ############################################################################
# Notebook 2 — build get_image.py
# ############################################################################


def build_02_stream() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        code("", default_exp="get_image"),
        md(
            "# Step 2: Grab photos from the camera\n\n"
            "![Step 2 diagram](https://raw.githubusercontent.com/jaewilson07/bird-watcher/main/docs/diagrams/02-step.png)\n\n"
            "**Goal:** connect to the phone camera, ask for one (or several) photos, save them to disk.\n\n"
            "We build **two** functions that both belong to `bird_watcher/get_image.py`:\n\n"
            "- `get_image_from_camera` — fetch one photo\n"
            "- `get_images_from_camera` — fetch several, one every few seconds\n\n"
            "Both land in `get_image.py` because they share the same `#| default_exp get_image` directive."
        ),
        md("## Step 2.0 — Setup"),
        code(ENV_PREAMBLE),
        md(
            "## Step 2.1 — The camera is just a web page\n\n"
            "IP Webcam (the Android app) serves photos at `http://PHONE_IP:8080/photo.jpg`. "
            "Open that URL in a browser — you'll see a single JPEG. We can grab that same JPEG with Python."
        ),
        code(
            "import requests\n\n"
            "response = requests.get(PHONE_URL, timeout=10)\n"
            "response.raise_for_status()\n"
            "print(\"Got\", len(response.content), \"bytes\")"
        ),
        md(
            "## Step 2.2 — Save with a timestamped filename\n\n"
            "Two photos can't have the same name. Use the current date and time."
        ),
        code(
            "from datetime import datetime\n"
            "from pathlib import Path\n\n"
            "SNAPSHOT_FOLDER.mkdir(parents=True, exist_ok=True)\n"
            "snapshot_file = SNAPSHOT_FOLDER / f\"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jpg\"\n"
            "snapshot_file.write_bytes(response.content)\n"
            "print(\"Saved:\", snapshot_file)"
        ),
        md(
            "## Step 2.3 — Wrap as `get_image_from_camera`\n\n"
            "The `#| export` directive tells nbdev: "
            "*'write this function to `bird_watcher/get_image.py`'*."
        ),
        code(
            "def get_image_from_camera(\n"
            "    camera_url: str,\n"
            "    snapshot_folder: str,\n"
            "    timeout_seconds: float = 10.0,\n"
            ") -> Path:\n"
            "    \"\"\"Grab one photo from the camera and save it with a timestamp filename.\n"
            "\n"
            "    Args:\n"
            "        camera_url: where to ask for a photo. Usually `http://PHONE_IP:8080/photo.jpg`.\n"
            "        snapshot_folder: which folder to write the photo into. Created if missing.\n"
            "        timeout_seconds: how long to wait before giving up.\n"
            "\n"
            "    Returns:\n"
            "        Path to the saved JPEG.\n"
            "    \"\"\"\n"
            "    folder = Path(snapshot_folder)\n"
            "    folder.mkdir(parents=True, exist_ok=True)\n"
            "\n"
            "    response = requests.get(camera_url, timeout=timeout_seconds)\n"
            "    response.raise_for_status()\n"
            "\n"
            "    timestamp = datetime.now().strftime(\"%Y-%m-%d_%H-%M-%S\")\n"
            "    snapshot_file = folder / f\"{timestamp}.jpg\"\n"
            "    snapshot_file.write_bytes(response.content)\n"
            "    return snapshot_file\n",
            export=True,
            imports="from datetime import datetime\nfrom pathlib import Path\nimport requests",
        ),
        md("## Step 2.4 — Add `get_images_from_camera`\n\nLoop + sleep + Stop-friendly."),
        code(
            "def get_images_from_camera(\n"
            "    camera_url: str,\n"
            "    snapshot_folder: str,\n"
            "    num_frames: int,\n"
            "    wait_seconds: float,\n"
            "    verbose: bool = True,\n"
            ") -> list[Path]:\n"
            "    \"\"\"Grab several photos from the camera, one every `wait_seconds`.\n"
            "\n"
            "    Each photo gets its own timestamped filename. Stops early if the user\n"
            "    presses Stop (KeyboardInterrupt).\n"
            "\n"
            "    Args:\n"
            "        camera_url: where to ask for a photo.\n"
            "        snapshot_folder: which folder to write the photos into.\n"
            "        num_frames: how many photos to grab before stopping.\n"
            "        wait_seconds: how long to pause between photos.\n"
            "        verbose: if True, print each saved photo's name. Default True.\n"
            "\n"
            "    Returns:\n"
            "        List of paths to the saved JPEGs, in the order they were taken.\n"
            "    \"\"\"\n"
            "    import time\n"
            "\n"
            "    saved_files: list[Path] = []\n"
            "    try:\n"
            "        for index in range(num_frames):\n"
            "            snapshot_file = get_image_from_camera(camera_url, snapshot_folder)\n"
            "            saved_files.append(snapshot_file)\n"
            "            if verbose:\n"
            "                print(f\"[{index + 1}/{num_frames}] saved {snapshot_file.name}\")\n"
            "            if index < num_frames - 1:\n"
            "                time.sleep(wait_seconds)\n"
            "    except KeyboardInterrupt:\n"
            "        if verbose:\n"
            "            print(\"Stopped by user\")\n"
            "    return saved_files\n",
            export=True,
            imports="import time\nfrom pathlib import Path",
        ),
        md("## Step 2.5 — Try them"),
        code(
            "snapshot_file = get_image_from_camera(PHONE_URL, str(SNAPSHOT_FOLDER))\n"
            "print(\"Saved:\", snapshot_file)\n"
            "assert snapshot_file.exists()\n"
            "assert snapshot_file.stat().st_size > 0"
        ),
        md(
            "## Acceptance criterion\n\n"
            "You should see a new `.jpg` in `tutorials/data/snapshots/` (e.g. `2026-07-07_18-30-00.jpg`). "
            "Open it and confirm it shows what your phone sees."
        ),
        code(
            "from PIL import Image\n"
            "image = Image.open(snapshot_file)\n"
            "print(f\"{snapshot_file.name}: {image.size[0]}x{image.size[1]} pixels\")\n"
            "image"
        ),
        md(
            "## What's next\n\n"
            "**Step 3:** open [03-poll.ipynb](03-poll.ipynb) — we *use* both functions and learn the polling pattern (frames, sleep, KeyboardInterrupt)."
        ),
    ]
    return nb


# ############################################################################
# Notebook 3 — Use get_image.py (no exports)
# ############################################################################


def build_03_poll() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        # No default_exp — this notebook doesn't export.
        md(
            "# Step 3: Polling the camera\n\n"
            "![Step 3 diagram](https://raw.githubusercontent.com/jaewilson07/bird-watcher/main/docs/diagrams/03-step.png)\n\n"
            "**Goal:** grab several photos over time, one every few seconds.\n\n"
            "In step 2 we built `get_image_from_camera` and `get_images_from_camera` and exported them to `bird_watcher/get_image.py`. "
            "Now we just *import* them and learn how the polling loop works."
        ),
        md("## Step 3.0 — Setup"),
        code(ENV_PREAMBLE + "\nfrom bird_watcher.get_image import get_image_from_camera, get_images_from_camera\nprint(\"Imported from bird_watcher.get_image: get_image_from_camera, get_images_from_camera\")"),
        md(
            "## Step 3.1 — A simple polling loop\n\n"
            "Grab 3 photos, wait 2 seconds between each."
        ),
        code(
            "snapshot_files = get_images_from_camera(\n"
            "    PHONE_URL,\n"
            "    str(SNAPSHOT_FOLDER),\n"
            "    num_frames=3,\n"
            "    wait_seconds=2,\n"
            ")\n"
            "print(f\"\\nTotal: {len(snapshot_files)} photos\")"
        ),
        md(
            "## Step 3.2 — How does `get_images_from_camera` know when to stop?\n\n"
            "It catches `KeyboardInterrupt`. If you press the Stop button in Jupyter, "
            "Python raises a `KeyboardInterrupt`, the function prints *'Stopped by user'*, "
            "and returns whatever photos it has so far. Open the source to see:"
        ),
        code(
            "import inspect\n"
            "print(inspect.getsource(get_images_from_camera))"
        ),
        md(
            "## Step 3.3 — And if you want one photo at a time?\n\n"
            "`get_image_from_camera` is for that — just one HTTP request, one file saved."
        ),
        code(
            "snapshot_file = get_image_from_camera(PHONE_URL, str(SNAPSHOT_FOLDER))\n"
            "print(\"One more:\", snapshot_file.name)"
        ),
        md(
            "## Acceptance criterion\n\n"
            "At least 3 new `.jpg` files in `tutorials/data/snapshots/`."
        ),
        code(
            "jpg_files = sorted(SNAPSHOT_FOLDER.glob(\"*.jpg\"))\n"
            "assert len(jpg_files) >= 3, f\"Expected at least 3 jpgs, found {len(jpg_files)}\"\n"
            "print(f\"✅ {len(jpg_files)} jpgs in {SNAPSHOT_FOLDER}\")"
        ),
        md(
            "## What's next\n\n"
            "**Step 4:** open [04-detect.ipynb](04-detect.ipynb) — we'll use YOLO to find birds in the photos."
        ),
    ]
    return nb


# ############################################################################
# Notebook 4 — build find_birds.py
# ############################################################################


def build_04_detect() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        code("", default_exp="find_birds"),
        md(
            "# Step 4: Detect birds in a photo\n\n"
            "![Step 4 diagram](https://raw.githubusercontent.com/jaewilson07/bird-watcher/main/docs/diagrams/04-step.png)\n\n"
            "**Goal:** given a photo, tell me where the birds are.\n\n"
            "We use a pre-trained object detector called YOLOv8n. It's small (~6MB), fast, and has 'bird' as one of its 80 classes.\n\n"
            "Two functions live in `bird_watcher/find_birds.py`:\n\n"
            "- `find_birds_in_image` — find every bird's bounding box\n"
            "- `crop_bird_from_image` — cut out one bird for the species classifier"
        ),
        md("## Step 4.0 — Setup"),
        code(
            ENV_PREAMBLE + "\n"
            "from bird_watcher.get_image import get_image_from_camera\n"
            "if not MODEL_FILE.exists():\n"
            "    print(f\"Downloading YOLO weights to {MODEL_FILE}...\")\n"
            "    import urllib.request\n"
            "    urllib.request.urlretrieve(\n"
            "        \"https://github.com/ultralytics/assets/releases/download/v8.0/yolov8n.pt\",\n"
            "        MODEL_FILE,\n"
            "    )\n"
            "print(f\"Model: {MODEL_FILE} ({MODEL_FILE.stat().st_size / 1024 / 1024:.1f} MB)\")"
        ),
        md(
            "## Step 4.1 — Grab a photo to analyze\n\n"
            "You can use one you saved earlier, or grab a fresh one. "
            "If your phone isn't reachable, the sample bird image is the fallback."
        ),
        code(
            "FRAME_FILE = SAMPLE_BIRD_FILE if SAMPLE_BIRD_FILE.exists() else get_image_from_camera(\n"
            "    PHONE_URL, str(SNAPSHOT_FOLDER)\n"
            ")\n"
            "print(f\"Analyzing: {FRAME_FILE}\")"
        ),
        md(
            "## Step 4.2 — Run YOLO and look at the raw output\n\n"
            "Each detection has a class id, a confidence score, and a bounding box (x_min, y_min, x_max, y_max)."
        ),
        code(
            "from ultralytics import YOLO\n\n"
            "model = YOLO(str(MODEL_FILE))\n"
            "results = model(str(FRAME_FILE), conf=0.4, verbose=False)\n\n"
            "for result in results:\n"
            "    for detection in result.boxes:\n"
            "        class_id = int(detection.cls[0])\n"
            "        class_name = model.names[class_id]\n"
            "        confidence = float(detection.conf[0])\n"
            "        x_min, y_min, x_max, y_max = detection.xyxy[0].tolist()\n"
            "        print(f\"  {class_name} ({confidence:.2f}): ({int(x_min)}, {int(y_min)}) - ({int(x_max)}, {int(y_max)})\")"
        ),
        md("## Step 4.3 — Wrap as `find_birds_in_image`\n\nKeep only birds — YOLO also detects people, cars, dogs, etc."),
        code(
            "def find_birds_in_image(\n"
            "    frame_file: Path,\n"
            "    model_file: Path,\n"
            "    confidence_threshold: float = 0.4,\n"
            "    verbose: bool = True,\n"
            ") -> list[dict]:\n"
            "    \"\"\"Find every bird in a single photo.\n"
            "\n"
            "    Args:\n"
            "        frame_file: path to the JPEG to analyze.\n"
            "        model_file: path to the YOLO model weights (e.g. yolov8n.pt).\n"
            "        confidence_threshold: ignore detections weaker than this (0.0 - 1.0).\n"
            "        verbose: if True, print how many birds were found. Default True.\n"
            "\n"
            "    Returns:\n"
            "        A list of bounding boxes. Each box is a dict:\n"
            "            {\n"
            "                \"x_min\": int, \"y_min\": int, \"x_max\": int, \"y_max\": int,\n"
            "                \"confidence\": float,\n"
            "            }\n"
            "        Empty list means no birds found.\n"
            "    \"\"\"\n"
            "    from ultralytics import YOLO\n"
            "\n"
            "    model = YOLO(str(model_file))\n"
            "    results = model(str(frame_file), conf=confidence_threshold, verbose=False)\n"
            "\n"
            "    boxes: list[dict] = []\n"
            "    for result in results:\n"
            "        for detection in result.boxes:\n"
            "            class_id = int(detection.cls[0])\n"
            "            class_name = model.names[class_id]\n"
            "            if class_name != \"bird\":\n"
            "                continue\n"
            "            x_min, y_min, x_max, y_max = detection.xyxy[0].tolist()\n"
            "            boxes.append(\n"
            "                {\n"
            "                    \"x_min\": int(x_min),\n"
            "                    \"y_min\": int(y_min),\n"
            "                    \"x_max\": int(x_max),\n"
            "                    \"y_max\": int(y_max),\n"
            "                    \"confidence\": float(detection.conf[0]),\n"
            "                }\n"
            "            )\n"
            "\n"
            "    if verbose:\n"
            "        print(f\"Found {len(boxes)} bird(s) in {frame_file.name}\")\n"
            "    return boxes\n",
            export=True,
            imports="from pathlib import Path\nfrom ultralytics import YOLO",
        ),
        md("## Step 4.4 — Add `crop_bird_from_image`\n\nCrop each bird for the species classifier in step 5."),
        code(
            "def crop_bird_from_image(\n"
            "    frame_file: Path,\n"
            "    bounding_box: dict,\n"
            "    crop_folder: str,\n"
            "    verbose: bool = True,\n"
            ") -> Path:\n"
            "    \"\"\"Cut out a single bird from a photo using a bounding box.\n"
            "\n"
            "    Args:\n"
            "        frame_file: the source photo.\n"
            "        bounding_box: dict with x_min, y_min, x_max, y_max.\n"
            "        crop_folder: where to save the cropped image. Created if missing.\n"
            "        verbose: if True, print where the crop was saved. Default True.\n"
            "\n"
            "    Returns:\n"
            "        Path to the cropped JPEG.\n"
            "    \"\"\"\n"
            "    from PIL import Image\n"
            "\n"
            "    folder = Path(crop_folder)\n"
            "    folder.mkdir(parents=True, exist_ok=True)\n"
            "\n"
            "    image = Image.open(frame_file)\n"
            "    crop_box = (\n"
            "        bounding_box[\"x_min\"],\n"
            "        bounding_box[\"y_min\"],\n"
            "        bounding_box[\"x_max\"],\n"
            "        bounding_box[\"y_max\"],\n"
            "    )\n"
            "    cropped = image.crop(crop_box)\n"
            "\n"
            "    crop_file = folder / f\"{frame_file.stem}-crop.jpg\"\n"
            "    cropped.save(crop_file, \"JPEG\")\n"
            "    if verbose:\n"
            "        print(f\"Saved crop: {crop_file}\")\n"
            "    return crop_file\n",
            export=True,
            imports="from pathlib import Path\nfrom PIL import Image",
        ),
        md("## Step 4.5 — Try it"),
        code(
            "bounding_boxes = find_birds_in_image(FRAME_FILE, MODEL_FILE)\n"
            "print(f\"{len(bounding_boxes)} bird(s)\")\n"
            "for box in bounding_boxes:\n"
            "    print(f\"  ({box['x_min']}, {box['y_min']}) - ({box['x_max']}, {box['y_max']}) conf={box['confidence']:.2f}\")"
        ),
        if_birds := md("## Step 4.6 — Draw the bounding boxes\n\nMake it visible."),
        code(
            "from PIL import Image, ImageDraw\n\n"
            "image = Image.open(FRAME_FILE).convert(\"RGB\")\n"
            "draw = ImageDraw.Draw(image)\n"
            "for box in bounding_boxes:\n"
            "    draw.rectangle(\n"
            "        [(box[\"x_min\"], box[\"y_min\"]), (box[\"x_max\"], box[\"y_max\"])],\n"
            "        outline=\"green\",\n"
            "        width=4,\n"
            "    )\n"
            "image"
        ),
        md(
            "## Acceptance criterion\n\n"
            "The image above should show green rectangles around any birds. "
            "If you used the sample bird image, there should be at least one rectangle."
        ),
        md(
            "## What's next\n\n"
            "**Step 5:** open [05-identify.ipynb](05-identify.ipynb) — we'll crop each bird and ask a different model \"what species is this?\""
        ),
    ]
    return nb


# ############################################################################
# Notebook 5 — build name_bird.py
# ############################################################################


def build_05_identify() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        code("", default_exp="name_bird"),
        md(
            "# Step 5: Identify the species\n\n"
            "![Step 5 diagram](https://raw.githubusercontent.com/jaewilson07/bird-watcher/main/docs/diagrams/05-step.png)\n\n"
            "**Goal:** given a photo, tell me what *species* the bird is.\n\n"
            "Detection said *'there's a bird here'*. Now we want *'it's a Northern Cardinal'*. "
            "We use a separate model — an image classifier fine-tuned on hundreds of bird species.\n\n"
            "The function `name_bird_in_image` lives in `bird_watcher/name_bird.py`."
        ),
        md("## Step 5.0 — Setup"),
        code(
            ENV_PREAMBLE + "\n"
            "from bird_watcher.get_image import get_image_from_camera\n"
            "from bird_watcher.find_birds import find_birds_in_image, crop_bird_from_image"
        ),
        md(
            "## Step 5.1 — Detect, then crop\n\n"
            "We use `find_birds_in_image` (step 4), then crop each bird to a separate image. "
            "The classifier wants a tight picture of just one bird."
        ),
        code(
            "FRAME_FILE = SAMPLE_BIRD_FILE if SAMPLE_BIRD_FILE.exists() else get_image_from_camera(\n"
            "    PHONE_URL, str(SNAPSHOT_FOLDER)\n"
            ")\n"
            "bounding_boxes = find_birds_in_image(FRAME_FILE, MODEL_FILE)\n"
            "if not bounding_boxes:\n"
            "    raise SystemExit(\"No birds detected — try a different photo.\")\n\n"
            "CROP_FILE = crop_bird_from_image(FRAME_FILE, bounding_boxes[0], str(CROP_FOLDER))\n"
            "print(f\"Cropped to {CROP_FILE}\")"
        ),
        md(
            "## Step 5.2 — Run the species classifier\n\n"
            "We'll use HuggingFace's `dennisjooo/Birds-Classifier` — ~500 species, ~80MB. "
            "First download may take a moment."
        ),
        code(
            "from transformers import pipeline\n\n"
            "classifier = pipeline(task=\"image-classification\", model=\"dennisjooo/Birds-Classifier\")\n"
            "guesses = classifier(str(CROP_FILE), top_k=3)\n"
            "for guess in guesses:\n"
            "    print(f\"  {guess['label']}: {guess['score']:.2f}\")"
        ),
        md("## Step 5.3 — Wrap as `name_bird_in_image`"),
        code(
            "def name_bird_in_image(\n"
            "    crop_file: Path,\n"
            "    top_k: int = 3,\n"
            "    verbose: bool = True,\n"
            ") -> list[dict]:\n"
            "    \"\"\"Guess the species of the bird in a cropped photo.\n"
            "\n"
            "    Args:\n"
            "        crop_file: a JPEG containing mostly one bird.\n"
            "        top_k: how many guesses to return, ranked by confidence.\n"
            "        verbose: if True, print the top guess. Default True.\n"
            "\n"
            "    Returns:\n"
            "        A list of guesses. Each is a dict:\n"
            "            {\"species\": str, \"confidence\": float}\n"
            "        Sorted from most to least confident.\n"
            "    \"\"\"\n"
            "    from transformers import pipeline\n"
            "\n"
            "    classifier = pipeline(\n"
            "        task=\"image-classification\",\n"
            "        model=\"dennisjooo/Birds-Classifier\",\n"
            "    )\n"
            "    guesses = classifier(str(crop_file), top_k=top_k)\n"
            "\n"
            "    results = [\n"
            "        {\"species\": guess[\"label\"], \"confidence\": float(guess[\"score\"])}\n"
            "        for guess in guesses\n"
            "    ]\n"
            "\n"
            "    if verbose and results:\n"
            "        top = results[0]\n"
            "        print(f\"Top guess: {top['species']} ({top['confidence']:.2f})\")\n"
            "    return results\n",
            export=True,
            imports="from pathlib import Path\nfrom transformers import pipeline",
        ),
        md("## Acceptance criterion"),
        code(
            "from bird_watcher.name_bird import name_bird_in_image\n\n"
            "guesses = name_bird_in_image(CROP_FILE)\n"
            "assert guesses, \"Should have at least one guess\"\n"
            "print(f\"✅ {guesses[0]['species']} ({guesses[0]['confidence']:.2f})\")"
        ),
        md(
            "## What's next\n\n"
            "**Step 6:** open [06-persist.ipynb](06-persist.ipynb) — we'll save every sighting to a SQLite database."
        ),
    ]
    return nb


# ############################################################################
# Notebook 6 — build save_sighting.py
# ############################################################################


def build_06_persist() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        code("", default_exp="save_sighting"),
        md(
            "# Step 6: Save sightings to a database\n\n"
            "![Step 6 diagram](https://raw.githubusercontent.com/jaewilson07/bird-watcher/main/docs/diagrams/06-step.png)\n\n"
            "**Goal:** every bird we detect and identify gets logged to a SQLite database.\n\n"
            "SQLite is built into Python — no server, just one file on disk. Perfect for a hobby project.\n\n"
            "Two functions live in `bird_watcher/save_sighting.py`:\n\n"
            "- `save_sighting_to_db` — insert one new sighting\n"
            "- `list_sightings_from_db` — read recent sightings, optionally filtered by time"
        ),
        md("## Step 6.0 — Setup"),
        code(ENV_PREAMBLE),
        md(
            "## Step 6.1 — A table for sightings\n\n"
            "Each row is one sighting: when, what species, how sure we were, which photo file."
        ),
        code(
            "import sqlite3\n\n"
            "DB_FILE.parent.mkdir(parents=True, exist_ok=True)\n"
            "with sqlite3.connect(DB_FILE) as conn:\n"
            "    conn.execute(\n"
            "        \"\"\"\n"
            "        CREATE TABLE IF NOT EXISTS sightings (\n"
            "            id              INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "            timestamp       TEXT    NOT NULL,\n"
            "            species         TEXT    NOT NULL,\n"
            "            confidence      REAL    NOT NULL,\n"
            "            snapshot_file   TEXT    NOT NULL,\n"
            "            bbox_x_min      INTEGER,\n"
            "            bbox_y_min      INTEGER,\n"
            "            bbox_x_max      INTEGER,\n"
            "            bbox_y_max      INTEGER\n"
            "        )\n"
            "        \"\"\"\n"
            "    )\n"
            "    conn.commit()\n"
            "print(f\"Table ready at {DB_FILE}\")"
        ),
        md(
            "## Step 6.2 — Insert a sighting (parameterized, never f-string)\n\n"
            "Always use `?` placeholders for user-supplied data. F-strings in SQL = SQL injection vulnerabilities."
        ),
        code(
            "from datetime import datetime\n\n"
            "timestamp = datetime.now().isoformat(timespec=\"seconds\")\n"
            "with sqlite3.connect(DB_FILE) as conn:\n"
            "    cursor = conn.execute(\n"
            "        \"\"\"\n"
            "        INSERT INTO sightings (timestamp, species, confidence, snapshot_file)\n"
            "        VALUES (?, ?, ?, ?)\n"
            "        \"\"\",\n"
            "        (timestamp, \"Northern Cardinal\", 0.92, \"data/snapshots/2026-07-07_18-30-00.jpg\"),\n"
            "    )\n"
            "    conn.commit()\n"
            "    print(\"Inserted row id:\", cursor.lastrowid)"
        ),
        md("## Step 6.3 — Wrap as `save_sighting_to_db`"),
        code(
            "def save_sighting_to_db(\n"
            "    db_file: Path,\n"
            "    snapshot_file: Path,\n"
            "    species: str,\n"
            "    confidence: float,\n"
            "    bounding_box: dict | None = None,\n"
            "    verbose: bool = True,\n"
            ") -> int:\n"
            "    \"\"\"Add one new sighting to the database.\n"
            "\n"
            "    Args:\n"
            "        db_file: path to the SQLite file.\n"
            "        snapshot_file: path to the photo file this sighting came from.\n"
            "        species: the bird's name.\n"
            "        confidence: how sure the classifier was, 0.0 - 1.0.\n"
            "        bounding_box: optional dict with x_min, y_min, x_max, y_max.\n"
            "        verbose: if True, print the new row id. Default True.\n"
            "\n"
            "    Returns:\n"
            "        The new row's id (auto-incremented).\n"
            "    \"\"\"\n"
            "    import sqlite3\n"
            "    from datetime import datetime\n"
            "\n"
            "    db_file.parent.mkdir(parents=True, exist_ok=True)\n"
            "    timestamp = datetime.now().isoformat(timespec=\"seconds\")\n"
            "    with sqlite3.connect(db_file) as conn:\n"
            "        conn.execute(\n"
            "            \"\"\"\n"
            "            CREATE TABLE IF NOT EXISTS sightings (\n"
            "                id              INTEGER PRIMARY KEY AUTOINCREMENT,\n"
            "                timestamp       TEXT    NOT NULL,\n"
            "                species         TEXT    NOT NULL,\n"
            "                confidence      REAL    NOT NULL,\n"
            "                snapshot_file   TEXT    NOT NULL,\n"
            "                bbox_x_min      INTEGER,\n"
            "                bbox_y_min      INTEGER,\n"
            "                bbox_x_max      INTEGER,\n"
            "                bbox_y_max      INTEGER\n"
            "            )\n"
            "            \"\"\"\n"
            "        )\n"
            "        cursor = conn.execute(\n"
            "            \"\"\"\n"
            "            INSERT INTO sightings (\n"
            "                timestamp, species, confidence, snapshot_file,\n"
            "                bbox_x_min, bbox_y_min, bbox_x_max, bbox_y_max\n"
            "            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)\n"
            "            \"\"\",\n"
            "            (\n"
            "                timestamp,\n"
            "                species,\n"
            "                confidence,\n"
            "                str(snapshot_file),\n"
            "                bounding_box.get(\"x_min\") if bounding_box else None,\n"
            "                bounding_box.get(\"y_min\") if bounding_box else None,\n"
            "                bounding_box.get(\"x_max\") if bounding_box else None,\n"
            "                bounding_box.get(\"y_max\") if bounding_box else None,\n"
            "            ),\n"
            "        )\n"
            "        conn.commit()\n"
            "        row_id = cursor.lastrowid\n"
            "    if verbose:\n"
            "        print(f\"Saved sighting #{row_id}: {species} ({confidence:.2f})\")\n"
            "    return row_id\n",
            export=True,
            imports="import sqlite3\nfrom datetime import datetime\nfrom pathlib import Path",
        ),
        md("## Step 6.4 — Add `list_sightings_from_db`"),
        code(
            "def list_sightings_from_db(\n"
            "    db_file: Path,\n"
            "    since: str | None = None,\n"
            "    limit: int = 100,\n"
            "    verbose: bool = True,\n"
            ") -> list[dict]:\n"
            "    \"\"\"Get sightings from the database, most recent first.\n"
            "\n"
            "    Args:\n"
            "        db_file: path to the SQLite file.\n"
            "        since: optional ISO timestamp; only return sightings after this.\n"
            "        limit: max rows to return.\n"
            "        verbose: if True, print a count. Default True.\n"
            "\n"
            "    Returns:\n"
            "        List of sighting dicts, sorted by timestamp descending.\n"
            "    \"\"\"\n"
            "    import sqlite3\n"
            "\n"
            "    if not db_file.exists():\n"
            "        return []\n"
            "    with sqlite3.connect(db_file) as conn:\n"
            "        conn.row_factory = sqlite3.Row\n"
            "        if since:\n"
            "            cursor = conn.execute(\n"
            "                \"\"\"\n"
            "                SELECT * FROM sightings\n"
            "                WHERE timestamp >= ?\n"
            "                ORDER BY timestamp DESC\n"
            "                LIMIT ?\n"
            "                \"\"\",\n"
            "                (since, limit),\n"
            "            )\n"
            "        else:\n"
            "            cursor = conn.execute(\n"
            "                \"SELECT * FROM sightings ORDER BY timestamp DESC LIMIT ?\",\n"
            "                (limit,),\n"
            "            )\n"
            "        rows = [dict(row) for row in cursor.fetchall()]\n"
            "    if verbose:\n"
            "        print(f\"{len(rows)} sighting(s) in {db_file.name}\")\n"
            "    return rows\n",
            export=True,
            imports="import sqlite3\nfrom pathlib import Path",
        ),
        md("## Acceptance criterion"),
        code(
            "from bird_watcher.save_sighting import save_sighting_to_db, list_sightings_from_db\n\n"
            "jpg_files = sorted(SNAPSHOT_FOLDER.glob(\"*.jpg\"))\n"
            "snapshot_file = SNAPSHOT_FOLDER / jpg_files[0].name if jpg_files else SNAPSHOT_FOLDER / \"missing.jpg\"\n"
            "\n"
            "row_id = save_sighting_to_db(DB_FILE, snapshot_file, \"Northern Cardinal\", 0.92)\n"
            "rows = list_sightings_from_db(DB_FILE)\n"
            "assert any(r[\"id\"] == row_id for r in rows), \"New row should be in the listing\"\n"
            "print(f\"✅ {len(rows)} sighting(s), most recent id={rows[0]['id']}\")"
        ),
        md(
            "## What's next\n\n"
            "**Step 7:** open [07-slack.ipynb](07-slack.ipynb) — we'll send a Slack message whenever we save a sighting."
        ),
    ]
    return nb


# ############################################################################
# Notebook 7 — build send_alert.py
# ############################################################################


def build_07_slack() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        code("", default_exp="send_alert"),
        md(
            "# Step 7: Slack notifications\n\n"
            "![Step 7 diagram](https://raw.githubusercontent.com/jaewilson07/bird-watcher/main/docs/diagrams/07-step.png)\n\n"
            "**Goal:** every time we save a sighting, post a message to Slack.\n\n"
            "We use a Slack **incoming webhook** — just a URL that accepts JSON. "
            "If you don't have a webhook set yet, the code falls back to a *dry-run* that prints the message instead.\n\n"
            "Two functions live in `bird_watcher/send_alert.py`:\n\n"
            "- `build_sighting_alert` — build the Slack Block Kit JSON\n"
            "- `send_alert_to_slack` — POST it (or dry-run)"
        ),
        md("## Step 7.0 — Setup"),
        code(
            ENV_PREAMBLE + "\n"
            "from bird_watcher.save_sighting import save_sighting_to_db\n"
            "print(f\"Slack webhook set: {bool(SLACK_WEBHOOK)}\")"
        ),
        md(
            "## Step 7.1 — Slack messages use Block Kit\n\n"
            "Slack Block Kit is JSON that describes the message layout. "
            "A header + a section with fields is enough for a sighting alert."
        ),
        code(
            "payload = {\n"
            "    \"blocks\": [\n"
            "        {\n"
            "            \"type\": \"header\",\n"
            "            \"text\": {\"type\": \"plain_text\", \"text\": \":bird: New sighting — Northern Cardinal\"},\n"
            "        },\n"
            "        {\n"
            "            \"type\": \"section\",\n"
            "            \"fields\": [\n"
            "                {\"type\": \"mrkdwn\", \"text\": \"*Species*\\nNorthern Cardinal\"},\n"
            "                {\"type\": \"mrkdwn\", \"text\": \"*Confidence*\\n92%\"},\n"
            "            ],\n"
            "        },\n"
            "    ]\n"
            "}\n"
            "import json\n"
            "print(json.dumps(payload, indent=2))"
        ),
        md("## Step 7.2 — Wrap the payload builder as `build_sighting_alert`"),
        code(
            "def build_sighting_alert(\n"
            "    species: str,\n"
            "    confidence: float,\n"
            "    snapshot_file: Path,\n"
            "    sighting_id: int | None = None,\n"
            ") -> dict:\n"
            "    \"\"\"Build a Slack Block Kit message payload for one sighting.\n"
            "\n"
            "    Args:\n"
            "        species: the bird's name.\n"
            "        confidence: 0.0 - 1.0.\n"
            "        snapshot_file: the photo to attach.\n"
            "        sighting_id: optional database id for cross-referencing.\n"
            "\n"
            "    Returns:\n"
            "        A dict ready to be POSTed as JSON to a Slack webhook.\n"
            "    \"\"\"\n"
            "    confidence_pct = int(confidence * 100)\n"
            "    header_text = f\":bird: New sighting — {species}\"\n"
            "    if sighting_id is not None:\n"
            "        header_text += f\" (#{sighting_id})\"\n"
            "    return {\n"
            "        \"blocks\": [\n"
            "            {\n"
            "                \"type\": \"header\",\n"
            "                \"text\": {\"type\": \"plain_text\", \"text\": header_text},\n"
            "            },\n"
            "            {\n"
            "                \"type\": \"section\",\n"
            "                \"fields\": [\n"
            "                    {\"type\": \"mrkdwn\", \"text\": f\"*Species*\\n{species}\"},\n"
            "                    {\"type\": \"mrkdwn\", \"text\": f\"*Confidence*\\n{confidence_pct}%\"},\n"
            "                    {\"type\": \"mrkdwn\", \"text\": f\"*Photo*\\n`{snapshot_file.name}`\"},\n"
            "                ],\n"
            "            },\n"
            "        ]\n"
            "    }\n",
            export=True,
            imports="from pathlib import Path",
        ),
        md("## Step 7.3 — Add `send_alert_to_slack`"),
        code(
            "def send_alert_to_slack(\n"
            "    payload: dict,\n"
            "    webhook_url: str | None = None,\n"
            "    verbose: bool = True,\n"
            ") -> bool:\n"
            "    \"\"\"POST a message payload to Slack. Prints locally if no webhook.\n"
            "\n"
            "    Args:\n"
            "        payload: the dict returned by `build_sighting_alert`.\n"
            "        webhook_url: the Slack incoming webhook URL. If empty, this runs in\n"
            "            dry-run mode and prints the payload instead.\n"
            "        verbose: if True, print whether we sent or just previewed.\n"
            "\n"
            "    Returns:\n"
            "        True if the message was sent (or dry-run previewed), False if failed.\n"
            "    \"\"\"\n"
            "    import json\n"
            "    import requests\n"
            "\n"
            "    url = webhook_url or \"\"\n"
            "    if not url:\n"
            "        if verbose:\n"
            "            print(\"[dry-run] No SLACK_WEBHOOK set. Would have sent:\")\n"
            "            print(json.dumps(payload, indent=2))\n"
            "        return True\n"
            "\n"
            "    try:\n"
            "        response = requests.post(\n"
            "            url,\n"
            "            data=json.dumps(payload),\n"
            "            headers={\"Content-Type\": \"application/json\"},\n"
            "            timeout=10,\n"
            "        )\n"
            "        response.raise_for_status()\n"
            "        if verbose:\n"
            "            print(f\"Sent to Slack (status {response.status_code})\")\n"
            "        return True\n"
            "    except requests.RequestException as exc:\n"
            "        if verbose:\n"
            "            print(f\"Slack send failed: {exc}\")\n"
            "        return False\n",
            export=True,
            imports="import json\nimport os\nimport requests",
        ),
        md("## Acceptance criterion"),
        code(
            "from bird_watcher.send_alert import build_sighting_alert, send_alert_to_slack\n\n"
            "jpg_files = sorted(SNAPSHOT_FOLDER.glob(\"*.jpg\"))\n"
            "snapshot_file = SNAPSHOT_FOLDER / jpg_files[0].name if jpg_files else SNAPSHOT_FOLDER / \"missing.jpg\"\n"
            "\n"
            "row_id = save_sighting_to_db(DB_FILE, snapshot_file, \"Northern Cardinal\", 0.92, verbose=False)\n"
            "payload = build_sighting_alert(\"Northern Cardinal\", 0.92, snapshot_file, sighting_id=row_id)\n"
            "sent = send_alert_to_slack(payload, webhook_url=SLACK_WEBHOOK)\n"
            "assert sent, \"send_alert_to_slack should return True (dry-run if no webhook)\"\n"
            "print(\"✅ Notification flow works\")"
        ),
        md(
            "## What's next\n\n"
            "**Step 8:** open [08-web-hello.ipynb](08-web-hello.ipynb) — we'll start a tiny web app with FastAPI."
        ),
    ]
    return nb


# ############################################################################
# Notebook 8 — FastAPI hello world (no exports; the factory is owned by #09)
# ############################################################################


def build_08_web_hello() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        # No default_exp — the canonical `create_app` is owned by notebook #09.
        md(
            "# Step 8: Web app hello world\n\n"
            "![Step 8 diagram](https://raw.githubusercontent.com/jaewilson07/bird-watcher/main/docs/diagrams/08-step.png)\n\n"
            "**Goal:** start a tiny web server you can open in a browser.\n\n"
            "FastAPI is the easiest Python web framework for this. We don't need HTML — just two endpoints.\n\n"
            "We *demo* FastAPI here. The canonical `create_app` factory gets exported in step 9, where we'll add the gallery."
        ),
        md("## Step 8.0 — Setup"),
        code(ENV_PREAMBLE),
        md(
            "## Step 8.1 — Hello world in 10 lines\n\n"
            "An `app` object, a `@app.get(\"/\")` decorator, a function that returns a dict. "
            "FastAPI turns the dict into JSON automatically."
        ),
        code(
            "from fastapi import FastAPI\n\n"
            "app = FastAPI(title=\"Bird Watcher\", version=\"0.0.0\")\n\n\n"
            "@app.get(\"/\")\n"
            "def index() -> dict:\n"
            "    \"\"\"Landing page.\"\"\"\n"
            "    return {\"app\": \"bird-watcher\", \"status\": \"watching\"}\n\n\n"
            "@app.get(\"/health\")\n"
            "def health() -> dict:\n"
            "    \"\"\"Health check — useful for uptime monitoring.\"\"\"\n"
            "    return {\"status\": \"ok\"}"
        ),
        md(
            "## Step 8.2 — Test without starting a server\n\n"
            "`TestClient` lets you hit your endpoints as if they were live. No `uvicorn` needed."
        ),
        code(
            "from fastapi.testclient import TestClient\n\n"
            "client = TestClient(app)\n"
            "r = client.get(\"/\")\n"
            "print(r.status_code, r.json())\n"
            "assert r.status_code == 200\n"
            "assert r.json() == {\"app\": \"bird-watcher\", \"status\": \"watching\"}\n\n"
            "r = client.get(\"/health\")\n"
            "print(r.status_code, r.json())\n"
            "assert r.status_code == 200\n"
            "assert r.json() == {\"status\": \"ok\"}\n"
            "print(\"✅ / and /health both respond\")"
        ),
        md(
            "## Step 8.3 — Why a factory function?\n\n"
            "For a real app, you want to *configure* it at startup — where's the database? where are the snapshots? "
            "A factory takes those as args and returns an `app`:\n\n"
            "```python\n"
            "def create_app(db_file, snapshot_folder) -> FastAPI:\n"
            "    app = FastAPI(...)\n"
            "    # ... add endpoints that use db_file + snapshot_folder ...\n"
            "    return app\n"
            "```\n\n"
            "We'll wire that up next, where the factory gets the `/gallery` endpoint and mounts `/snapshots` for thumbnails."
        ),
        md(
            "## What's next\n\n"
            "**Step 9:** open [09-gallery.ipynb](09-gallery.ipynb) — we'll define the `create_app` factory, add a `/gallery` endpoint, and mount the snapshot folder."
        ),
    ]
    return nb


# ############################################################################
# Notebook 9 — build web_app.py (the canonical create_app, with /gallery)
# ############################################################################


def build_09_gallery() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        code(
            "# Lazy type-hint evaluation so `Path` doesn't need to be imported\n"
            "# just to put it in a function signature.\n"
            "from __future__ import annotations",
            export=True,
        ),
        code("", default_exp="web_app"),
        md(
            "# Step 9: Gallery endpoint + canonical `create_app`\n\n"
            "![Step 9 diagram](https://raw.githubusercontent.com/jaewilson07/bird-watcher/main/docs/diagrams/09-step.png)\n\n"
            "**Goal:** add a `/gallery` endpoint that returns the recent sightings as JSON, "
            "and mount the snapshot folder so the browser can show thumbnails.\n\n"
            "We define the full factory `create_app` here — including `/`, `/health`, `/gallery`, "
            "and the static `/snapshots` mount. `bird_watcher/web_app.py` is now complete."
        ),
        md("## Step 9.0 — Setup"),
        code(ENV_PREAMBLE),
        md("## Step 9.1 — The factory + all four endpoints"),
        code(
            "def create_app(\n"
            "    db_file: Path,\n"
            "    snapshot_folder: Path,\n"
            ") -> FastAPI:\n"
            "    \"\"\"Build the full Bird Watcher FastAPI app.\n"
            "\n"
            "    Endpoints:\n"
            "        GET /          — landing page metadata\n"
            "        GET /health    — uptime check\n"
            "        GET /gallery   — recent sightings as JSON\n"
            "        GET /snapshots/... — static thumbnails (mounted if folder exists)\n"
            "\n"
            "    Args:\n"
            "        db_file: path to the SQLite file with sightings.\n"
            "        snapshot_folder: folder of saved JPEG snapshots (mounted for thumbnails).\n"
            "\n"
            "    Returns:\n"
            "        A configured FastAPI app, ready to be served with uvicorn.\n"
            "    \"\"\"\n"
            "    from fastapi import FastAPI\n"
            "    from fastapi.staticfiles import StaticFiles\n"
            "\n"
            "    from bird_watcher.save_sighting import list_sightings_from_db\n"
            "\n"
            "    app = FastAPI(title=\"Bird Watcher\", version=\"0.0.0\")\n"
            "\n"
            "    @app.get(\"/\")\n"
            "    def index() -> dict:\n"
            "        \"\"\"Landing page.\"\"\"\n"
            "        return {\"app\": \"bird-watcher\", \"status\": \"watching\"}\n"
            "\n"
            "    @app.get(\"/health\")\n"
            "    def health() -> dict:\n"
            "        \"\"\"Health check — useful for uptime monitoring.\"\"\"\n"
            "        return {\"status\": \"ok\"}\n"
            "\n"
            "    @app.get(\"/gallery\")\n"
            "    def gallery(limit: int = 50) -> dict:\n"
            "        \"\"\"Recent sightings with thumbnails.\"\"\"\n"
            "        rows = list_sightings_from_db(db_file, limit=limit, verbose=False)\n"
            "        return {\"count\": len(rows), \"sightings\": rows}\n"
            "\n"
            "    if snapshot_folder.exists():\n"
            "        app.mount(\n"
            "            \"/snapshots\",\n"
            "            StaticFiles(directory=str(snapshot_folder)),\n"
            "            name=\"snapshots\",\n"
            "        )\n"
            "\n"
            "    return app\n",
            export=True,
            imports="from pathlib import Path\nfrom fastapi import FastAPI\nfrom fastapi.staticfiles import StaticFiles\nfrom bird_watcher.save_sighting import list_sightings_from_db",
        ),
        md("## Step 9.2 — Smoke-test the app"),
        code(
            "from fastapi.testclient import TestClient\n"
            "from bird_watcher.web_app import create_app\n\n"
            "app = create_app(DB_FILE, SNAPSHOT_FOLDER)\n"
            "client = TestClient(app)\n\n"
            "r = client.get(\"/\")\n"
            "assert r.status_code == 200\n"
            "assert r.json()[\"app\"] == \"bird-watcher\"\n\n"
            "r = client.get(\"/health\")\n"
            "assert r.status_code == 200\n\n"
            "r = client.get(\"/gallery\")\n"
            "assert r.status_code == 200\n"
            "data = r.json()\n"
            "assert \"count\" in data and \"sightings\" in data\n"
            "print(f\"✅ /, /health, /gallery all 200. /gallery returned {data['count']} sightings.\")"
        ),
        md("## Acceptance criterion\n\nAll three endpoints respond with 200."),
        md(
            "## What's next\n\n"
            "**Step 10:** open [10-digest.ipynb](10-digest.ipynb) — we'll post a daily summary to Slack."
        ),
    ]
    return nb


# ############################################################################
# Notebook 10 — build daily_summary.py
# ############################################################################


def build_10_digest() -> nbf.NotebookNode:
    nb = nbf.v4.new_notebook()
    nb.cells = [
        code(
            "# Lazy type-hint evaluation so `Path` doesn't need to be imported\n"
            "# just to put it in a function signature.\n"
            "from __future__ import annotations",
            export=True,
        ),
        code("", default_exp="daily_summary"),
        md(
            "# Step 10: Daily digest\n\n"
            "![Step 10 diagram](https://raw.githubusercontent.com/jaewilson07/bird-watcher/main/docs/diagrams/10-step.png)\n\n"
            "**Goal:** once a day, post a summary to Slack — *'today we saw 7 birds, 4 unique species, top visitor was the American Robin.'*\n\n"
            "We use the `schedule` library for the daily tick. In production you'd use a real cron, but `schedule` is fine for learning.\n\n"
            "Three functions live in `bird_watcher/daily_summary.py`:\n\n"
            "- `build_daily_summary` — build the Slack Block Kit payload\n"
            "- `send_daily_summary` — build and send (or dry-run)\n"
            "- `schedule_daily_summary` — blocking scheduler that posts once a day"
        ),
        md("## Step 10.0 — Setup"),
        code(ENV_PREAMBLE),
        md(
            "## Step 10.1 — Query the last 24 hours\n\n"
            "`list_sightings_from_db` takes a `since=` timestamp. Compute it from `datetime.now()`."
        ),
        code(
            "from datetime import datetime, timedelta\n"
            "from bird_watcher.save_sighting import list_sightings_from_db\n\n"
            "cutoff = (datetime.now() - timedelta(hours=24)).isoformat(timespec=\"seconds\")\n"
            "recent = list_sightings_from_db(DB_FILE, since=cutoff, limit=500, verbose=False)\n"
            "print(f\"{len(recent)} sighting(s) in the last 24h\")"
        ),
        md("## Step 10.2 — Group by species, find the top visitor"),
        code(
            "from collections import Counter\n\n"
            "counts = Counter(s[\"species\"] for s in recent)\n"
            "print(f\"{len(counts)} unique species\")\n"
            "for species, count in counts.most_common(5):\n"
            "    print(f\"  {species}: {count}\")"
        ),
        md("## Step 10.3 — Wrap as `build_daily_summary`"),
        code(
            "def build_daily_summary(\n"
            "    db_file: Path,\n"
            "    snapshot_folder: Path,\n"
            "    window_hours: int = 24,\n"
            ") -> dict:\n"
            "    \"\"\"Build a Slack message summarizing the last `window_hours` of sightings.\n"
            "\n"
            "    Args:\n"
            "        db_file: where sightings are stored.\n"
            "        snapshot_folder: where snapshot images live (for referencing).\n"
            "        window_hours: how far back to look. Default 24 (one day).\n"
            "\n"
            "    Returns:\n"
            "        A Slack Block Kit payload.\n"
            "    \"\"\"\n"
            "    from collections import Counter\n"
            "    from datetime import datetime, timedelta\n"
            "\n"
            "    cutoff = (datetime.now() - timedelta(hours=window_hours)).isoformat(timespec=\"seconds\")\n"
            "    sightings = list_sightings_from_db(db_file, since=cutoff, limit=500, verbose=False)\n"
            "\n"
            "    total = len(sightings)\n"
            "    counts = Counter(s[\"species\"] for s in sightings)\n"
            "    unique_species = len(counts)\n"
            "    top_visitor = counts.most_common(1)[0] if counts else None\n"
            "\n"
            "    title = f\":bird: Daily summary — {total} sighting(s), {unique_species} species\"\n"
            "    if top_visitor:\n"
            "        title += f\", top: *{top_visitor[0]}*\"\n"
            "\n"
            "    blocks: list[dict] = [\n"
            "        {\"type\": \"header\", \"text\": {\"type\": \"plain_text\", \"text\": title}},\n"
            "        {\n"
            "            \"type\": \"section\",\n"
            "            \"fields\": [\n"
            "                {\"type\": \"mrkdwn\", \"text\": f\"*Window*\\nlast {window_hours}h\"},\n"
            "                {\"type\": \"mrkdwn\", \"text\": f\"*Total sightings*\\n{total}\"},\n"
            "                {\"type\": \"mrkdwn\", \"text\": f\"*Unique species*\\n{unique_species}\"},\n"
            "            ],\n"
            "        },\n"
            "    ]\n"
            "    if counts:\n"
            "        species_lines = [\n"
            "            f\"• {species} — {count}\" for species, count in counts.most_common(10)\n"
            "        ]\n"
            "        blocks.append(\n"
            "            {\n"
            "                \"type\": \"section\",\n"
            "                \"text\": {\"type\": \"mrkdwn\", \"text\": \"*Top species*\\n\" + \"\\n\".join(species_lines)},\n"
            "            }\n"
            "        )\n"
            "\n"
            "    return {\"blocks\": blocks}\n",
            export=True,
            imports="from collections import Counter\nfrom datetime import datetime, timedelta\nfrom pathlib import Path\nfrom bird_watcher.save_sighting import list_sightings_from_db",
        ),
        md("## Step 10.4 — Add `send_daily_summary`"),
        code(
            "def send_daily_summary(\n"
            "    db_file: Path,\n"
            "    snapshot_folder: Path,\n"
            "    window_hours: int = 24,\n"
            "    webhook_url: str | None = None,\n"
            "    verbose: bool = True,\n"
            ") -> bool:\n"
            "    \"\"\"Build and send (or dry-run) today's daily summary.\n"
            "\n"
            "    Args:\n"
            "        db_file: where sightings are stored.\n"
            "        snapshot_folder: where snapshot images live.\n"
            "        window_hours: how far back to look.\n"
            "        webhook_url: optional Slack webhook URL. If omitted, this becomes a dry run.\n"
            "        verbose: if True, print a status line.\n"
            "\n"
            "    Returns:\n"
            "        True if sent (or dry-run previewed), False on error.\n"
            "    \"\"\"\n"
            "    from bird_watcher.send_alert import send_alert_to_slack\n"
            "\n"
            "    payload = build_daily_summary(db_file, snapshot_folder, window_hours=window_hours)\n"
            "    return send_alert_to_slack(payload, webhook_url=webhook_url, verbose=verbose)\n",
            export=True,
            imports="from pathlib import Path\nfrom bird_watcher.send_alert import send_alert_to_slack",
        ),
        md("## Step 10.5 — And the scheduler `schedule_daily_summary`"),
        code(
            "def schedule_daily_summary(\n"
            "    db_file: Path,\n"
            "    snapshot_folder: Path,\n"
            "    run_at_hour: int = 21,\n"
            "    verbose: bool = True,\n"
            ") -> None:\n"
            "    \"\"\"Run a blocking scheduler that posts the daily summary once a day.\n"
            "\n"
            "    For learning purposes only — production code would use a real cron job.\n"
            "\n"
            "    Args:\n"
            "        db_file: where sightings are stored.\n"
            "        snapshot_folder: where snapshot images live.\n"
            "        run_at_hour: hour of day to send (24h format). Default 21 (9pm).\n"
            "        verbose: if True, print the next scheduled run.\n"
            "    \"\"\"\n"
            "    import time\n"
            "\n"
            "    import schedule\n"
            "\n"
            "    job = lambda: send_daily_summary(db_file, snapshot_folder, verbose=verbose)\n"
            "    schedule.every().day.at(f\"{run_at_hour:02d}:00\").do(job)\n"
            "    if verbose:\n"
            "        print(f\"Scheduled daily summary at {run_at_hour:02d}:00 every day\")\n"
            "        print(\"Press Stop / Ctrl+C to exit\")\n"
            "    while True:\n"
            "        schedule.run_pending()\n"
            "        time.sleep(60)\n",
            export=True,
            imports="import time\nfrom pathlib import Path\nimport schedule",
        ),
        md("## Acceptance criterion"),
        code(
            "from bird_watcher.daily_summary import build_daily_summary, send_daily_summary\n\n"
            "payload = build_daily_summary(DB_FILE, SNAPSHOT_FOLDER)\n"
            "assert \"blocks\" in payload\n"
            "assert any(b.get(\"type\") == \"header\" for b in payload[\"blocks\"])\n\n"
            "sent = send_daily_summary(DB_FILE, SNAPSHOT_FOLDER)\n"
            "assert sent, \"send_daily_summary should return True (dry-run if no webhook)\"\n"
            "print(\"✅ Daily summary built + sent (or dry-run)\")"
        ),
        md(
            "## 🎉 You finished the bird watcher tutorial!\n\n"
            "Ten notebooks. Seven modules. One bird watcher.\n\n"
            "- pull photos from a phone camera\n"
            "- find birds in those photos\n"
            "- name the species\n"
            "- log everything to a database\n"
            "- post alerts to Slack\n"
            "- serve a web gallery\n"
            "- send a daily digest\n\n"
            "**What's next?** Experiment. Add features. Break stuff. That's how you learn."
        ),
    ]
    return nb


# ############################################################################
# Orchestrator
# ############################################################################


BUILDERS = {
    "01-setup.ipynb": build_01_setup,
    "02-stream.ipynb": build_02_stream,
    "03-poll.ipynb": build_03_poll,
    "04-detect.ipynb": build_04_detect,
    "05-identify.ipynb": build_05_identify,
    "06-persist.ipynb": build_06_persist,
    "07-slack.ipynb": build_07_slack,
    "08-web-hello.ipynb": build_08_web_hello,
    "09-gallery.ipynb": build_09_gallery,
    "10-digest.ipynb": build_10_digest,
}


def main() -> None:
    from pathlib import Path

    tutorials_folder = Path("tutorials")
    tutorials_folder.mkdir(parents=True, exist_ok=True)
    for filename, builder in BUILDERS.items():
        nb = builder()
        nbformat_path = tutorials_folder / filename
        with open(nbformat_path, "w") as f:
            nbf.write(nb, f)
        print(f"wrote {nbformat_path}")


if __name__ == "__main__":
    main()