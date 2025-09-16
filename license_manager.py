#!/usr/bin/env python3
"""
License Key Management System
Handles license key validation, session management, and permission checking
"""

import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from functools import wraps
from flask import request, jsonify, session, g
import psycopg2
import psycopg2.extras
from core.database import SentimentDatabase

class LicenseManager:
    """
    Comprehensive license key management system with multi-tier support
    """

    def __init__(self):
        """Initialize license manager with database connection"""
        self.db = SentimentDatabase()

    def generate_license_key(self, tier_name: str, user_name: str = None,
                           user_email: str = None, expires_days: int = None) -> str:
        """
        Generate a new license key

        Args:
            tier_name: License tier (evaluation, standard, premium, master)
            user_name: Optional user name
            user_email: Optional user email
            expires_days: Optional expiration in days (None for no expiration)

        Returns:
            Generated license key string
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get tier ID
                cursor.execute("SELECT id FROM license_tiers WHERE tier_name = %s", (tier_name,))
                tier_result = cursor.fetchone()
                if not tier_result:
                    raise ValueError(f"Invalid tier name: {tier_name}")

                tier_id = tier_result['id']

                # Generate secure license key
                cursor.execute("SELECT generate_license_key()")
                license_key = cursor.fetchone()['generate_license_key']

                # Calculate expiration
                expires_at = None
                if expires_days:
                    expires_at = datetime.utcnow() + timedelta(days=expires_days)

                # Insert license key
                cursor.execute("""
                    INSERT INTO license_keys (license_key, tier_id, user_name, user_email, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (license_key, tier_id, user_name, user_email, expires_at))

                license_id = cursor.fetchone()['id']

            conn.commit()

        print(f"[LICENSE] Generated {tier_name} license key for {user_name or 'Anonymous'} (ID: {license_id})")
        return license_key

    def validate_license_key(self, license_key: str) -> Dict[str, Any]:
        """
        Validate a license key and return its details

        Args:
            license_key: License key to validate

        Returns:
            Dictionary with validation result and license details
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM validate_license_key(%s)", (license_key,))
                result = cursor.fetchone()

                if result:
                    return {
                        'valid': result['valid'],
                        'license_id': result['license_id'],
                        'tier_name': result['tier_name'],
                        'user_name': result['user_name'],
                        'features_enabled': result['features_enabled'],
                        'max_concurrent_sessions': result['max_concurrent_sessions'],
                        'current_sessions': result['current_sessions'],
                        'message': result['message']
                    }
                else:
                    return {
                        'valid': False,
                        'message': 'License validation failed'
                    }

    def create_session(self, license_key: str, device_fingerprint: str = None,
                      user_agent: str = None, ip_address: str = None,
                      session_duration_hours: int = 24) -> Dict[str, Any]:
        """
        Create a new session for a license key

        Args:
            license_key: Valid license key
            device_fingerprint: Optional device fingerprint
            user_agent: Optional user agent string
            ip_address: Optional IP address
            session_duration_hours: Session duration in hours

        Returns:
            Dictionary with session creation result
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM create_license_session(%s, %s, %s, %s::inet, %s)
                """, (license_key, device_fingerprint, user_agent, ip_address, session_duration_hours))

                result = cursor.fetchone()
                conn.commit()  # Ensure transaction is committed

                if result:
                    return {
                        'success': result['success'],
                        'session_token': result['session_token'],
                        'message': result['message']
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Session creation failed'
                    }

    def validate_session(self, session_token: str) -> Dict[str, Any]:
        """
        Validate a session token

        Args:
            session_token: Session token to validate

        Returns:
            Dictionary with validation result and session details
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM validate_session_token(%s)", (session_token,))
                result = cursor.fetchone()

                if result:
                    return {
                        'valid': result['valid'],
                        'license_key_id': result['license_key_id'],
                        'tier_name': result['tier_name'],
                        'features_enabled': result['features_enabled'],
                        'message': result['message']
                    }
                else:
                    return {
                        'valid': False,
                        'message': 'Session validation failed'
                    }

    def log_api_usage(self, session_token: str, endpoint: str, method: str = 'GET',
                     request_size: int = 0, response_size: int = 0,
                     response_status: int = 200, processing_time_ms: int = 0,
                     ip_address: str = None, user_agent: str = None):
        """
        Log API usage for analytics and billing

        Args:
            session_token: Valid session token
            endpoint: API endpoint accessed
            method: HTTP method
            request_size: Request size in bytes
            response_size: Response size in bytes
            response_status: HTTP response status code
            processing_time_ms: Processing time in milliseconds
            ip_address: Client IP address
            user_agent: Client user agent
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT log_api_usage(%s, %s, %s, %s, %s, %s, %s, %s::inet, %s)
                    """, (session_token, endpoint, method, request_size, response_size,
                         response_status, processing_time_ms, ip_address, user_agent))

                conn.commit()
        except Exception as e:
            print(f"[WARNING] Failed to log API usage: {e}")

    def disable_license_key(self, license_key: str, message: str = None):
        """
        Disable a license key

        Args:
            license_key: License key to disable
            message: Optional custom message to display when key is used
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE license_keys
                    SET is_active = FALSE, disabled_message = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE license_key = %s
                """, (message, license_key))

                # Deactivate all sessions for this license key
                cursor.execute("""
                    UPDATE license_sessions
                    SET is_active = FALSE
                    FROM license_keys
                    WHERE license_sessions.license_key_id = license_keys.id
                    AND license_keys.license_key = %s
                """, (license_key,))

            conn.commit()

        print(f"[LICENSE] Disabled license key: {license_key[:8]}...")

    def enable_license_key(self, license_key: str):
        """
        Re-enable a license key

        Args:
            license_key: License key to enable
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE license_keys
                    SET is_active = TRUE, disabled_message = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE license_key = %s
                """, (license_key,))

            conn.commit()

        print(f"[LICENSE] Enabled license key: {license_key[:8]}...")

    def get_license_usage_stats(self, license_key: str = None,
                               days_back: int = 30) -> Dict[str, Any]:
        """
        Get usage statistics for license keys

        Args:
            license_key: Optional specific license key (None for all keys)
            days_back: Number of days to look back

        Returns:
            Dictionary with usage statistics
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cutoff_date = datetime.utcnow() - timedelta(days=days_back)

                if license_key:
                    # Stats for specific license key
                    cursor.execute("""
                        SELECT
                            lk.license_key,
                            lk.user_name,
                            lt.tier_name,
                            lt.display_name,
                            COUNT(aul.id) as total_api_calls,
                            COUNT(DISTINCT DATE(aul.request_timestamp)) as active_days,
                            AVG(aul.processing_time_ms) as avg_processing_time,
                            SUM(aul.request_size + aul.response_size) as total_bandwidth
                        FROM license_keys lk
                        JOIN license_tiers lt ON lk.tier_id = lt.id
                        LEFT JOIN api_usage_logs aul ON lk.id = aul.license_key_id
                            AND aul.request_timestamp > %s
                        WHERE lk.license_key = %s
                        GROUP BY lk.id, lt.id
                    """, (cutoff_date, license_key))

                    result = cursor.fetchone()
                    if result:
                        return dict(result)
                    else:
                        return {}
                else:
                    # Stats for all license keys
                    cursor.execute("""
                        SELECT
                            lt.tier_name,
                            lt.display_name,
                            COUNT(DISTINCT lk.id) as total_licenses,
                            COUNT(DISTINCT CASE WHEN lk.is_active THEN lk.id END) as active_licenses,
                            COUNT(aul.id) as total_api_calls,
                            AVG(aul.processing_time_ms) as avg_processing_time,
                            SUM(aul.request_size + aul.response_size) as total_bandwidth
                        FROM license_tiers lt
                        LEFT JOIN license_keys lk ON lt.id = lk.tier_id
                        LEFT JOIN api_usage_logs aul ON lk.id = aul.license_key_id
                            AND aul.request_timestamp > %s
                        GROUP BY lt.id
                        ORDER BY lt.tier_name
                    """, (cutoff_date,))

                    results = cursor.fetchall()
                    return [dict(row) for row in results]

    def cleanup_expired_sessions(self):
        """
        Clean up expired sessions

        Returns:
            Number of sessions cleaned up
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE license_sessions
                    SET is_active = FALSE
                    WHERE is_active = TRUE
                    AND expires_at IS NOT NULL
                    AND expires_at < CURRENT_TIMESTAMP
                """)

                cleaned_count = cursor.rowcount

            conn.commit()

        print(f"[LICENSE] Cleaned up {cleaned_count} expired sessions")
        return cleaned_count

    def get_license_tiers(self) -> List[Dict[str, Any]]:
        """
        Get all available license tiers

        Returns:
            List of license tier dictionaries
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT tier_name, display_name, max_concurrent_sessions,
                           max_api_calls_per_hour, max_api_calls_per_day,
                           features_enabled, price_monthly
                    FROM license_tiers
                    ORDER BY price_monthly
                """)

                return [dict(row) for row in cursor.fetchall()]

    def check_rate_limit(self, license_key_id: int, endpoint: str = None) -> Dict[str, Any]:
        """
        Check if license key has exceeded rate limits

        Args:
            license_key_id: License key ID
            endpoint: Optional specific endpoint to check

        Returns:
            Dictionary with rate limit status
        """
        with self.db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get license tier limits
                cursor.execute("""
                    SELECT lt.max_api_calls_per_hour, lt.max_api_calls_per_day, lt.tier_name
                    FROM license_keys lk
                    JOIN license_tiers lt ON lk.tier_id = lt.id
                    WHERE lk.id = %s
                """, (license_key_id,))

                tier_info = cursor.fetchone()
                if not tier_info:
                    return {'allowed': False, 'message': 'Invalid license key'}

                # Master tier has unlimited usage
                if tier_info['tier_name'] == 'master':
                    return {'allowed': True, 'message': 'Unlimited usage'}

                max_hourly = tier_info['max_api_calls_per_hour']
                max_daily = tier_info['max_api_calls_per_day']

                # Check hourly limit
                if max_hourly > 0:
                    cursor.execute("""
                        SELECT COUNT(*) as hourly_count
                        FROM api_usage_logs
                        WHERE license_key_id = %s
                        AND request_timestamp > CURRENT_TIMESTAMP - INTERVAL '1 hour'
                    """, (license_key_id,))

                    hourly_count = cursor.fetchone()['hourly_count']
                    if hourly_count >= max_hourly:
                        return {
                            'allowed': False,
                            'message': f'Hourly rate limit exceeded ({hourly_count}/{max_hourly})'
                        }

                # Check daily limit
                if max_daily > 0:
                    cursor.execute("""
                        SELECT COUNT(*) as daily_count
                        FROM api_usage_logs
                        WHERE license_key_id = %s
                        AND request_timestamp > CURRENT_TIMESTAMP - INTERVAL '1 day'
                    """, (license_key_id,))

                    daily_count = cursor.fetchone()['daily_count']
                    if daily_count >= max_daily:
                        return {
                            'allowed': False,
                            'message': f'Daily rate limit exceeded ({daily_count}/{max_daily})'
                        }

                return {'allowed': True, 'message': 'Within rate limits'}


# Global license manager instance
license_manager = LicenseManager()

def require_license(features: List[str] = None):
    """
    Decorator to require valid license key for API endpoints

    Args:
        features: List of required features (e.g., ['sentiment', 'technical'])
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.utcnow()

            # Get session token from header or session
            session_token = request.headers.get('X-Session-Token') or session.get('session_token')

            if not session_token:
                # Debug information
                print(f"[DEBUG] Session token not found. Headers: {dict(request.headers)}")
                print(f"[DEBUG] Flask session: {dict(session)}")
                return jsonify({
                    'error': 'Session token required',
                    'message': 'Please provide a valid session token'
                }), 401

            # Validate session
            session_validation = license_manager.validate_session(session_token)
            if not session_validation['valid']:
                return jsonify({
                    'error': 'Invalid session',
                    'message': session_validation['message']
                }), 401

            # Check rate limits
            rate_limit_check = license_manager.check_rate_limit(
                session_validation['license_key_id'],
                request.endpoint
            )

            if not rate_limit_check['allowed']:
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'message': rate_limit_check['message']
                }), 429

            # Check feature permissions
            if features:
                enabled_features = session_validation['features_enabled'] or {}
                for feature in features:
                    if not enabled_features.get(feature, False):
                        return jsonify({
                            'error': 'Feature not available',
                            'message': f'Your license does not include access to {feature} features'
                        }), 403

            # Store session info in Flask g object for use in endpoint
            g.session_token = session_token
            g.license_key_id = session_validation['license_key_id']
            g.tier_name = session_validation['tier_name']
            g.features_enabled = session_validation['features_enabled']

            # Execute the original function
            response = f(*args, **kwargs)

            # Log API usage
            end_time = datetime.utcnow()
            processing_time = int((end_time - start_time).total_seconds() * 1000)

            # Get response size (approximation)
            print(f"[DEBUG] Response type: {type(response)}")
            print("AAAA",response.get_json(silent=True))
            response_data = response if isinstance(response.get_json(silent=True), (dict, list)) else response.get_json(silent=True)
            response_size = len(str(response_data)) if response_data else 0

            license_manager.log_api_usage(
                session_token=session_token,
                endpoint=request.endpoint or request.path,
                method=request.method,
                request_size=len(request.get_data()),
                response_size=response_size,
                response_status=response[1] if isinstance(response, tuple) else 200,
                processing_time_ms=processing_time,
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )

            return response

        return decorated_function
    return decorator

def admin_required(f):
    """
    Decorator to require admin access (master license)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.headers.get('X-Session-Token') or session.get('session_token')

        if not session_token:
            return jsonify({'error': 'Session token required'}), 401

        session_validation = license_manager.validate_session(session_token)
        if not session_validation['valid']:
            return jsonify({'error': 'Invalid session'}), 401

        # Check for admin feature
        features_enabled = session_validation['features_enabled'] or {}
        if not features_enabled.get('admin', False):
            return jsonify({
                'error': 'Admin access required',
                'message': 'This endpoint requires master license privileges'
            }), 403

        g.session_token = session_token
        g.license_key_id = session_validation['license_key_id']
        g.tier_name = session_validation['tier_name']
        g.features_enabled = session_validation['features_enabled']

        return f(*args, **kwargs)

    return decorated_function