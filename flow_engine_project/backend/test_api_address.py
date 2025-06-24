#!/usr/bin/env python3

import requests
import json

def test_address_api():
    print("🌐 TESTING ADDRESS SECTION VIA API")
    print("=" * 60)
    
    url = "http://localhost:8000/v1/api/next_question_flow"
    payload = {
        "sectionId": "SEC_1a879403-51e3-4eef-b6c5-00a613f8f76e",
        "applicationId": "Appl_123", 
        "applicantId": "App001",
        "isPrimaryFlow": True
    }
    
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("\nMaking API request...")
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        print(f"\n📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API call successful!")
            print(f"\nResponse:")
            print(json.dumps(result, indent=2))
            
            # Analyze the result
            print(f"\n{'='*30}")
            print("RESULT ANALYSIS")
            print(f"{'='*30}")
            
            if result.get('question'):
                question_id = result['question']['questionId']
                print(f"✅ Next Question: {question_id}")
                
                if question_id == "Q_AD_Address_Check":
                    print("🎯 SUCCESS: Shows address verification question (UseCase 1)")
                    print("   This means dealer_address_exists = True worked correctly!")
                elif question_id == "Q_AD_Residential_Address_(Customer-Current)":
                    print("🤔 UNEXPECTED: Shows address collection instead of verification")
                    print("   This means dealer_address_exists = False (no test data?)")
                else:
                    print(f"❓ UNEXPECTED: Shows different question: {question_id}")
                    
            elif result.get('completed'):
                print("❌ Section completed immediately")
                print("   Check if both edge conditions are failing")
                
            else:
                print("❓ Unexpected result structure")
                
        else:
            print(f"❌ API call failed with status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - is the server running?")
        print("Start server with: python app.py")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_address_api() 