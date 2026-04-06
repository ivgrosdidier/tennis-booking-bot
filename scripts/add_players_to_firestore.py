import json
from firebase_admin import credentials, firestore, initialize_app

# 1. Setup
cred = credentials.Certificate("firebase-auth-dev.json")
initialize_app(cred)
db = firestore.client(database_id="dev-db")

# 2. Read your JSON
with open('data/players.json', encoding='utf-8') as f:
    raw_data = json.load(f)

# 3. Upload each player as a document
for name, email in raw_data.items():
    # We use the name as the Document ID
    # We store the email inside the document fields
    db.collection("players").document(name).set({
        "email": email,
        "active": True
    })

print(f"Upload complete! Processed {len(raw_data)} players.")