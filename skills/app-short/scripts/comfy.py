#!/usr/bin/env python3
"""Generate stills (Flux 3 klein) and clips (LTX-2.5 image-to-video) on the arch ComfyUI service.

    comfy.py klein --prompt-file p.txt [--ref face.png ...] --width 1152 --height 2048 --seeds 1,2,3 --prefix shorts/cast
    comfy.py i2v --image first.png --prompt-file motion.txt --width 768 --height 1344 --seconds 5 --seeds 7,8 --prefix shorts/clip

klein cites references in the prompt as <ref_image_0>, <ref_image_1>... in the order given. Every result path
is printed on its own line; outputs land in /mnt/nvme8tb/comfyui-output. llama-keepwarm unloads its resident
model by itself once ComfyUI has work; LTX needs about 72 GB, so check nvidia-smi for other jobs first.
"""

import argparse
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "http://127.0.0.1:8189"
ENTRY = "http://127.0.0.1:8188/system_stats"
OUTPUT = pathlib.Path("/mnt/nvme8tb/comfyui-output")
COMFY = pathlib.Path.home() / "AI/comfyui"
I2V_WORKFLOW = COMFY / "ComfyUI/user/default/workflows/ltx2_5_i2v_bf16.json"
I2V_SUBGRAPH, I2V_IMAGE, I2V_SAVE, I2V_RESOLUTION = 398, 395, 75, 403


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="mode", required=True)
    klein = sub.add_parser("klein")
    klein.add_argument("--prompt-file", required=True)
    klein.add_argument("--ref", dest="refs", action="append", default=[])
    klein.add_argument("--ref-mp", type=float, default=1.0)
    klein.add_argument("--width", type=int, required=True)
    klein.add_argument("--height", type=int, required=True)
    klein.add_argument("--steps", type=int, default=50)
    klein.add_argument("--cfg", type=float, default=3.5)
    klein.add_argument("--seeds", default="1")
    klein.add_argument("--prefix", required=True)
    i2v = sub.add_parser("i2v")
    i2v.add_argument("--image", required=True)
    i2v.add_argument("--prompt-file", required=True)
    i2v.add_argument("--width", type=int, required=True)
    i2v.add_argument("--height", type=int, required=True)
    i2v.add_argument("--seconds", type=int, default=5)
    i2v.add_argument("--fps", type=int, default=24)
    i2v.add_argument("--seeds", default="1")
    i2v.add_argument("--prefix", required=True)
    return parser.parse_args()


def request(path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(API + path, data, {"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit(error.read().decode()[:3000])


def wait_for_service() -> None:
    for _ in range(90):
        try:
            urllib.request.urlopen(ENTRY, timeout=5).read()
            urllib.request.urlopen(API + "/system_stats", timeout=5).read()
            return
        except OSError:
            time.sleep(2)
    sys.exit("ComfyUI did not come up")


def upload(path: str) -> str:
    name = "shorts_" + pathlib.Path(path).name
    subprocess.run(["curl", "-sf", "-X", "POST", API + "/upload/image", "-F", f"image=@{path};filename={name}",
                    "-F", "overwrite=true"], check=True, stdout=subprocess.DEVNULL)
    return name


def run_graph(graph: dict) -> list[pathlib.Path]:
    """Queue one API graph, wait for it, and return the files it wrote."""
    prompt_id = request("/prompt", {"prompt": graph, "client_id": "app-short"})["prompt_id"]
    while True:
        time.sleep(4)
        history = request(f"/history/{prompt_id}")
        if prompt_id not in history:
            continue
        run = history[prompt_id]
        if run["status"].get("status_str") == "error":
            sys.exit(json.dumps(run["status"]["messages"])[-2500:])
        if run["status"].get("completed"):
            files = []
            for output in run["outputs"].values():
                for item in output.get("images", []) + output.get("videos", []):
                    files.append(OUTPUT / item.get("subfolder", "") / item["filename"])
            return files


def klein_graph(args: argparse.Namespace, prompt: str, refs: list[str], seed: int) -> dict:
    graph = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux3_image_klein_sd_bf16.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_4b_bf16.safetensors", "type": "flux3", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": ""}},
    }
    positive, negative = ["4", 0], ["5", 0]
    if refs:
        inputs = {"positive": positive, "negative": negative, "vae": ["3", 0], "resolution": "resize",
                  "resolution.megapixels": args.ref_mp}
        for index, name in enumerate(refs):
            graph[str(20 + index)] = {"class_type": "LoadImage", "inputs": {"image": name}}
            inputs[f"images.image{index}"] = [str(20 + index), 0]
        graph["10"] = {"class_type": "ReferenceMultiLatent", "inputs": inputs}
        positive, negative = ["10", 0], ["10", 1]
    graph["6"] = {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": args.width, "height": args.height, "batch_size": 1}}
    graph["7"] = {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": positive, "negative": negative, "latent_image": ["6", 0], "seed": seed,
        "steps": args.steps, "cfg": args.cfg, "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}}
    graph["8"] = {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}}
    graph["9"] = {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": f"{args.prefix}_s{seed}"}}
    return graph


def fill_defaults(api: dict) -> dict:
    """Supply defaults for widgets a newer ComfyUI added since the stock workflow was saved."""
    spec = request("/object_info")
    for node in api.values():
        signature = spec.get(node["class_type"], {}).get("input", {})
        for name, definition in {**(signature.get("required") or {}), **(signature.get("optional") or {})}.items():
            if node["inputs"].get(name) is not None:
                continue
            options = definition[1] if len(definition) > 1 and isinstance(definition[1], dict) else {}
            if "default" in options:
                node["inputs"][name] = options["default"]
            elif definition[0] == "COMBO" and options.get("options"):
                node["inputs"][name] = options["options"][0]
    return api


def i2v_graph(args: argparse.Namespace, prompt: str, image: str, seed: int, work: pathlib.Path) -> dict:
    """The stock LTX-2.5 i2v workflow, flattened, with every subgraph input set on the inner node it feeds.

    wf2api maps the subgraph node's widget values one slot off for this graph (it counts the IMAGE,MASK input as
    a widget), so the values are written straight onto the inner nodes after conversion instead.
    """
    doc = json.loads(I2V_WORKFLOW.read_text())
    doc["nodes"] = [n for n in doc["nodes"] if n["id"] != I2V_RESOLUTION]
    doc["links"] = [link for link in doc["links"] if link[1] != I2V_RESOLUTION]
    for node in doc["nodes"]:
        if node["id"] == I2V_SUBGRAPH:
            for slot in node["inputs"]:
                if slot["name"] in ("value_3", "value_4"):
                    slot["link"] = None
    ui, api = work / f"ui_{seed}.json", work / f"api_{seed}.json"
    ui.write_text(json.dumps(doc))
    subprocess.run([sys.executable, str(COMFY / "wf2api.py"), str(ui), str(api)], check=True, stdout=subprocess.DEVNULL)
    graph = json.loads(api.read_text())
    ui.unlink()
    api.unlink()
    inner = {
        "376": {"value": prompt}, "383": {"value": False}, "363": {"value": False},
        "362": {"value": args.seconds}, "372": {"value": args.width}, "360": {"value": args.height},
        "361": {"value": args.fps}, "339": {"noise_seed": seed},
        "384": {"unet_name": "ltx-2.5-22b-distilled-transformer-bf16.safetensors"},
        "385": {"vae_name": "ltx-2.5-video-vae-bf16.safetensors"},
        "386": {"vae_name": "ltx-2.5-audio-vae-bf16.safetensors"},
        "387": {"clip_name": "gemma4-12b-with-proj-ltx-2.5-bf16.safetensors"},
        "393": {"clip_name": "gemma4_e2b_it_bf16.safetensors"},
        "371": {"model_name": "ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors"},
    }
    for node_id, values in inner.items():
        graph[f"{I2V_SUBGRAPH}_{node_id}"]["inputs"].update(values)
    graph[str(I2V_IMAGE)]["inputs"]["image"] = image
    graph[str(I2V_SAVE)]["inputs"]["filename_prefix"] = f"{args.prefix}_s{seed}"
    return fill_defaults(graph)


def main() -> None:
    args = parse_args()
    prompt = pathlib.Path(args.prompt_file).read_text().strip()
    seeds = [int(s) for s in args.seeds.split(",")]
    wait_for_service()
    work = pathlib.Path(args.prompt_file).resolve().parent
    for seed in seeds:
        started = time.time()
        if args.mode == "klein":
            graph = klein_graph(args, prompt, [upload(r) for r in args.refs], seed)
        else:
            graph = i2v_graph(args, prompt, upload(args.image), seed, work)
        for path in run_graph(graph):
            print(path, flush=True)
        print(f"seed {seed}: {time.time() - started:.0f}s", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
