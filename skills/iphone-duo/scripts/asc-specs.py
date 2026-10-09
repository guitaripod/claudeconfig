#!/usr/bin/env python3
"""Print the App Store Connect asset specs that matter for iPhone Duo, straight from Apple's API.

Reads `asc asset-library specs` (asc 5.12 or later) and prints, per placement, the accepted image
and video sizes, formats and limits for: iPhone Duo screenshots and previews, the product page
Header asset, and the App Store Search Results asset. Always read this before producing assets:
the numbers are Apple's current policy, not a copy of it.

    asc-specs.py            human-readable table
    asc-specs.py --json     machine-readable list of {placement, group, kind, ...}
"""
import json
import subprocess
import sys

PLACEMENTS = ("APP_SCREENSHOT", "APP_PREVIEW", "PRODUCT_PAGE_HEADER_ASSET", "APP_STORE_SEARCH_RESULTS_ASSET")
DUO_GROUP = "IPHONE_DUO_PROFILE"


def load_specs():
    """Returns the specs attributes from `asc asset-library specs`, or exits with a hint."""
    process = subprocess.run(["asc", "asset-library", "specs", "--output", "json"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if process.returncode != 0:
        sys.exit("asc-specs.py: `asc asset-library specs` failed; upgrade asc (needs 5.12 or later): "
                 + process.stderr.strip()[-200:])
    return json.loads(process.stdout)["data"][0]["attributes"]


def span(low, high):
    """Formats a fixed value or a range."""
    return str(low) if low == high else "%s-%s" % (low, high)


def describe(spec, kind):
    """One dict per spec, with the fields an agent needs to size and encode an asset."""
    dimensions = spec["dimensions"]
    entry = {
        "kind": kind,
        "width": span(dimensions["minWidth"], dimensions["maxWidth"]),
        "height": span(dimensions["minHeight"], dimensions["maxHeight"]),
        "ratio": spec["aspectRatio"],
        "formats": spec["fileExtensions"],
        "universal": spec["universalAsset"],
    }
    if kind == "image":
        entry["alpha"] = spec["alphaAllowed"]
    else:
        entry["fps"] = [rate["minFps"] for rate in spec["frameRates"]]
        entry["duration"] = "%s to %s" % (spec["duration"]["min"], spec["duration"]["max"])
        entry["audioRequired"] = spec["audioRequired"]
    return entry


def collect(attributes):
    """Builds the list of per-placement spec entries for the placements and the Duo group."""
    images = {spec["specId"]: spec for spec in attributes["imageSpecs"]}
    videos = {spec["specId"]: spec for spec in attributes["videoSpecs"]}
    limits = {}
    for feature in attributes["features"]:
        if feature["featureId"] != "APP_STORE_VERSIONS":
            continue
        for policy in feature["placementPolicies"]:
            for group in policy["groupLimits"]:
                for identifier in group["groupIds"]:
                    limits[(policy["placementType"], identifier)] = group["maxCount"]
    entries = []
    for placement in attributes["placementTypes"]:
        name = placement["placementTypeId"]
        if name not in PLACEMENTS:
            continue
        for mapping in placement["specMappings"]:
            group = mapping["placementGroupId"]
            if name in ("APP_SCREENSHOT", "APP_PREVIEW") and group != DUO_GROUP:
                continue
            for identifier in mapping["specs"]:
                kind = "image" if identifier in images else "video"
                spec = images.get(identifier) or videos.get(identifier)
                entry = describe(spec, kind)
                entry.update(placement=name, group=group, maxCount=limits.get((name, group)))
                entries.append(entry)
    return entries


def main():
    entries = collect(load_specs())
    if "--json" in sys.argv:
        print(json.dumps(entries, indent=2))
        return 0
    for entry in entries:
        extra = ("alpha=%s" % entry["alpha"]) if entry["kind"] == "image" else (
            "fps=%s %s audio=%s" % (entry["fps"], entry["duration"], entry["audioRequired"]))
        print("%-32s %-18s max %-3s %-5s %s x %s  %-5s %s  %s%s" % (
            entry["placement"], entry["group"], entry["maxCount"], entry["kind"], entry["width"], entry["height"],
            entry["ratio"], "/".join(entry["formats"]), extra, "  (universal)" if entry["universal"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
