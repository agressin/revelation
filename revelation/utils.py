"""Utility tools used by revelation"""

import base64
import hashlib
import os
import shutil
import tarfile
import tempfile
import zipfile
from urllib.request import urlretrieve

from . import default_config

# reveal.js figé : la version servie aux cours ne doit pas changer d'elle-même.
# Le paquet npm contient dist/ et plugin/, contrairement à l'archive GitHub
# du dépôt source (qui n'a pas de dist/ à jour).
REVEAL_VERSION = "5.2.1"
REVEAL_NPM_URL = "https://registry.npmjs.org/reveal.js/-/reveal.js-{version}.tgz"
REVEAL_INTEGRITY = {   # « integrity » publié par npm (dist.integrity)
    "5.2.1": "sha512-r7//6mIM5p34hFiDMvYfXgyjXqGRta+/psd9YtytsgRlrpRzFv4RbH76TXd2qD+7ZPZEbpBDhdRhJaFgfQ7zNQ==",
}

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

    Args:
        url: Direct URL to download from (optional)
        version: Version of reveal.js to download (default: "master")
        plugin: Plugin name to download (optional)

    Returns:
        tuple: (filename, headers) from urlretrieve

    Raises:
        ValueError: If plugin is invalid
        URLError: If download fails
        HTTPError: If HTTP request fails
    """
    if not url:
        if plugin is not None:
            if plugin not in PLUGINS_URL:
                raise ValueError(
                    f"Unknown plugin '{plugin}'. "
                    f"Available plugins: {', '.join(PLUGINS_URL.keys())}"
                )
            url = PLUGINS_URL[plugin]+"/archive/master.zip"
        else:
            url = REVEAL_URL.format(version=version)

    try:
        return urlretrieve(url)
    except Exception as e:
        raise RuntimeError(f"Failed to download from {url}: {e}") from e


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


def verify_integrity(path, integrity):
    """Vérifie un fichier contre une chaîne « integrity » npm (sha512-<base64>)."""
    algo, attendu = integrity.split("-", 1)
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    obtenu = base64.b64encode(h.digest()).decode()
    if obtenu != attendu:
        raise RuntimeError(
            f"Somme de contrôle incorrecte pour {path} : attendu {attendu}, obtenu {obtenu}"
        )


def safe_extract_tar(tgz, dest):
    """Extrait une archive tar sans autoriser de chemin hors de dest."""
    with tarfile.open(tgz, "r:*") as tfile:
        if hasattr(tarfile, "data_filter"):
            tfile.extractall(dest, filter="data")
        else:  # Python < 3.12 sans le correctif : contrôle manuel
            racine = os.path.realpath(dest)
            for m in tfile.getmembers():
                cible = os.path.realpath(os.path.join(dest, m.name))
                if not cible.startswith(racine + os.sep) or m.issym() or m.islnk():
                    raise RuntimeError(f"Entrée d'archive refusée : {m.name}")
            tfile.extractall(dest)


def install_revealjs(dest, version=REVEAL_VERSION, url=None):
    """
    Installe reveal.js (paquet npm) dans dest, à plat comme l'attendent les
    templates : dest/reveal.js, dest/reveal.css, dest/theme/, dest/plugin/.

    - version figée par défaut (REVEAL_VERSION), somme de contrôle vérifiée
      quand elle est connue ;
    - si dest est un lien symbolique, le lien est retiré (sa cible n'est pas
      touchée) et remplacé par un vrai dossier : on n'écrit plus « à travers »
      un lien vers un autre dépôt ;
    - les fichiers qui ne viennent pas de reveal.js (thème HEIG, logos,
      plugins locaux) sont conservés.

    Returns:
        str: la version installée
    """
    if url is None:
        url = REVEAL_NPM_URL.format(version=version)
    integrity = REVEAL_INTEGRITY.get(version) if url == REVEAL_NPM_URL.format(version=version) else None

    with tempfile.TemporaryDirectory() as tmp:
        archive = os.path.join(tmp, "reveal.tgz")
        try:
            urlretrieve(url, archive)
        except Exception as e:
            raise RuntimeError(f"Téléchargement impossible depuis {url} : {e}") from e
        if integrity:
            verify_integrity(archive, integrity)
        safe_extract_tar(archive, tmp)
        package = os.path.join(tmp, "package")
        if not os.path.isdir(os.path.join(package, "dist")):
            raise RuntimeError(f"Archive inattendue (pas de package/dist) : {url}")

        if os.path.islink(dest):
            os.unlink(dest)
        os.makedirs(dest, exist_ok=True)
        shutil.copytree(os.path.join(package, "dist"), dest, dirs_exist_ok=True)
        if os.path.isdir(os.path.join(package, "plugin")):
            shutil.copytree(os.path.join(package, "plugin"), os.path.join(dest, "plugin"),
                            dirs_exist_ok=True)

    with open(os.path.join(dest, "VERSION"), "w") as f:
        f.write(f"reveal.js {version}\n")
    return version
