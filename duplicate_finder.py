import os
import hashlib
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor


class DuplicateFinder:
    """
    Duplicate detection modes:

    name
        Same filename + extension.

    quick
        Same file size + first/last 64 KB sample.
        Filename does NOT have to be the same.

    hash
        Same file size + complete BLAKE2b hash.
        This is the exact duplicate check.
    """

    CHUNK_SIZE = 1024 * 1024

    QUICK_SAMPLE_SIZE = 64 * 1024

    def __init__(self):

        self.stop_event = threading.Event()

    # ======================================================
    # Stop
    # ======================================================

    def stop(self):

        self.stop_event.set()

    # ======================================================
    # Reset
    # ======================================================

    def reset(self):

        self.stop_event.clear()

    # ======================================================
    # File Iterator
    # ======================================================

    def _iter_files(self, roots):

        for root in roots:

            if self.stop_event.is_set():
                return

            if not os.path.exists(root):
                continue

            for current_root, dirs, files in os.walk(
                root,
                topdown=True,
                onerror=lambda e: None
            ):

                if self.stop_event.is_set():
                    return

                for filename in files:

                    if self.stop_event.is_set():
                        return

                    path = os.path.join(
                        current_root,
                        filename
                    )

                    try:

                        # Skip symbolic links
                        if os.path.islink(path):
                            continue

                        size = os.path.getsize(path)

                        yield {
                            "name": filename,
                            "path": path,
                            "size": size
                        }

                    except OSError:
                        continue

    # ======================================================
    # NAME SEARCH
    # ======================================================

    def find_by_name(
        self,
        roots,
        result_callback=None,
        progress_callback=None
    ):

        self.reset()

        groups = defaultdict(list)

        scanned = 0
        found_groups = 0

        # --------------------------------------------------
        # Group files by filename.
        #
        # Example:
        #
        # photo.jpg
        # photo.jpg
        # photo.jpg
        #
        # They will become one group.
        # --------------------------------------------------

        for info in self._iter_files(roots):

            if self.stop_event.is_set():
                break

            scanned += 1

            key = info["name"].lower()

            groups[key].append(info)

            # ------------------------------------------------
            # First time a duplicate appears.
            # ------------------------------------------------

            if len(groups[key]) == 2:

                found_groups += 1

                if result_callback:

                    result_callback(
                        key,
                        groups[key].copy()
                    )

            # ------------------------------------------------
            # More files with same name.
            #
            # Keep updating the same group.
            # ------------------------------------------------

            elif len(groups[key]) > 2:

                if result_callback:

                    result_callback(
                        key,
                        groups[key].copy()
                    )

            # ------------------------------------------------
            # Progress
            # ------------------------------------------------

            if scanned % 1000 == 0:

                if progress_callback:

                    progress_callback(
                        scanned,
                        found_groups,
                        "Scanning names..."
                    )

        # --------------------------------------------------
        # Finished
        # --------------------------------------------------

        if progress_callback:

            progress_callback(
                scanned,
                found_groups,
                "Finished"
            )

    # ======================================================
    # QUICK HASH
    # ======================================================

    def _quick_hash(self, info):

        path = info["path"]
        size = info["size"]

        try:

            h = hashlib.blake2b(
                digest_size=16
            )

            with open(path, "rb") as f:

                # ------------------------------------------------
                # First 64 KB
                # ------------------------------------------------

                first_sample = f.read(
                    self.QUICK_SAMPLE_SIZE
                )

                h.update(first_sample)

                # ------------------------------------------------
                # Last 64 KB
                #
                # For small files, first and last sample would
                # overlap, so don't read the same area twice.
                # ------------------------------------------------

                if size > self.QUICK_SAMPLE_SIZE:

                    f.seek(
                        max(
                            0,
                            size - self.QUICK_SAMPLE_SIZE
                        )
                    )

                    last_sample = f.read(
                        self.QUICK_SAMPLE_SIZE
                    )

                    h.update(last_sample)

            return (
                h.hexdigest(),
                info
            )

        except OSError:

            return None

    # ======================================================
    # QUICK SEARCH
    # ======================================================

    def find_quick(
        self,
        roots,
        result_callback=None,
        progress_callback=None
    ):

        self.reset()

        size_groups = defaultdict(list)

        scanned = 0

        # --------------------------------------------------
        # STAGE 1
        #
        # First group files by SIZE.
        #
        # Files with different sizes cannot be identical.
        # --------------------------------------------------

        for info in self._iter_files(roots):

            if self.stop_event.is_set():
                return

            scanned += 1

            size_groups[
                info["size"]
            ].append(info)

            if scanned % 2000 == 0:

                if progress_callback:

                    progress_callback(
                        scanned,
                        0,
                        "Grouping by size..."
                    )

        # --------------------------------------------------
        # Only same-size files are candidates.
        # --------------------------------------------------

        candidates = []

        for group in size_groups.values():

            if len(group) > 1:

                candidates.extend(group)

        # --------------------------------------------------
        # No candidates
        # --------------------------------------------------

        if not candidates:

            if progress_callback:

                progress_callback(
                    scanned,
                    0,
                    "No duplicates found"
                )

            return

        # --------------------------------------------------
        # STAGE 2
        #
        # Compare first/last sample.
        #
        # IMPORTANT:
        # Filename is NOT used here.
        #
        # Therefore:
        #
        # photo.jpg
        # vacation.jpg
        # backup.png
        #
        # can belong to the same group if their content
        # samples match.
        # --------------------------------------------------

        hash_groups = defaultdict(list)

        total = len(candidates)
        processed = 0
        found_groups = 0

        workers = min(
            8,
            max(
                2,
                os.cpu_count() or 2
            )
        )

        with ThreadPoolExecutor(
            max_workers=workers
        ) as executor:

            for result in executor.map(
                self._quick_hash,
                candidates
            ):

                if self.stop_event.is_set():
                    return

                processed += 1

                if result:

                    key, info = result

                    hash_groups[key].append(
                        info
                    )

                    # --------------------------------------------
                    # First duplicate pair
                    # --------------------------------------------

                    if len(hash_groups[key]) == 2:

                        found_groups += 1

                        if result_callback:

                            result_callback(
                                key,
                                hash_groups[key].copy()
                            )

                    # --------------------------------------------
                    # Additional duplicate files
                    # --------------------------------------------

                    elif len(hash_groups[key]) > 2:

                        if result_callback:

                            result_callback(
                                key,
                                hash_groups[key].copy()
                            )

                if processed % 20 == 0:

                    if progress_callback:

                        progress_callback(
                            processed,
                            found_groups,
                            "Quick comparing..."
                        )

        # --------------------------------------------------
        # Finished
        # --------------------------------------------------

        if progress_callback:

            progress_callback(
                total,
                found_groups,
                "Finished"
            )

    # ======================================================
    # FULL HASH
    # ======================================================

    def _full_hash(self, info):

        try:

            h = hashlib.blake2b(
                digest_size=32
            )

            with open(
                info["path"],
                "rb"
            ) as f:

                while True:

                    if self.stop_event.is_set():
                        return None

                    chunk = f.read(
                        self.CHUNK_SIZE
                    )

                    if not chunk:
                        break

                    h.update(chunk)

            return (
                h.hexdigest(),
                info
            )

        except OSError:

            return None

    # ======================================================
    # HASH SEARCH
    # ======================================================

    def find_hash(
        self,
        roots,
        result_callback=None,
        progress_callback=None
    ):

        self.reset()

        size_groups = defaultdict(list)

        scanned = 0

        # --------------------------------------------------
        # STAGE 1
        #
        # Group by file size.
        # --------------------------------------------------

        for info in self._iter_files(roots):

            if self.stop_event.is_set():
                return

            scanned += 1

            size_groups[
                info["size"]
            ].append(info)

            if scanned % 2000 == 0:

                if progress_callback:

                    progress_callback(
                        scanned,
                        0,
                        "Grouping by size..."
                    )

        # --------------------------------------------------
        # Only same-size files need full hashing.
        # --------------------------------------------------

        candidates = []

        for group in size_groups.values():

            if len(group) > 1:

                candidates.extend(group)

        # --------------------------------------------------
        # No candidates
        # --------------------------------------------------

        if not candidates:

            if progress_callback:

                progress_callback(
                    scanned,
                    0,
                    "No duplicates found"
                )

            return

        # --------------------------------------------------
        # STAGE 2
        #
        # Full BLAKE2b hash.
        # Filename is NOT considered.
        #
        # So files with different names but exactly the
        # same content will be grouped together.
        # --------------------------------------------------

        hash_groups = defaultdict(list)

        total = len(candidates)
        processed = 0
        found_groups = 0

        workers = min(
            6,
            max(
                2,
                os.cpu_count() or 2
            )
        )

        with ThreadPoolExecutor(
            max_workers=workers
        ) as executor:

            for result in executor.map(
                self._full_hash,
                candidates
            ):

                if self.stop_event.is_set():
                    return

                processed += 1

                if result:

                    key, info = result

                    hash_groups[key].append(
                        info
                    )

                    # --------------------------------------------
                    # First duplicate pair
                    # --------------------------------------------

                    if len(hash_groups[key]) == 2:

                        found_groups += 1

                        if result_callback:

                            result_callback(
                                key,
                                hash_groups[key].copy()
                            )

                    # --------------------------------------------
                    # Additional duplicate files
                    # --------------------------------------------

                    elif len(hash_groups[key]) > 2:

                        if result_callback:

                            result_callback(
                                key,
                                hash_groups[key].copy()
                            )

                if processed % 5 == 0:

                    if progress_callback:

                        progress_callback(
                            processed,
                            found_groups,
                            "Hashing files..."
                        )

        # --------------------------------------------------
        # Finished
        # --------------------------------------------------

        if progress_callback:

            progress_callback(
                total,
                found_groups,
                "Finished"
            )