"""Utility tools used by revelation"""

import os
import shutil
import tarfile
import zipfile
from urllib.request import urlretrieve

from . import default_config

REVEAL_URL = "https://github.com/hakimel/reveal.js/archive/{version}.tar.gz"
PLUGINS_URL = {
    "default": "https://github.com/rajgoel/reveal.js-plugins",
    "menu": "https://github.com/denehyg/reveal.js-menu",
    "math-katex": "https://github.com/j13z/reveal.js-math-katex-plugin",
    "title-footer": "https://github.com/e-gor/Reveal.js-Title-Footer",
    "toc-progress": "https://github.com/e-gor/Reveal.js-TOC-Progress"
}


def make_presentation(presentation_path):
    """
    Make a new presentation boilerplate code given a presentation_path
    """
    name = os.path.basename(presentation_path)
    # Presentation dir
    os.mkdir(presentation_path)
    # Media dir
    os.mkdir(os.path.join(presentation_path, "media"))
    # Config file
    config_file = os.path.join(
        os.path.dirname(default_config.__file__), "default_config.py"
    )
    shutil.copy(config_file, os.path.join(presentation_path, "config.py"))
    # Slide file
    with open(os.path.join(presentation_path, "slides.md"), "w") as f:
        f.write(
            "# {0}\n\nStart from here!".format(
                name.replace("_", " ").replace("-", " ").title()
            )
        )


def download_reveal(url=None, version="master", plugin=None):
    """
    Download reveal.js installation files
    """
    if not url:
        if plugin is not None:
            url = PLUGINS_URL[plugin]+"/archive/master.zip"
        else:
            url = REVEAL_URL.format(version=version)

    try:
        return urlretrieve(url)
    except Exception:
        raise


def move_and_replace(src, dst):
    """
    Helper function used to move files from one place to another,
    creating os replacing them if needed

    :param src: source directory
    :param dst: destination directory
    """

    src = os.path.abspath(src)
    dst = os.path.abspath(dst)

    for src_dir, _, files in os.walk(src):
        # using os walk to navigate through the directory tree
        # keep te dir structure by replacing the source root to
        # the destination on walked path
        dst_dir = src_dir.replace(src, dst)

        if not os.path.exists(dst_dir):
            # to prevent copy from failing, create the not existing dirs
            os.makedirs(dst_dir)

        for file_ in files:
            src_file = os.path.join(src_dir, file_)
            dst_file = os.path.join(dst_dir, file_)

            if os.path.exists(dst_file):
                os.remove(dst_file)  # to copy not fail, create existing files

            shutil.move(src_file, dst_dir)  # move the files

    shutil.rmtree(src)  # remove the dir structure from the source


def extract_file(compressed_file, path="."):
    """Extract function to extract from zip or tar file"""
    if os.path.isfile(compressed_file):
        if tarfile.is_tarfile(compressed_file):
            with tarfile.open(compressed_file, "r:gz") as tfile:
                basename = tfile.members[0].name
                tfile.extractall(path + "/")
        elif zipfile.is_zipfile(compressed_file):
            with zipfile.ZipFile(compressed_file, "r") as zfile:
                basename = zfile.namelist()[0]
                zfile.extractall(path)
        else:
            raise NotImplementedError("File type not supported")
    else:
        raise FileNotFoundError(
            "{0} is not a valid file".format(compressed_file)
        )

    return os.path.abspath(os.path.join(path, basename))


def normalize_newlines(text):
    """Normalize text to follow Unix newline pattern"""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def install_reveal_plugin(url, plugin, revealjs_folder):
    """Install reveal plugin"""
    download = download_reveal(url, plugin=plugin)

    extracted_file = extract_file(download[0])

    if os.path.isdir(os.path.join(extracted_file, "plugin")):
        install_dir = revealjs_folder
    else:
        install_dir = os.path.join(revealjs_folder, "plugin")
    print("Installing reveal.js plugin to " + install_dir)

    move_and_replace(extracted_file, install_dir)
