#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.request
import urllib.error


def check_npm(package, version):
    url = f"https://registry.npmjs.org/{package}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            versions = data.get("versions", {}).keys()
            return version in versions
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise e


def check_pypi(package, version):
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            releases = data.get("releases", {}).keys()
            return version in releases
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise e


def check_crates(package, version):
    url = f"https://crates.io/api/v1/crates/{package}/{version}"
    try:
        # Crates.io returns 200 if version exists, 404 if not
        with urllib.request.urlopen(url) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise e


def check_nuget(package, version):
    # Nuget V3 flat container requires lowercase
    pkg_lower = package.lower()
    ver_lower = version.lower()
    url = f"https://api.nuget.org/v3-flatcontainer/{pkg_lower}/{ver_lower}/{pkg_lower}.nuspec"
    try:
        with urllib.request.urlopen(url) as response:
            return response.status == 200
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise e


def check_rubygems(package, version):
    url = f"https://rubygems.org/api/v1/versions/{package}.json"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            # API returns a list of objects: [{"number": "1.0.0", ...}, ...]
            for release in data:
                if release.get("number") == version:
                    return True
            return False
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise e


def check_pub(package, version):
    url = f"https://pub.dev/api/packages/{package}"
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            versions = [v["version"] for v in data.get("versions", [])]
            return version in versions
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise e


def check_luarocks(package, version):
    # LuaRocks doesn't have a simple JSON API for checking versions.
    # We check if the rockspec file exists in the manifest.
    # URL pattern: https://luarocks.org/manifests/<user>/<package>-<version>.rockspec
    # We assume the user is 'strling' or 'thecyberlocal'.
    # Since we don't know the user, we can try checking the module page.
    # https://luarocks.org/modules/<user>/<package>
    # But parsing HTML is brittle.
    # Let's try the search API if possible? No.
    # Let's assume the package is uploaded to the root manifest or a specific user.
    # The CI uses `luarocks upload`, which uses the API key.
    # Let's try to fetch the rockspec from the main server.
    # https://luarocks.org/manifests/thecyberlocal/strling-3.0.0-alpha-1.rockspec

    # We will try a few common users or just fail open (return False) if we can't verify.
    # But the goal is to prevent failure.
    # Let's try to hit the rockspec URL for 'thecyberlocal' (repo owner).

    # Note: version in rockspec usually includes revision, e.g. "3.0.0-alpha-1"
    # The input version might be "3.0.0-alpha".
    # If the input version doesn't have a revision, we might miss it.
    # But let's assume the input version is the full version string from the rockspec.

    users = ["thecyberlocal", "strling"]
    for user in users:
        url = f"https://luarocks.org/manifests/{user}/{package}-{version}.rockspec"
        try:
            with urllib.request.urlopen(url) as response:
                if response.status == 200:
                    return True
        except urllib.error.HTTPError:
            continue

    return False


def main():
    parser = argparse.ArgumentParser(
        description="Check if a package version exists on a registry."
    )
    parser.add_argument(
        "--registry",
        required=True,
        choices=["npm", "pypi", "crates", "nuget", "rubygems", "pub", "luarocks"],
        help="Package registry to check",
    )
    parser.add_argument("--package", required=True, help="Package name")
    parser.add_argument("--version", required=True, help="Package version")

    args = parser.parse_args()

    exists = False
    try:
        if args.registry == "npm":
            exists = check_npm(args.package, args.version)
        elif args.registry == "pypi":
            exists = check_pypi(args.package, args.version)
        elif args.registry == "crates":
            exists = check_crates(args.package, args.version)
        elif args.registry == "nuget":
            exists = check_nuget(args.package, args.version)
        elif args.registry == "rubygems":
            exists = check_rubygems(args.package, args.version)
        elif args.registry == "pub":
            exists = check_pub(args.package, args.version)
        elif args.registry == "luarocks":
            exists = check_luarocks(args.package, args.version)
    except Exception as e:
        print(f"Error checking registry: {e}", file=sys.stderr)
        sys.exit(2)  # Error

    if exists:
        print(f"Version {args.version} of {args.package} exists on {args.registry}.")
        sys.exit(0)  # Exists -> Skip (Success in finding it)
    else:
        print(f"Version {args.version} of {args.package} NOT found on {args.registry}.")
        sys.exit(1)  # Not Found -> Publish (Failure in finding it)


if __name__ == "__main__":
    main()
