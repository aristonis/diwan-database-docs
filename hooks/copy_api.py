"""Copies the generated API reference into the built site once.

The Javadoc under docs/api/ is excluded from MkDocs (exclude_docs) so the i18n plugin does not
copy it per language and the docs search does not index thousands of class pages; this hook puts
it back at site/api/ after the build.
"""
import shutil
from pathlib import Path


def on_post_build(config, **kwargs):
    source = Path(config["docs_dir"]) / "api"
    if not source.is_dir():
        return
    target = Path(config["site_dir"]) / "api"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
