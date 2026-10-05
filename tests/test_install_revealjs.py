"""Tests de l'installation de reveal.js (sans réseau : archive locale file://)"""
import base64
import hashlib
import io
import os
import tarfile
import tempfile
from pathlib import Path
from unittest import TestCase

from revelation.utils import install_revealjs, verify_integrity


def fausse_archive(dossier):
    """Archive au format npm : package/dist/... et package/plugin/..."""
    chemin = os.path.join(dossier, "reveal.tgz")
    with tarfile.open(chemin, "w:gz") as t:
        for nom, contenu in [("package/dist/reveal.js", b"// reveal"),
                             ("package/dist/theme/white.css", b"body{}"),
                             ("package/plugin/notes/notes.js", b"// notes")]:
            info = tarfile.TarInfo(nom)
            info.size = len(contenu)
            t.addfile(info, io.BytesIO(contenu))
    return chemin


class InstallRevealjsTestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.url = Path(fausse_archive(self.dir)).as_uri()

    def tearDown(self):
        self.tmp.cleanup()

    def test_layout_a_plat(self):
        dest = os.path.join(self.dir, "revealjs")
        install_revealjs(dest, version="9.9.9", url=self.url)
        self.assertTrue(os.path.isfile(os.path.join(dest, "reveal.js")))
        self.assertTrue(os.path.isfile(os.path.join(dest, "theme", "white.css")))
        self.assertTrue(os.path.isfile(os.path.join(dest, "plugin", "notes", "notes.js")))
        self.assertIn("9.9.9", open(os.path.join(dest, "VERSION")).read())

    def test_fichiers_locaux_conserves(self):
        dest = os.path.join(self.dir, "revealjs")
        os.makedirs(os.path.join(dest, "theme"))
        Path(dest, "theme", "heig_ec+g.css").write_text("/* heig */")
        install_revealjs(dest, version="9.9.9", url=self.url)
        self.assertEqual(Path(dest, "theme", "heig_ec+g.css").read_text(), "/* heig */")

    def test_lien_symbolique_remplace_sans_toucher_la_cible(self):
        cible = os.path.join(self.dir, "ailleurs")
        os.makedirs(cible)
        dest = os.path.join(self.dir, "revealjs")
        os.symlink(cible, dest)
        install_revealjs(dest, version="9.9.9", url=self.url)
        self.assertFalse(os.path.islink(dest))
        self.assertEqual(os.listdir(cible), [])

    def test_integrity(self):
        chemin = os.path.join(self.dir, "f.bin")
        Path(chemin).write_bytes(b"abc")
        bonne = "sha512-" + base64.b64encode(hashlib.sha512(b"abc").digest()).decode()
        verify_integrity(chemin, bonne)
        with self.assertRaises(RuntimeError):
            verify_integrity(chemin, "sha512-" + base64.b64encode(b"x" * 64).decode())
