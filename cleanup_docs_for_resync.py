#!/usr/bin/env python3
"""
Remove doc entries from rev_index to force re-sync with file extensions.
Also clears the cursor to force a full Dropbox scan.

Faster approach: Get list of image file_ids from GCS (they have the correct format),
then remove all OTHER entries from rev_index (those are docs/media that need re-sync).
"""
import json
import subprocess
import sys
import re

BUCKET = "gs://gen-lang-client-0540480379-dropbox-mirror"
REV_INDEX_KEY = "mirror/state/rev_index.json"
SYNC_STATE_KEY = "mirror/state/sync_state.json"

def gsutil_cat(key):
    """Read a GCS object."""
    result = subprocess.run(
        ["gsutil", "cat", f"{BUCKET}/{key}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)

def gsutil_cp(content, key):
    """Write content to GCS."""
    proc = subprocess.Popen(
        ["gsutil", "cp", "-", f"{BUCKET}/{key}"],
        stdin=subprocess.PIPE, text=True
    )
    proc.communicate(input=json.dumps(content))
    return proc.returncode == 0

def gsutil_ls(prefix):
    """List GCS objects."""
    result = subprocess.run(
        ["gsutil", "ls", f"{BUCKET}/{prefix}"],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []
    return result.stdout.strip().split("\n")

def main():
    print("=== Cleanup docs for re-sync ===\n")
    
    # Step 1: Load rev_index
    print("1. Loading rev_index...")
    rev_index = gsutil_cat(REV_INDEX_KEY) or {}
    original_count = len(rev_index)
    print(f"   Found {original_count} entries in rev_index")
    
    # Step 2: Get image file_ids from GCS (these are OK, don't need re-sync)
    print("\n2. Getting image file_ids from GCS...")
    image_files = gsutil_ls("mirror/images/")
    image_file_ids = set()
    for f in image_files:
        # Extract file_id from path like: gs://bucket/mirror/images/ABC123
        match = re.search(r'/mirror/images/([^/]+)$', f)
        if match:
            image_file_ids.add(match.group(1))
    print(f"   Found {len(image_file_ids)} images in GCS")
    
    # Step 3: Get existing doc file_ids from GCS (already have extensions, keep them)
    print("\n3. Getting existing doc file_ids from GCS...")
    doc_files = gsutil_ls("mirror/docs/")
    existing_doc_ids = set()
    for f in doc_files:
        # Extract file_id from path like: gs://bucket/mirror/docs/ABC123.pdf
        match = re.search(r'/mirror/docs/([^/]+)\.[a-z]+$', f)
        if match:
            existing_doc_ids.add(match.group(1))
    print(f"   Found {len(existing_doc_ids)} docs with extensions in GCS")
    
    # Step 4: Keep only entries for images and existing docs with extensions
    print("\n4. Filtering rev_index to keep only valid entries...")
    keep_ids = image_file_ids | existing_doc_ids
    new_rev_index = {fid: rev for fid, rev in rev_index.items() if fid in keep_ids}
    removed = original_count - len(new_rev_index)
    
    print(f"   Removed {removed} entries (docs without extensions, media)")
    print(f"   Keeping {len(new_rev_index)} entries")
    
    # Step 5: Save updated rev_index
    print("\n5. Saving updated rev_index...")
    if gsutil_cp(new_rev_index, REV_INDEX_KEY):
        print("   OK - rev_index saved")
    else:
        print("   FAILED to save rev_index")
        sys.exit(1)
    
    # Step 6: Clear cursor from sync_state to force full re-scan
    print("\n6. Clearing cursor from sync_state...")
    sync_state = gsutil_cat(SYNC_STATE_KEY) or {}
    if "cursor" in sync_state:
        del sync_state["cursor"]
        if gsutil_cp(sync_state, SYNC_STATE_KEY):
            print("   OK - Cursor cleared")
        else:
            print("   FAILED to clear cursor")
            sys.exit(1)
    else:
        print("   No cursor to clear")
    
    print("\n=== Done! ===")
    print(f"\nSummary:")
    print(f"  - Original rev_index entries: {original_count}")
    print(f"  - Entries removed (need re-sync): {removed}")
    print(f"  - Entries kept (images + valid docs): {len(new_rev_index)}")
    print(f"\nNext steps:")
    print("  1. Run: gcloud run jobs execute sync-dropbox-to-gcs --region=us-central1")
    print("  2. After sync completes, verify docs have extensions:")
    print("     gsutil ls 'gs://gen-lang-client-0540480379-dropbox-mirror/mirror/docs/' | head -10")
    print("  3. Import docs to Vertex AI Search datastore")

if __name__ == "__main__":
    main()
