import requests
import sys
import json
import os
from datetime import datetime
import tempfile
from io import BytesIO
from PIL import Image

class PhotoEventAPITester:
    def __init__(self, base_url="https://snapfinder-7.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    # Remove Content-Type for multipart
                    headers.pop('Content-Type', None)
                    response = requests.post(url, headers=headers, files=files, data=data)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}"
            
            if success:
                try:
                    response_data = response.json()
                    details += f", Response: {json.dumps(response_data, indent=2)[:200]}..."
                except:
                    details += f", Response: {response.text[:100]}..."
            else:
                details += f", Expected: {expected_status}, Response: {response.text[:200]}"

            self.log_test(name, success, details)
            return success, response.json() if success and response.text else {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_user_registration(self):
        """Test user registration"""
        timestamp = datetime.now().strftime('%H%M%S')
        user_data = {
            "email": f"test_user_{timestamp}@example.com",
            "password": "TestPass123!",
            "name": f"Test User {timestamp}"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=user_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            print(f"   Token obtained: {self.token[:20]}...")
            return True
        return False

    def test_user_login(self):
        """Test user login with existing credentials"""
        # Use the same credentials from registration
        timestamp = datetime.now().strftime('%H%M%S')
        login_data = {
            "email": f"test_user_{timestamp}@example.com",
            "password": "TestPass123!"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response['user']['id']
            return True
        return False

    def test_get_user_profile(self):
        """Test get current user profile"""
        return self.run_test("Get User Profile", "GET", "auth/me", 200)

    def test_create_event(self):
        """Test event creation"""
        event_data = {
            "name": f"Test Event {datetime.now().strftime('%H%M%S')}",
            "description": "Test event for API testing",
            "date": "2024-12-25"
        }
        
        success, response = self.run_test(
            "Create Event",
            "POST",
            "events",
            200,
            data=event_data
        )
        
        if success and 'id' in response:
            self.event_id = response['id']
            print(f"   Event ID: {self.event_id}")
            return True
        return False

    def test_get_events(self):
        """Test get user events"""
        return self.run_test("Get Events", "GET", "events", 200)

    def test_get_event_detail(self):
        """Test get specific event"""
        if not hasattr(self, 'event_id'):
            self.log_test("Get Event Detail", False, "No event ID available")
            return False
            
        return self.run_test(
            "Get Event Detail",
            "GET",
            f"events/{self.event_id}",
            200
        )

    def create_test_image(self):
        """Create a test image file for upload"""
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        return img_bytes

    def test_photo_upload(self):
        """Test photo upload to event"""
        if not hasattr(self, 'event_id'):
            self.log_test("Photo Upload", False, "No event ID available")
            return False

        # Create test image
        test_image = self.create_test_image()
        
        files = {
            'files': ('test_photo.jpg', test_image, 'image/jpeg')
        }
        
        success, response = self.run_test(
            "Photo Upload",
            "POST",
            f"events/{self.event_id}/photos",
            200,
            files=files
        )
        
        if success and isinstance(response, list) and len(response) > 0:
            self.photo_id = response[0]['id']
            print(f"   Photo ID: {self.photo_id}")
            return True
        return False

    def test_get_event_photos(self):
        """Test get photos for event"""
        if not hasattr(self, 'event_id'):
            self.log_test("Get Event Photos", False, "No event ID available")
            return False
            
        return self.run_test(
            "Get Event Photos",
            "GET",
            f"events/{self.event_id}/photos",
            200
        )

    def test_public_event_access(self):
        """Test public event access (no auth required)"""
        if not hasattr(self, 'event_id'):
            self.log_test("Public Event Access", False, "No event ID available")
            return False
        
        # Temporarily remove token for public access
        temp_token = self.token
        self.token = None
        
        success, response = self.run_test(
            "Public Event Access",
            "GET",
            f"public/events/{self.event_id}",
            200
        )
        
        # Restore token
        self.token = temp_token
        return success

    def test_public_event_photos(self):
        """Test public event photos access"""
        if not hasattr(self, 'event_id'):
            self.log_test("Public Event Photos", False, "No event ID available")
            return False
        
        # Temporarily remove token for public access
        temp_token = self.token
        self.token = None
        
        success, response = self.run_test(
            "Public Event Photos",
            "GET",
            f"public/events/{self.event_id}/photos",
            200
        )
        
        # Restore token
        self.token = temp_token
        return success

    def test_delete_event(self):
        """Test event deletion"""
        if not hasattr(self, 'event_id'):
            self.log_test("Delete Event", False, "No event ID available")
            return False
            
        return self.run_test(
            "Delete Event",
            "DELETE",
            f"events/{self.event_id}",
            200
        )

    def run_all_tests(self):
        """Run all API tests in sequence"""
        print("🚀 Starting PhotoEvent Pro API Tests")
        print(f"   Base URL: {self.base_url}")
        print("=" * 60)

        # Test sequence
        tests = [
            self.test_health_check,
            self.test_user_registration,
            self.test_get_user_profile,
            self.test_create_event,
            self.test_get_events,
            self.test_get_event_detail,
            self.test_photo_upload,
            self.test_get_event_photos,
            self.test_public_event_access,
            self.test_public_event_photos,
            # Don't delete event so we can test frontend
            # self.test_delete_event,
        ]

        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_test(test.__name__, False, f"Exception: {str(e)}")

        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed. Check details above.")
            return False

def main():
    tester = PhotoEventAPITester()
    success = tester.run_all_tests()
    
    # Save test results
    with open('/app/test_reports/backend_api_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_tests': tester.tests_run,
            'passed_tests': tester.tests_passed,
            'success_rate': tester.tests_passed / tester.tests_run if tester.tests_run > 0 else 0,
            'results': tester.test_results
        }, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())