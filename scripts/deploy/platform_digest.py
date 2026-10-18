"""Resolve the linux/amd64 manifest digest behind a pushed image's manifest index.

`docker push` can publish an image *index*: a multi-platform push, or a single-platform build
with provenance attestations. Artifact Registry then reports the index's digest for the tag,
while Cloud Run records the digest of the platform manifest it runs — two different digests for
the same push (orchestrator evidence, 2026-10-14: `sha256:572c87ba…` on revision
`grid-nowcast-00005-kxh` against `sha256:2b054bde…` for the tag). `deploy.sh` pipes
`docker buildx imagetools inspect --raw REF` into this module and compares the revision against
what it prints: the index's linux/amd64 manifest digest, which is the digest Cloud Run records.

A push that is a *plain* manifest prints nothing and exits 0 — its own digest is already the
platform one, and the caller keeps the digest the registry reported. An *index* that lists no
linux/amd64 manifest, or lists one without a usable digest, is a different thing and exits 1
with what it read: the platform identity of the pushed image is then unknown, and answering
empty would let the caller substitute the index digest for a digest Cloud Run was never asked
to run (review finding, 2026-10-14). The selection is by the entry's `platform`, never by
position: an index lists its attestation manifest alongside the platform one, in no promised
order.

No network call, credential or SDK: the manifest arrives on stdin, and anything that is not a
JSON object is refused on stderr with exit 1, so the caller fails closed rather than comparing
against a guess.
"""
import json
import sys

PLATFORM = {'os': 'linux', 'architecture': 'amd64'}
# What an index names itself: the Docker manifest list and the OCI image index. An object that
# does not carry one of these still counts as an index when it carries a `manifests` list.
INDEX_MEDIA_TYPES = frozenset((
    'application/vnd.docker.distribution.manifest.list.v2+json',
    'application/vnd.oci.image.index.v1+json',
))


def is_index(manifest):
    """Whether the manifest is an image index rather than the plain manifest of one image."""
    return manifest.get('mediaType') in INDEX_MEDIA_TYPES or 'manifests' in manifest


def entry_platform(entry):
    """The `os/architecture` an index entry states, with an absent half named unknown."""
    platform = entry.get('platform') or {}
    return '%s/%s' % (platform.get('os') or 'unknown',
                      platform.get('architecture') or 'unknown')


def is_digest(value):
    """Whether a value can be a manifest digest: `sha256:` and a non-empty tail."""
    return (isinstance(value, str) and value.startswith('sha256:')
            and len(value) > len('sha256:'))


def platform_digest(manifest):
    """The digest of the linux/amd64 manifest of an image index, or '' when there is none."""
    entries = manifest.get('manifests')
    if not isinstance(entries, list):
        return ''
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry_platform(entry) != '%s/%s' % (PLATFORM['os'], PLATFORM['architecture']):
            continue
        digest = entry.get('digest')
        if is_digest(digest):
            return digest
    return ''


def describe(manifest):
    """The index's entries as `os/architecture`, so the refusal below names what it read."""
    entries = manifest.get('manifests')
    if not isinstance(entries, list):
        return 'not a list'
    if not entries:
        return 'none'
    described = []
    for entry in entries:
        if not isinstance(entry, dict):
            described.append('not an entry')
        elif is_digest(entry.get('digest')):
            described.append(entry_platform(entry))
        else:
            described.append('%s without a digest' % entry_platform(entry))
    return ', '.join(described)


def main(stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    text = stdin.read()
    try:
        manifest = json.loads(text or 'null')
    except ValueError as error:
        print('not a manifest: %s' % error, file=stderr)
        return 1
    if not isinstance(manifest, dict):
        print('not a manifest: expected a JSON object, got %s' % type(manifest).__name__, file=stderr)
        return 1
    if not is_index(manifest):
        # A plain manifest: its own digest is already the platform manifest digest.
        return 0
    digest = platform_digest(manifest)
    if digest:
        print(digest, file=stdout)
        return 0
    print('no linux/amd64 manifest digest in the image index (manifests: %s)' % describe(manifest),
          file=stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
