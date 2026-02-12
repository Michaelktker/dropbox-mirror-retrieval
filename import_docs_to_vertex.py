#!/usr/bin/env python3
"""
Import docs to Vertex AI Search in batches of 1000.
"""
import json
import subprocess
import time

BUCKET = "gen-lang-client-0540480379-dropbox-mirror"
PROJECT_ID = "gen-lang-client-0540480379"
DATASTORE_ID = "dropbox-docs-datastore-ocr"
BATCH_SIZE = 100  # API limit is 100 URIs per import request

def gsutil_ls(prefix):
    result = subprocess.run(
        ["gsutil", "ls", f"gs://{BUCKET}/{prefix}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return []
    return [l for l in result.stdout.strip().split("\n") if l]

def get_access_token():
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def trigger_import(uris):
    token = get_access_token()
    payload = {
        "gcsSource": {"inputUris": uris},
        "reconciliationMode": "INCREMENTAL"
    }
    url = f"https://discoveryengine.googleapis.com/v1/projects/{PROJECT_ID}/locations/global/collections/default_collection/dataStores/{DATASTORE_ID}/branches/default_branch/documents:import"
    
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", url,
         "-H", f"Authorization: Bearer {token}",
         "-H", f"x-goog-user-project: {PROJECT_ID}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload)],
        capture_output=True, text=True
    )
    return json.loads(result.stdout) if result.stdout else {"error": "No response"}

def main():
    print("=== Importing docs to Vertex AI Search ===\n")
    
    print("1. Listing docs in GCS...")
    doc_uris = gsutil_ls("mirror/docs/")
    print(f"   Found {len(doc_uris)} docs")
    
    batches = [doc_uris[i:i+BATCH_SIZE] for i in range(0, len(doc_uris), BATCH_SIZE)]
    print(f"   Split into {len(batches)} batches")
    
    print("\n2. Triggering imports...")
    operations = []
    
    for i, batch in enumerate(batches):
        print(f"\n   Batch {i+1}/{len(batches)} ({len(batch)} files)...")
        result = trigger_import(batch)
        
        if "name" in result:
            op_name = result["name"]
            operations.append(op_name)
            print(f"   OK: {op_name.split('/')[-1]}")
        elif "error" in result:
            print(f"   ERROR: {result.get('error', {}).get('message', result)}")
        else:
            print(f"   Unknown: {result}")
        
        if i < len(batches) - 1:
            time.sleep(2)
    
    print(f"\n=== {len(operations)} imports triggered ===")
    for op in operations:
        print(f"  - {op.split('/')[-1]}")

if __name__ == "__main__":
    main()
