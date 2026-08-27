import os
from pathlib import Path


class FileSearchEngine:

    def __init__(self):
        self.running = True

    def reset(self):
        self.running = True

    def stop(self):
        self.running = False

    def search(
        self,
        roots,
        query="",
        extensions=None,
        result_callback=None,
        progress_callback=None,
    ):

        self.running = True

        query = query.lower().strip()

        if extensions is None:
            extensions = set()

        extensions = {
            ext.lower()
            for ext in extensions
        }

        scanned = 0
        found = 0

        result_batch = []

        # Batch size ছোট রাখলে realtime result দ্রুত দেখা যাবে
        batch_size = 15

        for root in roots:

            if not self.running:
                break

            try:

                for current_root, dirs, files in os.walk(
                    root,
                    topdown=True,
                ):

                    if not self.running:
                        break

                    # Permission-heavy folders skip
                    dirs[:] = [
                        d for d in dirs
                        if d.lower() not in {
                            "$recycle.bin",
                            "system volume information",
                        }
                    ]

                    # Live: currently scanning path
                    if progress_callback:
                        progress_callback(
                            scanned,
                            found,
                            current_root,
                        )

                    for filename in files:

                        if not self.running:
                            break

                        scanned += 1

                        lower_name = filename.lower()

                        # Filename matching
                        if query:

                            # Partial search
                            if query not in lower_name:
                                continue

                        file_path = os.path.join(
                            current_root,
                            filename,
                        )

                        suffix = Path(
                            filename
                        ).suffix.lower()

                        # Optional extension filter
                        if extensions:

                            if suffix not in extensions:
                                continue

                        try:

                            size = os.path.getsize(
                                file_path
                            )

                        except (
                            OSError,
                            PermissionError,
                        ):

                            continue

                        found += 1

                        result_batch.append({
                            "name": filename,
                            "path": file_path,
                            "size": size,
                        })

                        # Realtime results
                        if len(result_batch) >= batch_size:

                            if result_callback:

                                result_callback(
                                    result_batch
                                )

                            result_batch = []

                        # Progress update
                        if scanned % 100 == 0:

                            if progress_callback:

                                progress_callback(
                                    scanned,
                                    found,
                                    current_root,
                                )

            except (
                PermissionError,
                OSError,
            ):

                continue

        # Remaining results
        if result_batch and result_callback:

            result_callback(result_batch)

        return scanned, found