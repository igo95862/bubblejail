#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: 2023 igo95862
from __future__ import annotations

from argparse import ArgumentParser
from functools import partial
from subprocess import run as subprocess_run
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

run = partial(subprocess_run, check=True)


DISTRO_IMAGE: dict[str, str] = {
    "archlinux": "archlinux:latest",
    "alpine": "alpine:edge",
}

DISTRO_BUILD_DEPS: dict[str, tuple[str, ...]] = {
    "archlinux": ("python", "meson", "python-jinja", "scdoc"),
}

DISTRO_PYTHON_RUNTIME_DEPS: dict[str, tuple[str, ...]] = {
    "archlinux": (
        "python",
        "python-xdg",
        "python-tomli",
        "python-tomli-w",
        "python-pyqt6",
    )
}

DISTRO_CODE_ANALYSIS_TOOLS: dict[str, tuple[str, ...]] = {
    "archlinux": ("python-pyflakes", "codespell", "mypy"),
}

DISTRO_TEST_DEPS: dict[str, tuple[str, ...]] = {
    "archlinux": (
        "desktop-file-utils",
        "xdg-dbus-proxy",
        "bubblewrap",
        "libseccomp",
    )
}

IMAGE_BASE_NAME = "bubblejail-ci-base-{distro}"
IMAGE_BUILD_NAME = "bubblejail-ci-build-{distro}"
IMAGE_CODE_ANALYSIS_NAME = "bubblejail-ci-analysis-{distro}"
IMAGE_TEST_NAME = "bubblejail-ci-test-{distro}"


def install_packages_for_distro(
    container_name: str, distro: str, packages: tuple[str, ...]
) -> None:
    match distro:
        case "archlinux":
            run(
                (
                    "buildah",
                    "run",
                    container_name,
                    "pacman",
                    "--noconfirm",
                    "-Syu",
                    "--needed",
                    *packages,
                ),
            )
        case _:
            raise RuntimeError(f"Can't install packages for {distro}")


@contextmanager
def buildah_from(
    from_image: str,
    new_image: str,
    do_pull: bool = False,
) -> Generator[str, None, None]:
    buildah_args = ["buildah", "from"]

    if do_pull:
        buildah_args.append("--pull")

    buildah_args.append(from_image)

    container_name = run(
        buildah_args,
        text=True,
        capture_output=True,
    ).stdout.removesuffix("\n")

    if container_name is None:
        raise RuntimeError("Failed to capture container name")

    try:
        yield container_name
    except Exception:
        run(
            ("buildah", "rm", container_name),
        )
        raise

    run(
        (
            "buildah",
            "commit",
            "--rm",
            container_name,
            new_image,
        ),
    )


def build_base_image(distro: str) -> None:
    base_image_name = DISTRO_IMAGE[distro]

    with buildah_from(
        base_image_name,
        IMAGE_BASE_NAME.format(distro=distro),
        do_pull=True,
    ) as container_name:
        run(
            (
                "buildah",
                "unshare",
                "--mount",
                f"MOUNTPOINT={container_name}",
                "sh",
                "-ceu",
                (
                    "rsync -av "
                    "--exclude-from=.gitignore "
                    '. "$MOUNTPOINT/root/bubblejail"'
                ),
            ),
        )
        run(
            (
                "buildah",
                "config",
                "--workingdir",
                "/root/bubblejail",
                container_name,
            ),
        )


def build_build_image(distro: str) -> None:
    with buildah_from(
        IMAGE_BASE_NAME.format(distro=distro),
        IMAGE_BUILD_NAME.format(distro=distro),
    ) as container_name:
        install_packages_for_distro(
            container_name,
            distro,
            DISTRO_BUILD_DEPS[distro],
        )


def build_analysis_image(distro: str) -> None:
    with buildah_from(
        IMAGE_BUILD_NAME.format(distro=distro),
        IMAGE_CODE_ANALYSIS_NAME.format(distro=distro),
    ) as container_name:
        install_packages_for_distro(
            container_name,
            distro,
            DISTRO_CODE_ANALYSIS_TOOLS[distro]
            + DISTRO_PYTHON_RUNTIME_DEPS[distro],
        )


def build_test_image(distro: str) -> None:
    with buildah_from(
        IMAGE_BUILD_NAME.format(distro=distro),
        IMAGE_TEST_NAME.format(distro=distro),
    ) as container_name:
        install_packages_for_distro(
            container_name,
            distro,
            DISTRO_TEST_DEPS[distro] + DISTRO_PYTHON_RUNTIME_DEPS[distro],
        )


def build_images(distro: str) -> None:
    build_base_image(distro)
    build_build_image(distro)
    build_analysis_image(distro)
    build_test_image(distro)


def main() -> None:
    parser = ArgumentParser()

    parser.add_argument(
        "--distro",
        choices=DISTRO_IMAGE.keys(),
        default="archlinux",
    )

    args = parser.parse_args()
    build_images(**vars(args))


if __name__ == "__main__":
    main()
