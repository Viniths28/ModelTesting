import requests
import json

def test_execute_api():
    url = "http://localhost:8005/api/execute"
    payload = {
        "sectionId": "SEC_0f962e4d-a932-4958-9352-b54e0ef92be5",
        "applicationId": "app_123",
        "applicantId": "applicant_456",
        "isPrimaryFlow": True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ API call successful!")
            return True
        else:
            print("❌ API call failed")
            return False
            
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False

if __name__ == "__main__":
    test_execute_api() 