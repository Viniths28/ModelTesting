#!/usr/bin/env python3

import requests
import json

def test_api():
    url = "http://localhost:8000/v1/api/next_question_flow"
    payload = {
        "sectionId": "SEC_0f962e4d-a932-4958-9352-b54e0ef92be5",
        "applicationId": "Appl_123", 
        "applicantId": "App001",
        "isPrimaryFlow": True
    }
    
    print("Testing API with payload:")
    print(json.dumps(payload, indent=2))
    print()
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print()
        print("Response:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api() 