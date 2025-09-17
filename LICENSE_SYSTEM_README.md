# Stock Trading AI - License System

This document describes the comprehensive license key system that has been implemented for the Stock Trading AI platform, providing multi-tier access control, session management, and API protection.

## 🔑 License System Overview

The license system provides:
- **Multi-tier licensing** (Evaluation, Standard, Premium, Master)
- **Session-based authentication** with device tracking
- **Rate limiting** and usage monitoring
- **Feature-based access control**
- **Web UI with login system**
- **API protection** for all endpoints

## 📋 License Tiers

### Evaluation License (Free)
- **Concurrent Sessions**: 1
- **API Calls**: 10/hour, 50/day
- **Features**: Sentiment analysis only
- **Price**: Free
- **Use Case**: Trial and testing

### Standard License ($29.99/month)
- **Concurrent Sessions**: 1
- **API Calls**: 100/hour, 1,000/day
- **Features**: Sentiment, Technical, Historical data
- **Price**: $29.99/month
- **Use Case**: Individual traders

### Premium License ($99.99/month)
- **Concurrent Sessions**: 3
- **API Calls**: 500/hour, 5,000/day
- **Features**: All features including Unified analysis
- **Price**: $99.99/month
- **Use Case**: Professional traders

### Master License (Admin)
- **Concurrent Sessions**: Unlimited
- **API Calls**: Unlimited
- **Features**: All features + Admin access
- **Price**: Free (Admin use)
- **Use Case**: System administration

## 🛠️ Installation & Setup

### 1. Install the License System

```bash
# Initialize the database with license tables
python install_license_system.py
```

This will:
- Create all necessary license tables
- Set up default license tiers
- Verify the installation

### 2. Generate License Keys

```bash
# Generate a master key for admin use
python generate_license_keys.py master --user-name "Admin"

# Generate evaluation keys (30-day expiry)
python generate_license_keys.py evaluation --count 5 --expires-days 30

# Generate standard keys
python generate_license_keys.py standard --user-name "John Doe" --user-email "john@example.com"

# Generate premium keys
python generate_license_keys.py premium --user-name "Jane Smith" --expires-days 365
```

### 3. Start the Services

```bash
# Start the licensed web application (port 5001)
python licensed_web_app.py

# Start the API server with licensing (port 5000)
python server.py
```

## 🌐 Web Application

### Access the Web UI
1. Navigate to `http://localhost:5001`
2. Enter your license key on the login page
3. Access features based on your license tier

### Features Available:
- **Dashboard**: Overview of license and quick analysis
- **Analysis Page**: Comprehensive analysis tools
- **Session Management**: Automatic session handling
- **Feature-based UI**: Only shows available features

## 🔌 API Usage

### Authentication
All API endpoints require authentication using either:
1. **Session Token** (web application)
2. **License Key** (direct API access)

### Login Process
```bash
# Login with license key
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"license_key": "your_license_key_here"}'
```

### Protected Endpoints
```bash
# Sentiment Analysis (requires 'sentiment' feature)
curl "http://localhost:5000/sentiment?symbol=AAPL&articles=20" \
  -H "X-Session-Token: your_session_token"

# Technical Analysis (requires 'technical' feature)
curl "http://localhost:5000/technical?symbol=AAPL&timeframe=hour" \
  -H "X-Session-Token: your_session_token"

# Unified Analysis (requires 'unified' feature)
curl "http://localhost:5000/unified?symbol=AAPL&articles=20" \
  -H "X-Session-Token: your_session_token"

# Historical Data (requires 'historical' feature)
curl "http://localhost:5000/historical?symbol=AAPL&start_date=2024-01-01&end_date=2024-01-31" \
  -H "X-Session-Token: your_session_token"
```

## 🔧 Admin Features

### Master License Access
With a master license, you can:

```bash
# View all license keys
curl "http://localhost:5000/admin/licenses" \
  -H "X-Session-Token: master_session_token"

# Create new license keys
curl -X POST "http://localhost:5000/admin/licenses" \
  -H "Content-Type: application/json" \
  -H "X-Session-Token: master_session_token" \
  -d '{"tier_name": "standard", "user_name": "New User", "expires_days": 365}'

# View usage statistics
curl "http://localhost:5000/admin/usage" \
  -H "X-Session-Token: master_session_token"

# View active sessions
curl "http://localhost:5000/admin/sessions" \
  -H "X-Session-Token: master_session_token"
```

## 📊 Database Schema

### Key Tables
- **license_tiers**: License tier definitions
- **license_keys**: Individual license keys
- **license_sessions**: Active user sessions
- **api_usage_logs**: API call logging for analytics

### Key Functions
- **validate_license_key()**: Validates license and checks permissions
- **create_license_session()**: Creates authenticated sessions
- **validate_session_token()**: Validates active sessions
- **log_api_usage()**: Logs API calls for billing/analytics

## 🚀 Usage Examples

### Web Application Login
1. Visit `http://localhost:5001`
2. Enter license key: `your_64_character_license_key`
3. Access dashboard and analysis tools

### API Integration Example (Python)
```python
import requests

# Login
response = requests.post('http://localhost:5000/auth/login',
                        json={'license_key': 'your_license_key'})
session_token = response.json()['session_token']

# Use API
headers = {'X-Session-Token': session_token}
sentiment = requests.get('http://localhost:5000/sentiment?symbol=AAPL',
                        headers=headers)
print(sentiment.json())
```

## 🔒 Security Features

### Session Management
- **Device Fingerprinting**: Tracks unique devices
- **Session Expiration**: 24-hour default session lifetime
- **Concurrent Session Limits**: Enforced per license tier
- **Automatic Cleanup**: Expired sessions are automatically cleaned

### Rate Limiting
- **Hourly Limits**: Prevents API abuse
- **Daily Limits**: Ensures fair usage
- **Per-endpoint Tracking**: Detailed usage analytics
- **Master License Exception**: Unlimited access for admins

### Access Control
- **Feature-based Permissions**: Granular feature access
- **Tier-based Restrictions**: Clear separation of capabilities
- **Custom Messages**: Configurable disabled key messages
- **Real-time Validation**: Every request is validated

## 🛡️ Error Handling

### Common Error Responses
```json
// Invalid license key
{"error": "Invalid license key", "message": "License key not found"}

// Session expired
{"error": "Invalid session", "message": "Session has expired"}

// Rate limit exceeded
{"error": "Rate limit exceeded", "message": "Hourly rate limit exceeded (150/100)"}

// Feature not available
{"error": "Feature not available", "message": "Your license does not include access to technical features"}

// Concurrent session limit
{"error": "Session creation failed", "message": "Maximum concurrent sessions reached for this license"}
```

## 📈 Monitoring & Analytics

### Usage Tracking
- All API calls are logged with:
  - Timestamp and duration
  - Request/response sizes
  - IP address and user agent
  - Response status codes
  - Associated license key

### Admin Dashboards
- License key management
- Usage statistics per key/tier
- Active session monitoring
- Rate limit status

## 🔧 Configuration

### Database Configuration
Ensure `database_config.py` has correct PostgreSQL settings:
```python
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'stock_sentiment',
    'username': 'postgres',
    'password': 'your_password'
}
```

### License Tier Customization
Modify the license tiers in `Schemas/database_schema.sql` or via SQL:
```sql
UPDATE license_tiers
SET max_api_calls_per_hour = 200
WHERE tier_name = 'standard';
```

## 🚨 Troubleshooting

### Common Issues

**1. Database Connection Failed**
- Ensure PostgreSQL is running
- Check `database_config.py` settings
- Verify database exists and permissions

**2. License Key Invalid**
- Check key format (64 characters)
- Verify key exists in database
- Check if key is disabled or expired

**3. Session Issues**
- Clear browser cookies/session
- Check session token validity
- Verify device fingerprint matching

**4. Feature Access Denied**
- Verify license tier includes required features
- Check feature flags in database
- Confirm license is active

### Debug Mode
Run applications with debug mode for detailed error information:
```bash
# Web app with debug
python licensed_web_app.py

# API server with debug
python server.py
```

## 📞 Support

For technical support or license key issues:
1. Check the troubleshooting guide above
2. Review database logs for specific errors
3. Use admin endpoints to diagnose license issues
4. Contact system administrator with master license access

---

**Note**: This license system provides enterprise-grade authentication and authorization for the Stock Trading AI platform. All license keys are cryptographically secure and sessions are properly managed for maximum security.