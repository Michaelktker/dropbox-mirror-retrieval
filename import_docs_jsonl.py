#!/usr/bin/env python3
"""
Generate JSONL metadata file for Vertex AI Search import, then trigger import.

For unstructured data stores, Vertex AI Search requires a JSONL file where each line
is a JSON object with:
  - id: unique document ID
  - content.mimeType: the MIME type
  - content.uri: GCS URI of the document
"""
import json
import subprocess
import os

BUCKET = "gen-lang-client-0540480379-dropbox-mirror"
PROJECT_ID = "gen-lang-client-0540480379"
DATASTORE_ID = "dropbox-docs-datastore-ocr"

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".html": "text/html",
}

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

def main():
    print("=== Generate JSONL and Import Docs to Vertex AI Search ===\n")
    
    # Step 1: List all docs
    print("1. Listing docs in GCS...")
    doc_uris = gsutil_ls("mirror/docs/")
    print(f"   Found {len(doc_uris)} docs")
    
    # Step 2: Generate JSONL content
    print("\n2. Generating JSONL metadata...")
    jsonl_lines = []
    
    for uri in doc_uris:
        # Extract file_id and extension from URI
        # gs://bucket/mirror/docs/ABC123.pdf -> ABC123, .pdf
        filename = uri.split("/")[-1]
        file_id, ext = os.path.splitext(filename)
        mime_type = MIME_TYPES.get(ext.lower(), "application/octet-stream")
        
        doc = {
            "id": file_id,
            "content": {
                "mimeType": mime_type,
                "uri": uri
            }
        }
        jsonl_lines.append(json.dumps(doc))
    
    jsonl_content = "\n".join(jsonl_lines)
    print(f"   Generated {len(jsonl_lines)} document entries")
    
    # Step 3: Upload JSONL to GCS
    print("\n3. Uploading JSONL to GCS...")
    jsonl_uri = f"gs://{BUCKET}/mirror/state/docs_import.jsonl"
    
    proc = subprocess.Popen(
        ["gsutil", "cp", "-", jsonl_uri],
        stdin=subprocess.PIPE, text=True
    )
    proc.communicate(input=jsonl_content)
    
    if proc.returncode == 0:
        print(f"   OK - Uploaded to {jsonl_uri}")
    else:
        print("   FAILED to upload JSONL")
        return
    
    # Step 4: Trigger import
    print("\n4. Triggering import...")
    token = get_access_token()
    
    # For unstructured docs with content.uri, use "content" dataSchema
    payload = {
        "gcsSource": {
            "inputUris": [jsonl_uri],
            "dataSchema": "content"
        },
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
    
    response = json.loads(result.stdout) if result.stdout else {}
    
    if "name" in response:
        op_name = response["name"]
        print(f"   OK - Import started: {op_name.split('/')[-1]}")
        print(f"\nCheck status with:")
        print(f'  curl -s "https://discoveryengine.googleapis.com/v1/{op_name}" \\')
        print(f'    -H "Authorization: Bearer $(gcloud auth print-access-token)" | python3 -m json.tool')
    else:
        print(f"   Response: {json.dumps(response, indent=2)}")

if __name__ == "__main__":
    main()
