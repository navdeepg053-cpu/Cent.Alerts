import requests
import sys
import json
from datetime import datetime

class CentSAPITester:
    def __init__(self, base_url="https://cents-monitor.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test": name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    {details}")

    def test_health_endpoint(self):
        """Test basic health endpoint"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                scraper_status = data.get('scraper_running', False)
                details = f"Status: {response.status_code}, Scraper running: {scraper_status}"
            else:
                details = f"Status: {response.status_code}"
                
            self.log_test("Health Check", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Health Check", False, f"Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root API endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Status: {response.status_code}, Message: {data.get('message', 'N/A')}"
            else:
                details = f"Status: {response.status_code}"
                
            self.log_test("Root API Endpoint", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Root API Endpoint", False, f"Error: {str(e)}")
            return False, {}

    def test_availability_endpoint(self):
        """Test availability endpoint (public)"""
        try:
            response = requests.get(f"{self.api_url}/availability", timeout=15)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                spots_count = len(data.get('spots', []))
                available_count = data.get('available_count', 0)
                details = f"Status: {response.status_code}, Total spots: {spots_count}, Available: {available_count}"
            else:
                details = f"Status: {response.status_code}"
                
            self.log_test("Availability Endpoint", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Availability Endpoint", False, f"Error: {str(e)}")
            return False, {}

    def create_test_user_session(self):
        """Create test user and session using MongoDB directly"""
        try:
            import subprocess
            import uuid
            
            # Generate unique identifiers
            timestamp = int(datetime.now().timestamp())
            user_id = f"test-user-{timestamp}"
            session_token = f"test_session_{timestamp}"
            email = f"test.user.{timestamp}@example.com"
            
            # MongoDB command to create test user and session
            mongo_cmd = f'''
            use('test_database');
            db.users.insertOne({{
                user_id: "{user_id}",
                email: "{email}",
                name: "Test User",
                picture: "https://via.placeholder.com/150",
                phone: "+39123456789",
                alert_email: true,
                alert_sms: false,
                alert_whatsapp: false,
                created_at: new Date()
            }});
            db.user_sessions.insertOne({{
                user_id: "{user_id}",
                session_token: "{session_token}",
                expires_at: new Date(Date.now() + 7*24*60*60*1000),
                created_at: new Date()
            }});
            '''
            
            result = subprocess.run(
                ['mongosh', '--eval', mongo_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                self.session_token = session_token
                self.user_id = user_id
                self.log_test("Create Test User Session", True, f"User ID: {user_id}")
                return True
            else:
                self.log_test("Create Test User Session", False, f"MongoDB error: {result.stderr}")
                return False
                
        except Exception as e:
            self.log_test("Create Test User Session", False, f"Error: {str(e)}")
            return False

    def test_auth_me_endpoint(self):
        """Test authenticated /auth/me endpoint"""
        if not self.session_token:
            self.log_test("Auth Me Endpoint", False, "No session token available")
            return False, {}
            
        try:
            headers = {'Authorization': f'Bearer {self.session_token}'}
            response = requests.get(f"{self.api_url}/auth/me", headers=headers, timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                details = f"Status: {response.status_code}, User: {data.get('email', 'N/A')}"
            else:
                details = f"Status: {response.status_code}"
                
            self.log_test("Auth Me Endpoint", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Auth Me Endpoint", False, f"Error: {str(e)}")
            return False, {}

    def test_notification_history_endpoint(self):
        """Test notification history endpoint"""
        if not self.session_token:
            self.log_test("Notification History", False, "No session token available")
            return False, {}
            
        try:
            headers = {'Authorization': f'Bearer {self.session_token}'}
            response = requests.get(f"{self.api_url}/notifications/history", headers=headers, timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                count = len(data) if isinstance(data, list) else 0
                details = f"Status: {response.status_code}, Notifications: {count}"
            else:
                details = f"Status: {response.status_code}"
                
            self.log_test("Notification History", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Notification History", False, f"Error: {str(e)}")
            return False, {}

    def test_alert_settings_update(self):
        """Test updating alert settings"""
        if not self.session_token:
            self.log_test("Update Alert Settings", False, "No session token available")
            return False, {}
            
        try:
            headers = {
                'Authorization': f'Bearer {self.session_token}',
                'Content-Type': 'application/json'
            }
            data = {
                "alert_telegram": True
            }
            response = requests.put(f"{self.api_url}/users/alerts", headers=headers, json=data, timeout=10)
            success = response.status_code == 200
            
            if success:
                resp_data = response.json()
                details = f"Status: {response.status_code}, Telegram alerts: {resp_data.get('alert_telegram')}"
            else:
                details = f"Status: {response.status_code}"
                
            self.log_test("Update Alert Settings", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Update Alert Settings", False, f"Error: {str(e)}")
            return False, {}

    def test_telegram_bot_info(self):
        """Test telegram bot info endpoint"""
        try:
            response = requests.get(f"{self.api_url}/telegram/bot-info", timeout=10)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                username = data.get('username', 'N/A')
                details = f"Status: {response.status_code}, Bot username: @{username}"
            else:
                details = f"Status: {response.status_code}"
                
            self.log_test("Telegram Bot Info", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Telegram Bot Info", False, f"Error: {str(e)}")
            return False, {}

    def test_telegram_connect(self):
        """Test telegram connection endpoint"""
        if not self.session_token:
            self.log_test("Connect Telegram", False, "No session token available")
            return False, {}
            
        try:
            headers = {
                'Authorization': f'Bearer {self.session_token}',
                'Content-Type': 'application/json'
            }
            data = {"chat_id": "123456789"}
            response = requests.post(f"{self.api_url}/users/telegram", headers=headers, json=data, timeout=10)
            success = response.status_code == 200
            
            if success:
                resp_data = response.json()
                details = f"Status: {response.status_code}, Chat ID: {resp_data.get('telegram_chat_id')}"
            else:
                details = f"Status: {response.status_code}"
                
            self.log_test("Connect Telegram", success, details)
            return success, response.json() if success else {}
        except Exception as e:
            self.log_test("Connect Telegram", False, f"Error: {str(e)}")
            return False, {}

    def cleanup_test_data(self):
        """Clean up test data from MongoDB"""
        try:
            import subprocess
            
            mongo_cmd = '''
            use('test_database');
            db.users.deleteMany({email: /test\.user\./});
            db.user_sessions.deleteMany({session_token: /test_session/});
            '''
            
            result = subprocess.run(
                ['mongosh', '--eval', mongo_cmd],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            success = result.returncode == 0
            self.log_test("Cleanup Test Data", success, "Removed test users and sessions")
            return success
            
        except Exception as e:
            self.log_test("Cleanup Test Data", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting CEnT-S API Tests...")
        print(f"📍 Testing: {self.base_url}")
        print("=" * 50)
        
        # Public endpoints
        self.test_root_endpoint()
        self.test_health_endpoint()
        self.test_availability_endpoint()
        
        # Create test user for authenticated endpoints
        if self.create_test_user_session():
            self.test_auth_me_endpoint()
            self.test_notification_history_endpoint()
            self.test_alert_settings_update()
            self.test_phone_update()
            self.cleanup_test_data()
        
        # Print summary
        print("=" * 50)
        print(f"📊 Tests completed: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print("⚠️  Some tests failed")
            return 1

def main():
    tester = CentSAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())