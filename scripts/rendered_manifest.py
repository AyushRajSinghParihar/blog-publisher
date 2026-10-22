#!/usr/bin/env python3
"""Compare supplied rendered HTML artifacts. Never fetches or publishes anything."""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit


VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())
SKIP = frozenset({"script", "style", "template"})
URL_ATTRIBUTES = frozenset({"href", "src", "poster", "cite", "xlink:href"})
CRAWLER_META = frozenset({"robots", "googlebot", "bingbot"})
META_NAMES = CRAWLER_META | {"description"}


class Element:
    def __init__(self, tag, attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.root = Element("document")
        self.stack = [self.root]
        self.feed(source)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def elements(node):
    yield node
    for child in node.children:
        if isinstance(child, Element):
            yield from elements(child)


def text_content(node):
    return "".join(
        child if isinstance(child, str) else text_content(child)
        for child in node.children
    )


def spaced(value):
    return re.sub(r"\s+", " ", value).strip()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(value).hexdigest()


def valid_url(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("Document URL must be absolute HTTP(S), without credentials or a fragment")
    return value


def semantic_node(node, base, literal=False):
    if node.tag in SKIP:
        return None
    attrs = {}
    for name, value in sorted(node.attrs.items()):
        if name in {"class", "style", "nonce"} or name.startswith("data-"):
            continue
        if value is not None and name in URL_ATTRIBUTES:
            value = urljoin(base, value)
        attrs[name] = value
    literal = literal or node.tag in {"pre", "code"}
    children = []
    for child in node.children:
        if isinstance(child, str):
            value = child if literal else re.sub(r"\s+", " ", child)
        else:
            value = semantic_node(child, base, literal)
        if value is not None and value != "":
            children.append(value)
    return {"tag": node.tag, "attrs": attrs, "children": children}


def strict_json(source):
    def invalid_constant(value):
        raise ValueError("Non-JSON numeric constant: " + value)
    return json.loads(source, parse_constant=invalid_constant)


def document_semantics(source, location, selector):
    doc = Document(source)
    nodes = list(elements(doc.root))
    base_nodes = [n for n in nodes if n.tag == "base" and n.attrs.get("href")]
    if len(base_nodes) > 1:
        raise ValueError("Ambiguous document base URL")
    base = urljoin(location, base_nodes[0].attrs["href"]) if base_nodes else location
    targets = [
        n for n in nodes
        if (n.attrs.get("id") == selector["id"] if "id" in selector else n.tag == selector["tag"])
    ]
    if len(targets) != 1:
        raise ValueError("Article selector must identify exactly one element; found " + str(len(targets)))
    titles = [spaced(text_content(n)) for n in nodes if n.tag == "title"]
    if len(titles) != 1 or not titles[0]:
        raise ValueError("Expected one nonempty document title")
    canonicals = [
        urljoin(base, n.attrs["href"])
        for n in nodes
        if n.tag == "link"
        and "canonical" in (n.attrs.get("rel") or "").lower().split()
        and n.attrs.get("href")
    ]
    if len(canonicals) != 1:
        raise ValueError("Expected exactly one canonical link")
    metadata = {}
    for node in nodes:
        if node.tag != "meta":
            continue
        name = (node.attrs.get("name") or node.attrs.get("property") or "").lower()
        if name in META_NAMES or name.startswith(("og:", "twitter:")):
            metadata.setdefault(name, []).append(node.attrs.get("content") or "")
    if len(metadata.get("description", [])) != 1 or not spaced(metadata["description"][0]):
        raise ValueError("Expected exactly one nonempty meta description")
    structured = []
    for node in nodes:
        if node.tag == "script" and (node.attrs.get("type") or "").lower().split(";")[0].strip() == "application/ld+json":
            structured.append(strict_json(text_content(node)))
    html_nodes = [n for n in nodes if n.tag == "html"]
    return {
        "canonical": canonicals[0],
        "title": titles[0],
        "language": html_nodes[0].attrs.get("lang") if html_nodes else None,
        "baseUrl": base,
        "metadata": {key: sorted(values) for key, values in sorted(metadata.items())},
        "pageH1": [spaced(text_content(n)) for n in nodes if n.tag == "h1"],
        "article": semantic_node(targets[0], base),
        "jsonLd": sorted(structured, key=encoded),
    }


def crawler_directives(semantic):
    return [
        value for name, values in semantic["metadata"].items()
        if name in CRAWLER_META for value in values
    ]


def has_noindex(value):
    return re.search(r"\b(?:noindex|none)\b", value, re.IGNORECASE) is not None


def policy_errors(semantic, indexing, header_values=()):
    errors = []
    values = crawler_directives(semantic) + list(header_values)
    if any("unavailable_after" in value.lower() for value in values):
        errors.append("Timed unavailable_after directives require a separate crawler-aware evaluation")
    if indexing == "index" and any(has_noindex(value) for value in values):
        errors.append("Indexing intended, but HTML or HTTP crawler directives include noindex/none")
    if indexing == "noindex":
        # A crawler-specific instruction alone does not keep every crawler out.
        general = semantic["metadata"].get("robots", []) + [
            value for value in header_values if ":" not in value.split(",", 1)[0]
        ]
        if not any(has_noindex(value) for value in general):
            errors.append("General noindex intended, but no general noindex/none directive was supplied")
    return errors


def load_headers(path):
    raw = strict_json(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Headers must be a JSON object of strings or string arrays")
    result = {}
    for name, values in raw.items():
        if isinstance(values, str):
            values = [values]
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise ValueError("Header values must be strings or string arrays")
        result.setdefault(name.lower(), []).extend(values)
    return result


def differences(expected, observed, path="", result=None):
    if result is None:
        result = []
    if len(result) >= 50:
        return result
    if type(expected) is not type(observed):
        result.append({"path": path or "/", "reason": "different value types"})
    elif isinstance(expected, dict):
        for key in sorted(expected.keys() | observed.keys()):
            child_path = path + "/" + str(key).replace("~", "~0").replace("/", "~1")
            if key not in expected or key not in observed:
                result.append({"path": child_path, "reason": "missing or additional field"})
            else:
                differences(expected[key], observed[key], child_path, result)
    elif isinstance(expected, list):
        if len(expected) != len(observed):
            result.append({"path": path, "reason": "different item counts"})
        for index, (left, right) in enumerate(zip(expected, observed)):
            differences(left, right, path + "/" + str(index), result)
    elif expected != observed:
        result.append({"path": path or "/", "reason": "different values"})
    return result[:50]


def write_json(path, value):
    target = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, prefix=target.name + ".", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def snapshot(args):
    location = valid_url(args.url)
    selector = {"id": args.article_id} if args.article_id else {"tag": args.article_tag or "article"}
    source_bytes = Path(args.html).read_bytes()
    source = source_bytes.decode("utf-8")
    semantic = document_semantics(source, location, selector)
    if semantic["canonical"] != location:
        raise ValueError("Expected canonical URL does not match the supplied production URL")
    errors = policy_errors(semantic, args.indexing)
    if errors:
        raise ValueError("; ".join(errors))
    manifest = {
        "schemaVersion": 1,
        "profile": {"url": location, "indexing": args.indexing, "selector": selector},
        "sourceSha256": digest(source_bytes),
        "semanticSha256": digest(encoded(semantic).encode()),
        "semantic": semantic,
    }
    write_json(args.out, manifest)
    print(json.dumps({"status": "snapshot-created", "manifestSha256": digest(Path(args.out).read_bytes()), "liveCheck": "not-performed"}))
    return 0


def verify(args):
    expected_bytes = Path(args.expected).read_bytes()
    expected = strict_json(expected_bytes.decode("utf-8"))
    if expected.get("schemaVersion") != 1:
        raise ValueError("Unsupported expected-manifest schemaVersion")
    if digest(encoded(expected["semantic"]).encode()) != expected["semanticSha256"]:
        raise ValueError("Expected manifest semantic hash is invalid")
    profile = expected["profile"]
    if profile["indexing"] not in {"index", "noindex"}:
        raise ValueError("Unknown expected indexing policy")
    location = valid_url(args.url)
    source_bytes = Path(args.html).read_bytes()
    source = source_bytes.decode("utf-8")
    observed = document_semantics(source, location, profile["selector"])
    headers = load_headers(args.headers)
    errors = []
    if args.status != 200:
        errors.append("Observed HTTP status is not 200")
    if not any(value.lower().split(";", 1)[0].strip() == "text/html" for value in headers.get("content-type", [])):
        errors.append("Observed response does not have text/html content type")
    if location != profile["url"]:
        errors.append("Observed final URL differs from the approved URL")
    if observed["canonical"] != profile["url"]:
        errors.append("Observed canonical differs from the approved URL")
    errors.extend(policy_errors(observed, profile["indexing"], headers.get("x-robots-tag", [])))
    changes = differences(expected["semantic"], observed)
    receipt = {
        "status": "matched" if not errors and not changes else "blocked",
        "comparedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "supplied-artifacts-only",
        "expectedManifestSha256": digest(expected_bytes),
        "observedHtmlSha256": digest(source_bytes),
        "observedHeadersSha256": digest(encoded(headers).encode()),
        "observedSemanticSha256": digest(encoded(observed).encode()),
        "observedUrl": location,
        "observedStatus": args.status,
        "errors": errors,
        "differences": changes,
        "deploymentCheck": "not-performed",
        "browserCheck": "not-performed",
        "robotsAndSitemapCheck": "not-performed",
    }
    if args.out:
        write_json(args.out, receipt)
    print(json.dumps(receipt, ensure_ascii=False))
    return 0 if receipt["status"] == "matched" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("snapshot", help="Create an expected semantic manifest; no live check")
    create.add_argument("html")
    create.add_argument("--url", required=True)
    create.add_argument("--indexing", choices=("index", "noindex"), required=True)
    selector = create.add_mutually_exclusive_group()
    selector.add_argument("--article-id")
    selector.add_argument("--article-tag")
    create.add_argument("--out", required=True)
    check = commands.add_parser("verify", help="Compare supplied live HTML/status/headers with a reviewed manifest")
    check.add_argument("expected")
    check.add_argument("html")
    check.add_argument("--url", required=True)
    check.add_argument("--status", type=int, required=True)
    check.add_argument("--headers", required=True)
    check.add_argument("--out")
    args = parser.parse_args()
    try:
        return snapshot(args) if args.command == "snapshot" else verify(args)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        # Overwrite a requested receipt on an unperformed comparison; do not leave
        # yesterday's success at today's output path.
        receipt = {"status": "not-performed", "error": str(error), "scope": "supplied-artifacts-only"}
        if args.out:
            try:
                write_json(args.out, receipt)
            except OSError:
                pass
        print(json.dumps(receipt), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
