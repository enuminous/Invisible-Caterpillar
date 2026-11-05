#!/usr/bin/env python3
"""Offline, report-only validation of the existing SoundCloud catalog schema.

Only the Python standard library is required. Source metadata is never repaired.
Exit 0 means reports were produced, not that the catalog is complete or licensed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime
import hashlib
import html
import json
from pathlib import Path
import re
import sys

VERSION = "1.0.0"
OWNER_ID = 7380079  # enuminous SoundCloud account; uploader identity, not rights ownership.
SECTIONS = ("tracks", "reference_tracks", "collections")
TRACK_FIELDS = (
    "id", "title", "artist", "uploader", "uploader_id", "url", "duration_ms",
    "genre", "uploaded_at", "release_date", "isrc", "composer", "publisher",
    "label", "license", "tags", "plays", "likes", "album_ids",
)
COLLECTION_FIELDS = (
    "id", "title", "type", "genre", "url", "uploaded_at", "release_date",
    "original_release_date", "date", "date_kind", "duration_ms", "track_count",
    "track_ids", "credits", "cover", "artwork_source", "artwork_source_url",
    "literary_note", "source_description",
)
CHECKS = {
    "schema": "Object/list shape, field types, titles and source URLs",
    "identity": "Positive integer IDs and duplicate identities across source sections",
    "uploader_scope": "enuminous uploads versus other uploaders by numeric account ID",
    "isrc": "Missing ISRC, syntax, presentation and potential cross-record inconsistencies",
    "credits": "Artist/composer information and collection credits",
    "rights": "Available license, publisher and label metadata (not ownership verification)",
    "membership": "Resolvable collection references and reciprocal album membership",
    "ordering": "Ordered track ID arrays, entry counts and repeated entries",
    "dates": "Date syntax, release-date gaps and display-date provenance",
    "duration": "Nonnegative durations, upload totals and collection duration discrepancies",
    "engagement": "Missing/invalid counters, low plays and likes exceeding plays",
}
LIMITATIONS = [
    "Only supplied JSON is inspected; no live SoundCloud rescan, audio analysis or registry lookup.",
    "Missing_source means absent, null or empty in this export; the original platform may have more information.",
    "Verified_error means a schema/format violation or internal contradiction, not a verified fact about a recording.",
    "Review findings are heuristics or discrepancies; low plays, repeated entries and shared ISRCs can be legitimate.",
    "ISRC syntax does not verify assignment. SoundCloud track IDs identify uploads, not necessarily unique masters or compositions.",
    "Collection order is the supplied track_ids array (positions start at 1); actual SoundCloud order is not independently verified.",
    "Artists, composers and uploader names are separate roles. Missing artists are never replaced with the uploader.",
    "The snapshot has no dedicated performer/producer, master-owner, permission, contract or clearance fields. Free text is not treated as verified evidence.",
    "Catalog inclusion, ISRCs, uploader identity and SoundCloud rights settings do not independently establish ownership or grant licensing rights.",
    "No source fields are changed, guessed or filled. Report completion and CI success do not certify catalog completeness or rights.",
]
ABSENT = object()


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def state(row, field):
    if field not in row:
        return {"state": "absent"}
    value = row[field]
    if value is None:
        return {"state": "null", "value": None}
    if (isinstance(value, str) and not value.strip()) or value == []:
        return {"state": "empty", "value": value}
    return {"state": "present", "value": value}


def missing(row, field):
    return state(row, field)["state"] != "present"


def iso_date(value):
    """Accept YYYY-MM-DD or ISO datetime with explicit UTC/offset timezone."""
    if not isinstance(value, str):
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return date.fromisoformat(value)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def normalized_isrc(value):
    """Normalize for comparison only; never write normalized values to the source."""
    if not isinstance(value, str):
        return None
    value = re.sub(r"^ISRC\s+", "", value.strip(), flags=re.I)
    value = re.sub(r"[\s-]", "", value).upper()
    return value if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{3}[0-9]{7}", value) else None


def scope(row):
    uid = row.get("uploader_id")
    if not integer(uid, 1):
        return "unknown_uploader"
    return "enuminous_upload" if uid == OWNER_ID else "other_uploader"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def json_text(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def load_json(path):
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"Nonstandard JSON constant: {value}")

    raw = Path(path).read_bytes()
    return json.loads(raw.decode("utf-8"), object_pairs_hook=object_pairs,
                      parse_constant=reject_constant), sha256(raw)


class Validator:
    def __init__(self, low_plays=10):
        if not integer(low_plays):
            raise ValueError("low_plays must be a nonnegative integer")
        self.low_plays = low_plays
        self.findings = []
        self.examined = Counter()
        self.skipped = Counter()
        self.entities = {}

    def add(self, check, code, category, entity, field, evidence, message):
        key = [check, code, entity, field, evidence]
        self.findings.append({
            "finding_id": sha256(json_text(key).encode())[:20],
            "check": check, "code": code, "category": category,
            "entity": entity, "field": field, "evidence": evidence, "message": message,
        })

    def require(self, row, field, check, entity):
        if missing(row, field):
            self.add(check, "missing_source", "missing_source", entity, field,
                     state(row, field), "Source field is absent, null or empty; no replacement inferred.")
            return False
        return True

    def typed(self, row, field, kind, entity):
        # Absent/null/empty source values are unknown, not verified type errors.
        if missing(row, field):
            return
        value = row[field]
        valid = type(value) is kind
        if not valid:
            self.add("schema", "invalid_type", "verified_error", entity, field,
                     {"expected": kind.__name__, **state(row, field)}, "Value has an incompatible JSON type.")

    def validate(self, data):
        self.examined["schema"] += 1
        if not isinstance(data, dict):
            self.add("schema", "invalid_root", "verified_error", "catalog", "",
                     {"type": type(data).__name__}, "Catalog root must be an object.")
            data = {}
        records = {s: [] for s in SECTIONS}
        for section in SECTIONS:
            rows = data.get(section, ABSENT)
            if rows is ABSENT:
                self.require(data, section, "schema", "catalog")
                continue
            if not isinstance(rows, list):
                self.add("schema", "invalid_section", "verified_error", "catalog", section,
                         state(data, section), "Catalog section must be an array.")
                continue
            for i, row in enumerate(rows):
                self.examined["schema"] += 1
                pointer = f"/{section}/{i}"
                if not isinstance(row, dict):
                    self.add("schema", "invalid_record", "verified_error", pointer, "",
                             {"type": type(row).__name__}, "Record must be an object.")
                    continue
                entity = f"{section}:{row.get('id')}" if integer(row.get("id"), 1) else pointer
                # A duplicate retains its own evidence location rather than overwriting another record.
                if entity in self.entities:
                    entity += f"@{i}"
                self.entities[entity] = {"id": row.get("id"), "title": row.get("title"),
                                         "section": section, "pointer": pointer, "url": row.get("url")}
                if section != "collections":
                    self.entities[entity].update(uploader_scope=scope(row), uploader_id=row.get("uploader_id"),
                                                 uploader=row.get("uploader"))
                records[section].append((entity, row))
                fields = COLLECTION_FIELDS if section == "collections" else TRACK_FIELDS
                ints = {"id", "uploader_id", "duration_ms", "plays", "likes", "track_count"}
                lists = {"track_ids", "album_ids", "credits"}
                for field in fields:
                    self.typed(row, field, int if field in ints else list if field in lists else str,
                               entity)
                for field in ("title", "url"):
                    self.require(row, field, "schema", entity)
                if not missing(row, "url") and isinstance(row["url"], str):
                    if not re.fullmatch(r"https?://[^\s/]+/[^\s]*", row["url"]):
                        self.add("schema", "invalid_url", "verified_error", entity, "url",
                                 state(row, "url"), "Source URL must be an absolute HTTP(S) URL.")
                if section == "collections":
                    if self.require(row, "type", "schema", entity) and row["type"] not in ("album", "playlist"):
                        self.add("schema", "unknown_collection_type", "review", entity, "type",
                                 state(row, "type"), "Unrecognized collection type; album-specific checks may not apply.")

        tracks = records["tracks"] + records["reference_tracks"]
        collections = records["collections"]
        track_index = self.identity(tracks)
        collection_index = self.identity(collections)
        self.dates("catalog", data, ("snapshot_date",), data.get("snapshot_date"))
        isrc_groups = defaultdict(list)
        signature_groups = defaultdict(list)
        for entity, row in tracks:
            for check in ("uploader_scope", "isrc", "credits", "rights", "engagement", "duration"):
                self.examined[check] += 1
            for field in ("uploader_id", "uploader"):
                self.require(row, field, "uploader_scope", entity)
            uid = row.get("uploader_id")
            if not missing(row, "uploader_id") and not integer(uid, 1):
                self.add("uploader_scope", "invalid_uploader_id", "verified_error", entity, "uploader_id",
                         state(row, "uploader_id"), "Uploader ID must be a positive integer.")
            expected = "enuminous_upload" if entity.startswith("tracks:") or entity.startswith("/tracks/") else "other_uploader"
            if scope(row) != "unknown_uploader" and scope(row) != expected:
                self.add("uploader_scope", "uploader_section_conflict", "verified_error", entity, "uploader_id",
                         {"actual_scope": scope(row), "expected_scope": expected, "uploader_id": uid},
                         "Numeric uploader ID conflicts with the source section; rights ownership remains unknown.")
            for field in ("artist", "composer"):
                self.require(row, field, "credits", entity)
            for field in ("license", "publisher", "label"):
                self.require(row, field, "rights", entity)
            if self.require(row, "isrc", "isrc", entity):
                code = normalized_isrc(row["isrc"])
                if not code:
                    self.add("isrc", "invalid_isrc", "verified_error", entity, "isrc", state(row, "isrc"),
                             "Does not match the ISRC structure after presentation-only normalization.")
                else:
                    isrc_groups[code].append((entity, row))
                    if row["isrc"] != code:
                        self.add("isrc", "isrc_presentation", "review", entity, "isrc",
                                 {"raw": row["isrc"], "comparison_form": code}, "Noncanonical presentation; source value is retained.")
                    if all(isinstance(row.get(k), str) and row[k].strip() for k in ("title", "artist")) and integer(row.get("duration_ms")):
                        sig = (row["title"].strip().casefold(), row["artist"].strip().casefold(), row["duration_ms"])
                        signature_groups[sig].append((entity, code))
            self.dates(entity, row, ("uploaded_at", "release_date"), data.get("snapshot_date"))
            self.nonnegative(row, "duration_ms", "duration", entity)
            for field in ("plays", "likes"):
                self.nonnegative(row, field, "engagement", entity)
            plays, likes = row.get("plays"), row.get("likes")
            if integer(plays) and plays < self.low_plays:
                self.add("engagement", "low_plays", "review", entity, "plays",
                         {"plays": plays, "threshold_exclusive": self.low_plays},
                         "Below the configured review threshold; low play counts may be accurate.")
            if integer(plays) and integer(likes) and likes > plays:
                self.add("engagement", "likes_exceed_plays", "review", entity, "likes",
                         {"plays": plays, "likes": likes}, "Counter discrepancy for review; platform counters need not be synchronized.")
        for code, group in sorted(isrc_groups.items()):
            if len(group) > 1:
                self.add("isrc", "shared_isrc", "review", "catalog", "isrc",
                         {"isrc": code, "entities": [e for e, _ in group],
                          "metadata": [{k: r.get(k) for k in ("title", "artist", "duration_ms")} for _, r in group]},
                         "Multiple uploads share an ISRC; confirm whether they contain the same recording before treating this as an error.")
                for check, fields in (("rights", ("license", "publisher", "label")),
                                      ("credits", ("artist", "composer"))):
                    for field in fields:
                        supplied = [(e, r[field]) for e, r in group if isinstance(r.get(field), str) and r[field].strip()]
                        if len({v.strip().casefold() for _, v in supplied}) > 1:
                            self.add(check, "shared_isrc_metadata_conflict", "review", "catalog", field,
                                     {"isrc": code, "entities_and_values": supplied},
                                     "Uploads sharing an ISRC have differing metadata; versions, credits or territory-specific rights may explain it.")
        for sig, group in sorted(signature_groups.items()):
            if len({code for _, code in group}) > 1:
                self.add("isrc", "potential_isrc_conflict", "review", "catalog", "isrc",
                         {"title_artist_duration": list(sig), "entities_and_isrcs": group},
                         "Matching title, artist and exact duration have different ISRCs; audio identity is unverified.")

        memberships = defaultdict(list)
        incomplete_membership = (not isinstance(data.get("collections"), list)
                                 or len(collections) != len(data["collections"])
                                 or len(collection_index) != len(collections))
        for entity, row in collections:
            self.examined["credits"] += 1
            self.require(row, "credits", "credits", entity)
            if isinstance(row.get("credits"), list):
                for pos, credit in enumerate(row["credits"]):
                    if not isinstance(credit, str) or not credit.strip():
                        self.add("credits", "invalid_credit", "verified_error", entity, f"credits/{pos}",
                                 {"value": credit}, "Each supplied collection credit must be a nonempty string.")
            self.dates(entity, row, ("uploaded_at", "release_date", "original_release_date", "date"), data.get("snapshot_date"))
            self.collection_date(entity, row)
            self.examined["ordering"] += 1
            self.examined["membership"] += 1
            ids = self.id_list(entity, row, "track_ids", "ordering")
            if ids is None:
                incomplete_membership = True
            self.nonnegative(row, "track_count", "ordering", entity)
            self.examined["duration"] += 1
            self.nonnegative(row, "duration_ms", "duration", entity)
            if ids is None:
                self.skipped["membership"] += 1
                self.skipped["duration"] += 1
                continue
            if integer(row.get("track_count")) and row["track_count"] != len(ids):
                self.add("ordering", "entry_count_mismatch", "verified_error", entity, "track_count",
                         {"declared": row["track_count"], "ordered_entries": len(ids)}, "Declared entry count differs from the ordered array length.")
            duplicates = sorted(k for k, n in Counter(ids).items() if n > 1)
            if duplicates:
                self.add("ordering", "repeated_entry", "review", entity, "track_ids",
                         {"track_ids": duplicates}, "Repeated entries may be intentional; order and multiplicity are preserved.")
            resolved = True
            for pos, tid in enumerate(ids, 1):
                memberships[tid].append({"collection_id": row.get("id"), "collection_entity": entity,
                                          "type": row.get("type"), "position": pos})
                if tid not in track_index:
                    resolved = False
                    self.add("membership", "unresolved_track_reference", "verified_error", entity, "track_ids",
                             {"track_id": tid, "position": pos}, "Collection entry does not resolve to exactly one supplied track.")
            if resolved and all(integer(track_index[i][1].get("duration_ms")) for i in ids) and integer(row.get("duration_ms")):
                total = sum(track_index[i][1]["duration_ms"] for i in ids)
                if total != row["duration_ms"]:
                    self.add("duration", "collection_duration_discrepancy", "review", entity, "duration_ms",
                             {"declared_ms": row["duration_ms"], "sum_of_entries_ms": total,
                              "difference_ms": row["duration_ms"] - total},
                             "Collection duration differs from the sum of listed tracks; rounding, source timing or unavailable entries may explain it.")
            else:
                self.skipped["duration"] += 1

        for entity, row in tracks:
            self.examined["membership"] += 1
            ids = self.id_list(entity, row, "album_ids", "membership")
            tid = row.get("id")
            if not integer(tid, 1) or tid not in track_index:
                self.skipped["membership"] += 1
                continue
            actual = memberships.get(tid, [])
            self.entities[entity]["collection_memberships"] = actual
            if not actual and not incomplete_membership:
                self.add("membership", "no_collection", "review", entity, "album_ids", {"memberships": []},
                         "No listed collection contains this upload; it may be a standalone recording.")
            if ids is None:
                self.skipped["membership"] += 1
                continue
            expected = {m["collection_id"] for m in actual if m["type"] == "album" and integer(m["collection_id"], 1)}
            for aid in ids:
                target = collection_index.get(aid)
                if not target or target[1].get("type") != "album":
                    self.add("membership", "invalid_album_reference", "verified_error", entity, "album_ids",
                             {"album_id": aid}, "Album reference does not resolve to exactly one supplied album.")
            if not incomplete_membership and set(ids) != expected:
                self.add("membership", "album_membership_mismatch", "verified_error", entity, "album_ids",
                         {"declared": ids, "from_collection_lists": sorted(expected)}, "Track and album lists disagree about membership.")
            elif incomplete_membership:
                self.skipped["membership"] += 1
            if len(ids) != len(set(ids)):
                self.add("membership", "duplicate_album_reference", "verified_error", entity, "album_ids",
                         {"album_ids": ids}, "Album membership contains duplicate identifiers.")

        return self.finish(data, records, isrc_groups)

    def identity(self, records):
        groups = defaultdict(list)
        for entity, row in records:
            self.examined["identity"] += 1
            if not self.require(row, "id", "identity", entity):
                continue
            if not integer(row["id"], 1):
                self.add("identity", "invalid_id", "verified_error", entity, "id", state(row, "id"), "ID must be a positive integer.")
            else:
                groups[row["id"]].append((entity, row))
        for key, group in sorted(groups.items()):
            if len(group) > 1:
                self.add("identity", "duplicate_id", "verified_error", "catalog", "id",
                         {"id": key, "entities": [e for e, _ in group]}, "Identity is ambiguous; dependent joins and diffs must not guess.")
        return {key: group[0] for key, group in groups.items() if len(group) == 1}

    def nonnegative(self, row, field, check, entity):
        if self.require(row, field, check, entity) and not integer(row[field]):
            self.add(check, "invalid_nonnegative_integer", "verified_error", entity, field,
                     state(row, field), "Counter or duration must be a nonnegative integer (booleans are not integers).")

    def id_list(self, entity, row, field, check):
        # Empty membership arrays are valid, unlike unavailable/null fields.
        if missing(row, field) and not isinstance(row.get(field), list):
            self.require(row, field, check, entity)
            return None
        values = row[field]
        if not isinstance(values, list):
            return None  # Type violation already recorded by schema check.
        if any(not integer(v, 1) for v in values):
            self.add(check, "invalid_reference_ids", "verified_error", entity, field,
                     {"values": values}, "Reference array must contain positive integer IDs.")
            return None
        return values

    def dates(self, entity, row, fields, snapshot):
        self.examined["dates"] += 1
        snapshot_day = iso_date(snapshot)
        for field in fields:
            # Historical original-release metadata is optional, not universally required.
            if field == "original_release_date" and missing(row, field):
                continue
            if not self.require(row, field, "dates", entity):
                continue
            parsed = iso_date(row[field])
            if parsed is None:
                self.add("dates", "invalid_date", "verified_error", entity, field, state(row, field),
                         "Expected a real YYYY-MM-DD date or ISO timestamp with timezone.")
            elif snapshot_day and parsed > snapshot_day and field != "snapshot_date":
                self.add("dates", "date_after_snapshot", "review", entity, field,
                         {"value": row[field], "snapshot_date": snapshot}, "Date follows the snapshot; a future scheduled release may be intentional.")

    def collection_date(self, entity, row):
        source, label = "uploaded_at", "SoundCloud upload"
        if not missing(row, "original_release_date"):
            source, label = "original_release_date", "Original release (album notes)"
            if missing(row, "source_description"):
                self.add("dates", "original_date_evidence_missing", "missing_source", entity, "source_description",
                         state(row, "source_description"), "Original release is labeled as coming from album notes, but notes are unavailable.")
        elif not missing(row, "release_date"):
            source, label = "release_date", "Release date"
        expected = iso_date(row.get(source))
        shown = iso_date(row.get("date"))
        if expected and shown and expected != shown:
            self.add("dates", "display_date_mismatch", "verified_error", entity, "date",
                     {"display_date": row.get("date"), "source_field": source, "source_value": row.get(source)},
                     "Displayed date disagrees with its preferred source field.")
        if self.require(row, "date_kind", "dates", entity) and row["date_kind"] != label:
            self.add("dates", "date_kind_mismatch", "verified_error", entity, "date_kind",
                     {"actual": row["date_kind"], "expected": label}, "Date label disagrees with the available preferred date source.")

    def finish(self, data, records, isrc_groups):
        counts = Counter(f["category"] for f in self.findings)
        checks = []
        for key, description in CHECKS.items():
            n = sum(f["check"] == key for f in self.findings)
            checks.append({"id": key, "description": description, "execution": "completed",
                           "records_examined": self.examined[key], "dependent_operations_skipped": self.skipped[key],
                           "finding_count": n, "outcome": "findings" if n else "not_applicable" if not self.examined[key] else "no_findings"})
        coverage = {}
        for section, rows in records.items():
            fields = set(COLLECTION_FIELDS if section == "collections" else TRACK_FIELDS)
            fields.update(k for _, r in rows for k in r)
            coverage[section] = {field: dict(sorted(Counter(state(r, field)["state"] for _, r in rows).items())) for field in sorted(fields)}
        upload_rows = [r for _, r in records["tracks"] if scope(r) == "enuminous_upload"]
        total_ms = sum(r["duration_ms"] for r in upload_rows if integer(r.get("duration_ms")))
        self.findings.sort(key=lambda f: (f["category"], f["check"], f["code"], f["entity"], f["field"], f["finding_id"]))
        return {
            "report_version": 1, "validator_version": VERSION, "execution": "completed",
            "policy": {"report_only": True, "enuminous_uploader_id": OWNER_ID, "low_plays_threshold_exclusive": self.low_plays},
            "snapshot_date": data.get("snapshot_date"), "limitations": LIMITATIONS,
            "summary": {"source_section_counts": {s: len(r) for s, r in records.items()},
                        "albums": sum(r.get("type") == "album" for _, r in records["collections"]),
                        "other_playlists": sum(r.get("type") == "playlist" for _, r in records["collections"]),
                        "ordered_entries": sum(len(r["track_ids"]) for _, r in records["collections"] if isinstance(r.get("track_ids"), list)),
                        "uploader_scopes": dict(sorted(Counter(scope(r) for _, r in records["tracks"] + records["reference_tracks"]).items())),
                        "enuminous_duration_ms": total_ms, "enuminous_duration_hours": round(total_ms / 3600000, 8),
                        "duration_records_included": sum(integer(r.get("duration_ms")) for r in upload_rows),
                        "validly_formed_distinct_isrcs": len(isrc_groups),
                        "findings_by_category": {k: counts[k] for k in ("verified_error", "missing_source", "review")},
                        "total_findings": len(self.findings)},
            "checks": checks, "field_coverage": coverage, "entities": self.entities, "findings": self.findings,
        }


def validate(data, low_plays=10):
    return Validator(low_plays).validate(data)


def comparison_index(data, sections):
    groups, unresolved = defaultdict(list), []
    if not isinstance(data, dict):
        return {}, [{"reason": "root_not_object"}], True
    structural = False
    for section in sections:
        rows = data.get(section)
        if not isinstance(rows, list):
            unresolved.append({"section": section, "reason": "section_missing_or_not_array"})
            structural = True
            continue
        for i, row in enumerate(rows):
            if not isinstance(row, dict) or not integer(row.get("id"), 1):
                unresolved.append({"section": section, "index": i, "reason": "record_missing_valid_id"})
                continue
            groups[row["id"]].append({"source_section": section, "record": row})
    for key, group in groups.items():
        if len(group) > 1:
            unresolved.append({"id": key, "reason": "duplicate_id", "records": group})
    return {k: v[0] for k, v in groups.items() if len(v) == 1}, unresolved, structural


def field_changes(before, after, prefix=""):
    changes = []
    for key in sorted(set(before) | set(after)):
        b, a = before.get(key, ABSENT), after.get(key, ABSENT)
        field = f"{prefix}/{key.replace('~', '~0').replace('/', '~1')}"
        if isinstance(b, dict) and isinstance(a, dict):
            changes.extend(field_changes(b, a, field))
        elif b is ABSENT or a is ABSENT or type(b) is not type(a) or b != a:
            changes.append({"field": field, "before": state(before, key), "after": state(after, key)})
    return changes


def order_change(before, after):
    if not (isinstance(before, list) and isinstance(after, list) and all(integer(i, 1) for i in before + after)):
        return {"status": "unresolved", "reason": "track_ids is missing or malformed"}
    b, a = Counter(before), Counter(after)
    def occurrences(ids):
        seen, result = Counter(), []
        for key in ids:
            seen[key] += 1
            result.append((key, seen[key]))
        return result
    bo, ao = occurrences(before), occurrences(after)
    shared = set(bo) & set(ao)
    return {"status": "compared", "before": before, "after": after,
            "added_occurrences": [{"track_id": k, "count": v} for k, v in sorted((a - b).items())],
            "removed_occurrences": [{"track_id": k, "count": v} for k, v in sorted((b - a).items())],
            "retained_relative_order_changed": [x for x in bo if x in shared] != [x for x in ao if x in shared]}


def compare(before, after):
    result = {"report_version": 1, "validator_version": VERSION, "execution": "completed",
              "interpretation": "Changes describe supplied snapshots, not verified corrections. Missing, null and empty values remain distinct.",
              "root_changes": field_changes({k: v for k, v in before.items() if k not in SECTIONS} if isinstance(before, dict) else {},
                                            {k: v for k, v in after.items() if k not in SECTIONS} if isinstance(after, dict) else {})}
    for name, sections in (("tracks", ("tracks", "reference_tracks")), ("collections", ("collections",))):
        b, bu, bs = comparison_index(before, sections)
        a, au, ass = comparison_index(after, sections)
        blocked = {x["id"] for x in bu + au if "id" in x}
        for key in blocked:
            b.pop(key, None)
            a.pop(key, None)
        changes = []
        for key in sorted(set(a) & set(b)):
            fields = field_changes(b[key], a[key])
            if fields:
                entry = {"id": key, "changes": fields}
                if name == "collections" and any(f["field"] == "/record/track_ids" for f in fields):
                    entry["membership_and_order"] = order_change(b[key]["record"].get("track_ids"), a[key]["record"].get("track_ids"))
                changes.append(entry)
        # A malformed section cannot establish additions or removals in that entity domain.
        result[name] = {"added": [] if bs or ass else [a[k] for k in sorted(set(a) - set(b))],
                        "removed": [] if bs or ass else [b[k] for k in sorted(set(b) - set(a))],
                        "changed": changes, "unresolved_before": bu, "unresolved_after": au,
                        "presence_comparison": "unresolved" if bs or ass else "completed_for_unambiguous_ids"}
        if bu or au:
            result["execution"] = "completed_with_unresolved_identities"
    result["summary"] = {f"{name}_{kind}": len(result[name][kind]) for name in ("tracks", "collections") for kind in ("added", "removed", "changed")}
    result["summary"]["root_fields_changed"] = len(result["root_changes"])
    return result


def md(value):
    # Do not let source text create HTML, links, table cells or new report headings.
    value = html.escape(str(value), quote=False).replace("\n", " ").replace("\r", " ")
    return re.sub(r"([\\`*_[\]{}()#|])", r"\\\1", value)


def render_report(report, full=True):
    s = report["summary"]
    lines = ["# Catalog completeness report", "", f"Snapshot: {md(report['snapshot_date'])}. Validator: {VERSION}. Execution: completed.", "",
             "**Report-only. Successful execution is not a completeness or licensing certificate.**", "",
             f"Uploads: {s['source_section_counts']['tracks']}; other-uploader reference section: {s['source_section_counts']['reference_tracks']}; "
             f"albums: {s['albums']}; other playlists: {s['other_playlists']}; ordered entries: {s['ordered_entries']}.", "",
             f"enuminous upload duration: {s['enuminous_duration_hours']:.8f} hours ({s['duration_records_included']} records).", "",
             "| Finding category | Count |", "| --- | ---: |"]
    lines += [f"| {k} | {v} |" for k, v in s["findings_by_category"].items()]
    lines += ["", "## Checks executed", "", "Counts are records examined, not individual assertions. Skips are dependent operations whose inputs were unavailable or ambiguous.", "",
              "| Check | Records | Skipped operations | Findings | Outcome |", "| --- | ---: | ---: | ---: | --- |"]
    lines += [f"| {c['id']} — {c['description']} | {c['records_examined']} | {c['dependent_operations_skipped']} | {c['finding_count']} | {c['outcome']} |" for c in report["checks"]]
    lines += ["", "## Finding meanings", "", "Counts below are field-level findings, not counts of distinct recordings.", "",
              "| Category / code | Count | Interpretation |", "| --- | ---: | --- |"]
    codes = Counter((f["category"], f["code"], f["message"]) for f in report["findings"])
    lines += [f"| {md(category)} / {md(code)} | {count} | {md(message)} |"
              for (category, code, message), count in sorted(codes.items())]
    lines += ["", "## Interpretation and limits", ""] + [f"- {text}" for text in LIMITATIONS]
    lines += ["", "## Source-field coverage", "", "An absent key differs from an explicit null or empty value. All source fields and per-entity findings are in validation.json.", "",
              "| Section | Field | Absent | Null | Empty | Present |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for section, fields in report["field_coverage"].items():
        for field, counts in fields.items():
            lines.append(f"| {section} | {field} | " + " | ".join(str(counts.get(k, 0)) for k in ("absent", "null", "empty", "present")) + " |")
    if "provenance" in report:
        lines += ["", "## Provenance", "", "```json", json_text(report["provenance"]).rstrip(), "```"]
    if not full:
        return "\n".join(lines) + "\n"
    lines += ["", "## Verified errors and review findings", "", "Each row refers to an unchanged source entity. Full evidence and source pointers are in validation.json.", "",
              "| Category / code | Entity / title | Field | Evidence |", "| --- | --- | --- | --- |"]
    for f in report["findings"]:
        if f["category"] == "missing_source":
            continue
        entity = report["entities"].get(f["entity"], {})
        lines.append(f"| {md(f['category'])} / {md(f['code'])} | {md(f['entity'])} — {md(entity.get('title', 'Catalog'))} | {md(f['field'])} | {md(json.dumps(f['evidence'], ensure_ascii=False, sort_keys=True))} |")
    lines += ["", "## Missing source fields: affected entities", "", "Grouped for readability; no missing-field findings are omitted. IDs resolve through the entities map in validation.json.", ""]
    groups = defaultdict(list)
    for f in report["findings"]:
        if f["category"] == "missing_source":
            section = report["entities"].get(f["entity"], {}).get("section", "catalog")
            groups[(section, f["field"], f["evidence"].get("state", "unknown"))].append(f["entity"])
    for (section, field, status), entities in sorted(groups.items()):
        lines += [f"### {md(section)} / {md(field)} / {status}: {len(entities)}", ""]
        for i in range(0, len(entities), 25):
            lines.append(", ".join(md(e) for e in entities[i:i + 25]))
            lines.append("")
    return "\n".join(lines) + "\n"


def render_changes(report):
    lines = ["# Catalog snapshot comparison", "", report["interpretation"], "", f"Execution: {report['execution']}", "",
             "| Change | Count |", "| --- | ---: |"]
    lines += [f"| {key} | {count} |" for key, count in report["summary"].items()]
    lines += ["", "## Complete change evidence", "", "```json", json_text(report).rstrip(), "```", ""]
    return "\n".join(lines)


def write_reports(catalog, output_dir, baseline=None, baseline_manifest=None, low_plays=10):
    paths = {"validation.json", "summary.md", "issues.md", "changes.json", "changes.md"}
    output = Path(output_dir).resolve()
    protected = [Path(catalog).resolve()]
    protected += [Path(p).resolve() for p in (baseline, baseline_manifest) if p is not None]
    for name in paths:
        dest = (output / name).resolve()
        if dest in protected or (dest.exists() and any(p.exists() and dest.samefile(p) for p in protected)):
            raise ValueError("Report output would overwrite an input file")
    data, digest = load_json(catalog)
    old, old_digest, manifest = None, None, None
    if baseline is not None:
        old, old_digest = load_json(baseline)
    if baseline_manifest is not None:
        manifest, _ = load_json(baseline_manifest)
        if not isinstance(manifest, dict) or baseline is None or manifest.get("sha256") != old_digest:
            raise ValueError("Baseline checksum does not match its manifest")
    report = validate(data, low_plays)
    report["provenance"] = {"catalog_sha256": digest, "baseline_sha256": old_digest,
                            "baseline_manifest_verified": baseline_manifest is not None,
                            "baseline_source_commit": manifest.get("source_commit") if manifest else None}
    changes = compare(old, data) if baseline is not None else None
    if changes is not None:
        changes["provenance"] = report["provenance"]
    output.mkdir(parents=True, exist_ok=True)
    (output / "validation.json").write_text(json_text(report), encoding="utf-8")
    (output / "summary.md").write_text(render_report(report, full=False), encoding="utf-8")
    (output / "issues.md").write_text(render_report(report), encoding="utf-8")
    if changes is not None:
        (output / "changes.json").write_text(json_text(changes), encoding="utf-8")
        (output / "changes.md").write_text(render_changes(changes), encoding="utf-8")
    else:
        # Never leave a previous comparison masquerading as this run's result.
        for name in ("changes.json", "changes.md"):
            (output / name).write_text(json_text({"execution": "not_requested", "reason": "No baseline supplied"}) if name.endswith("json") else "# Snapshot comparison\n\nNot requested: no baseline supplied.\n", encoding="utf-8")
    return report, changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", nargs="?", default="catalog.json")
    parser.add_argument("--output-dir", default="reports")
    parser.add_argument("--baseline")
    parser.add_argument("--baseline-manifest")
    parser.add_argument("--low-plays", type=int, default=10, help="Flag plays below this review threshold; 0 disables low-play flags")
    args = parser.parse_args(argv)
    try:
        report, changes = write_reports(args.catalog, args.output_dir, args.baseline, args.baseline_manifest, args.low_plays)
    except (OSError, ValueError) as exc:
        print(f"Validation could not execute: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"execution": "completed", "checks_executed": [c["id"] for c in report["checks"]],
                      "findings": report["summary"]["findings_by_category"],
                      "comparison": changes["summary"] if changes is not None else "not_requested"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
