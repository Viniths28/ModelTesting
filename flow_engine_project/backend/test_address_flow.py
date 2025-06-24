#!/usr/bin/env python3

import requests
import json

def test_address_flow():
    url = "http://localhost:8000/v1/api/next_question_flow"
    payload = {
        "sectionId": "SEC_1a879403-51e3-4eef-b6c5-00a613f8f76e",  # Fixed: Added missing quote
        "applicationId": "Appl_123", 
        "applicantId": "App001",
        "isPrimaryFlow": True
    }
    
    print("Testing Address Flow Section:")
    print(json.dumps(payload, indent=2))
    print()
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print()
        
        if response.status_code == 200:
            print("✅ SUCCESS - Response:")
            print(json.dumps(response.json(), indent=2))
        else:
            print("❌ ERROR - Response:")
            print(json.dumps(response.json(), indent=2))
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_address_flow() 