#!/usr/bin/env python3
"""
CARGO Chat Core Backend Test Suite
Tests all 12 scenarios [A] through [L] as specified in the review request.
"""
import requests
import json
from datetime import datetime, timedelta

# Base URL from frontend/.env
BASE_URL = "https://6d1774a7-93f3-4112-a01b-a68cdfddb960.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@cargo.om"
ADMIN_PASSWORD = "admin123"
CUSTOMER_A_PHONE = "+96890000001"
DRIVER_A_PHONE = "+96890000002"
DRIVER_B_PHONE = "+96890000003"  # Second driver for authorization tests
CUSTOMER_B_PHONE = "+96895555777"  # Different customer for authorization tests

# Global state
admin_token = None
customer_a_token = None
driver_a_token = None
driver_b_token = None
customer_b_token = None
trip_id = None
shipment_id = None
conversation_id = None
first_message_created_at = None


def log_test(section, test_name, passed, details=""):
    """Log test result with clear formatting."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n[{section}] {test_name}: {status}")
    if details:
        print(f"    {details}")


def login_admin():
    """Login as super_admin."""
    global admin_token
    print("\n" + "="*80)
    print("SETUP: Admin Login")
    print("="*80)
    
    resp = requests.post(f"{BASE_URL}/auth/admin/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    
    if resp.status_code == 200:
        data = resp.json()
        admin_token = data.get("token")
        print(f"✅ Admin login successful. Token: {admin_token[:20]}...")
        return True
    else:
        print(f"❌ Admin login failed: {resp.status_code} {resp.text}")
        return False


def otp_login(phone, role):
    """Login via OTP demo flow."""
    print(f"\n--- OTP Login: {role} {phone} ---")
    
    # Request OTP
    resp = requests.post(f"{BASE_URL}/auth/otp/request", json={
        "phone": phone,
        "role": role
    })
    
    if resp.status_code != 200:
        print(f"❌ OTP request failed: {resp.status_code} {resp.text}")
        return None
    
    data = resp.json()
    demo_code = data.get("demo_code")
    print(f"✅ OTP request successful. Demo code: {demo_code}")
    
    # Verify OTP
    resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
        "phone": phone,
        "role": role,
        "code": demo_code
    })
    
    if resp.status_code != 200:
        print(f"❌ OTP verify failed: {resp.status_code} {resp.text}")
        return None
    
    data = resp.json()
    token = data.get("token")
    user = data.get("user")
    print(f"✅ OTP verify successful. Token: {token[:20]}... User: {user.get('name')}")
    return token


def setup_trip():
    """Setup a trip between customer A and driver A for testing."""
    global customer_a_token, driver_a_token, trip_id, shipment_id
    
    print("\n" + "="*80)
    print("SETUP: Create Trip (Customer A + Driver A)")
    print("="*80)
    
    # Login customer A
    customer_a_token = otp_login(CUSTOMER_A_PHONE, "customer")
    if not customer_a_token:
        return False
    
    # Login driver A
    driver_a_token = otp_login(DRIVER_A_PHONE, "driver")
    if not driver_a_token:
        return False
    
    # Create shipment
    pickup_date = (datetime.now() + timedelta(days=1)).isoformat()
    delivery_date = (datetime.now() + timedelta(days=2)).isoformat()
    
    resp = requests.post(f"{BASE_URL}/shipments", 
        headers={"Authorization": f"Bearer {customer_a_token}"},
        json={
            "title": "chat trip",
            "description": "",
            "category": "general",
            "weight": "100",
            "pickup_location": {
                "address": "مسقط",
                "lat": 23.58,
                "lng": 58.40
            },
            "delivery_location": {
                "address": "صلالة",
                "lat": 17.01,
                "lng": 54.09
            },
            "pickup_date": pickup_date,
            "delivery_date": delivery_date,
            "vehicle_type": "flatbed"
        }
    )
    
    if resp.status_code != 200:
        print(f"❌ Shipment creation failed: {resp.status_code} {resp.text}")
        return False
    
    data = resp.json()
    shipment_id = data.get("id")
    print(f"✅ Shipment created: {shipment_id}")
    
    # Publish shipment
    resp = requests.post(f"{BASE_URL}/shipments/{shipment_id}/publish",
        headers={"Authorization": f"Bearer {customer_a_token}"}
    )
    
    if resp.status_code != 200:
        print(f"❌ Shipment publish failed: {resp.status_code} {resp.text}")
        return False
    
    print(f"✅ Shipment published")
    
    # Driver A submits bid
    resp = requests.post(f"{BASE_URL}/shipments/{shipment_id}/bids",
        headers={"Authorization": f"Bearer {driver_a_token}"},
        json={"price": 40}
    )
    
    if resp.status_code != 200:
        print(f"❌ Bid submission failed: {resp.status_code} {resp.text}")
        return False
    
    data = resp.json()
    bid_id = data.get("id")
    print(f"✅ Bid submitted: {bid_id}")
    
    # Customer accepts bid
    resp = requests.post(f"{BASE_URL}/bids/{bid_id}/accept",
        headers={"Authorization": f"Bearer {customer_a_token}"}
    )
    
    if resp.status_code != 200:
        print(f"❌ Bid acceptance failed: {resp.status_code} {resp.text}")
        return False
    
    data = resp.json()
    trip_id = data.get("id")  # The response is the trip object itself, so id is the trip_id
    print(f"✅ Bid accepted. Trip created: {trip_id}")
    
    return True


def test_a_idempotent_create():
    """[A] Idempotent create: same conversation.id for same trip."""
    print("\n" + "="*80)
    print("[A] IDEMPOTENT CREATE")
    print("="*80)
    
    global conversation_id
    
    # Customer A creates conversation
    resp1 = requests.post(f"{BASE_URL}/chat/conversations/context",
        headers={"Authorization": f"Bearer {customer_a_token}"},
        json={"trip_id": trip_id}
    )
    
    passed = resp1.status_code == 200
    if passed:
        data1 = resp1.json()
        conv_id_1 = data1.get("id")
        participants = data1.get("participants", [])
        trip_id_field = data1.get("trip_id")
        shipment_id_field = data1.get("shipment_id")
        unread = data1.get("unread", 0)
        
        log_test("A", "Customer A first POST /chat/conversations/context", True,
                f"HTTP 200, conversation.id={conv_id_1}, participants={len(participants)}, trip_id={trip_id_field}, shipment_id={shipment_id_field}, unread={unread}")
        
        # Customer A creates again (idempotent)
        resp2 = requests.post(f"{BASE_URL}/chat/conversations/context",
            headers={"Authorization": f"Bearer {customer_a_token}"},
            json={"trip_id": trip_id}
        )
        
        if resp2.status_code == 200:
            data2 = resp2.json()
            conv_id_2 = data2.get("id")
            
            if conv_id_1 == conv_id_2:
                log_test("A", "Customer A second POST (idempotent)", True,
                        f"HTTP 200, SAME conversation.id={conv_id_2}")
                conversation_id = conv_id_1
            else:
                log_test("A", "Customer A second POST (idempotent)", False,
                        f"Different conversation IDs: {conv_id_1} vs {conv_id_2}")
                return False
        else:
            log_test("A", "Customer A second POST", False,
                    f"HTTP {resp2.status_code}: {resp2.text}")
            return False
        
        # Driver A creates (should get same conversation)
        resp3 = requests.post(f"{BASE_URL}/chat/conversations/context",
            headers={"Authorization": f"Bearer {driver_a_token}"},
            json={"trip_id": trip_id}
        )
        
        if resp3.status_code == 200:
            data3 = resp3.json()
            conv_id_3 = data3.get("id")
            
            if conv_id_1 == conv_id_3:
                log_test("A", "Driver A POST (same trip)", True,
                        f"HTTP 200, SAME conversation.id={conv_id_3}")
            else:
                log_test("A", "Driver A POST (same trip)", False,
                        f"Different conversation IDs: {conv_id_1} vs {conv_id_3}")
                return False
        else:
            log_test("A", "Driver A POST", False,
                    f"HTTP {resp3.status_code}: {resp3.text}")
            return False
        
        return True
    else:
        log_test("A", "Customer A first POST", False,
                f"HTTP {resp1.status_code}: {resp1.text}")
        return False


def test_b_send_message():
    """[B] Send message: customer sends, message appears."""
    print("\n" + "="*80)
    print("[B] SEND MESSAGE")
    print("="*80)
    
    global first_message_created_at
    
    # Customer A sends message
    resp = requests.post(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {customer_a_token}"},
        json={"text": "hello from customer"}
    )
    
    if resp.status_code == 200:
        data = resp.json()
        msg_id = data.get("id")
        sender_id = data.get("sender_id")
        sender_role = data.get("sender_role")
        text = data.get("text")
        created_at = data.get("created_at")
        first_message_created_at = created_at
        
        log_test("B", "Customer A POST message", True,
                f"HTTP 200, message.id={msg_id}, sender_role={sender_role}, text='{text}', created_at={created_at}")
    else:
        log_test("B", "Customer A POST message", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    # Get messages
    resp = requests.get(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {customer_a_token}"}
    )
    
    if resp.status_code == 200:
        messages = resp.json()
        if len(messages) == 1 and messages[0].get("text") == "hello from customer":
            log_test("B", "GET messages", True,
                    f"HTTP 200, array length=1, message text matches")
            return True
        else:
            log_test("B", "GET messages", False,
                    f"Expected 1 message with text 'hello from customer', got {len(messages)} messages")
            return False
    else:
        log_test("B", "GET messages", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False


def test_c_second_participant():
    """[C] Second participant sees it: driver sees unread=1, can mark read."""
    print("\n" + "="*80)
    print("[C] SECOND PARTICIPANT SEES MESSAGE")
    print("="*80)
    
    # Driver A gets conversations list
    resp = requests.get(f"{BASE_URL}/chat/conversations",
        headers={"Authorization": f"Bearer {driver_a_token}"}
    )
    
    if resp.status_code == 200:
        convs = resp.json()
        target_conv = None
        for c in convs:
            if c.get("id") == conversation_id:
                target_conv = c
                break
        
        if target_conv:
            unread = target_conv.get("unread", 0)
            last_msg_preview = target_conv.get("last_message_preview", "")
            
            if unread == 1 and "hello from customer" in last_msg_preview:
                log_test("C", "Driver A GET conversations", True,
                        f"HTTP 200, found conversation with unread=1, last_message_preview='{last_msg_preview}'")
            else:
                log_test("C", "Driver A GET conversations", False,
                        f"Expected unread=1 and preview containing 'hello from customer', got unread={unread}, preview='{last_msg_preview}'")
                return False
        else:
            log_test("C", "Driver A GET conversations", False,
                    f"Conversation {conversation_id} not found in list")
            return False
    else:
        log_test("C", "Driver A GET conversations", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    # Driver A gets messages
    resp = requests.get(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {driver_a_token}"}
    )
    
    if resp.status_code == 200:
        messages = resp.json()
        if len(messages) == 1 and messages[0].get("text") == "hello from customer":
            log_test("C", "Driver A GET messages", True,
                    f"HTTP 200, sees the customer message")
        else:
            log_test("C", "Driver A GET messages", False,
                    f"Expected 1 message, got {len(messages)}")
            return False
    else:
        log_test("C", "Driver A GET messages", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    # Driver A marks as read
    resp = requests.post(f"{BASE_URL}/chat/conversations/{conversation_id}/read",
        headers={"Authorization": f"Bearer {driver_a_token}"}
    )
    
    if resp.status_code == 200:
        log_test("C", "Driver A POST read", True, "HTTP 200")
    else:
        log_test("C", "Driver A POST read", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    # Driver A gets conversations again (unread should be 0)
    resp = requests.get(f"{BASE_URL}/chat/conversations",
        headers={"Authorization": f"Bearer {driver_a_token}"}
    )
    
    if resp.status_code == 200:
        convs = resp.json()
        target_conv = None
        for c in convs:
            if c.get("id") == conversation_id:
                target_conv = c
                break
        
        if target_conv:
            unread = target_conv.get("unread", 0)
            if unread == 0:
                log_test("C", "Driver A GET conversations (after read)", True,
                        f"HTTP 200, unread=0")
                return True
            else:
                log_test("C", "Driver A GET conversations (after read)", False,
                        f"Expected unread=0, got unread={unread}")
                return False
        else:
            log_test("C", "Driver A GET conversations (after read)", False,
                    f"Conversation not found")
            return False
    else:
        log_test("C", "Driver A GET conversations (after read)", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False


def test_d_reply_delta():
    """[D] Reply + delta polling: driver replies, customer gets delta."""
    print("\n" + "="*80)
    print("[D] REPLY + DELTA POLLING")
    print("="*80)
    
    # Driver A sends reply
    resp = requests.post(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {driver_a_token}"},
        json={"text": "reply from driver"}
    )
    
    if resp.status_code == 200:
        data = resp.json()
        log_test("D", "Driver A POST reply", True,
                f"HTTP 200, message.id={data.get('id')}, text='{data.get('text')}'")
    else:
        log_test("D", "Driver A POST reply", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    # Customer A gets messages with delta (after first message timestamp)
    resp = requests.get(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {customer_a_token}"},
        params={"after": first_message_created_at}
    )
    
    if resp.status_code == 200:
        messages = resp.json()
        if len(messages) == 1 and messages[0].get("text") == "reply from driver":
            log_test("D", "Customer A GET messages?after=", True,
                    f"HTTP 200, delta works, array length=1, contains only driver reply")
            return True
        else:
            log_test("D", "Customer A GET messages?after=", False,
                    f"Expected 1 message 'reply from driver', got {len(messages)} messages: {[m.get('text') for m in messages]}")
            return False
    else:
        log_test("D", "Customer A GET messages?after=", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False


def test_e_notifications():
    """[E] Notifications: both parties get chat_message notifications."""
    print("\n" + "="*80)
    print("[E] NOTIFICATIONS")
    print("="*80)
    
    # Driver A gets notifications (should have one from customer's first message)
    resp = requests.get(f"{BASE_URL}/notifications",
        headers={"Authorization": f"Bearer {driver_a_token}"}
    )
    
    if resp.status_code == 200:
        notifications = resp.json()
        chat_notifs = [n for n in notifications if n.get("type") == "chat_message" 
                      and n.get("meta", {}).get("conversation_id") == conversation_id]
        
        if len(chat_notifs) >= 1:
            log_test("E", "Driver A GET notifications", True,
                    f"HTTP 200, found {len(chat_notifs)} chat_message notification(s) for conversation")
        else:
            log_test("E", "Driver A GET notifications", False,
                    f"Expected at least 1 chat_message notification, found {len(chat_notifs)}")
            return False
    else:
        log_test("E", "Driver A GET notifications", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    # Customer A gets notifications (should have one from driver's reply)
    resp = requests.get(f"{BASE_URL}/notifications",
        headers={"Authorization": f"Bearer {customer_a_token}"}
    )
    
    if resp.status_code == 200:
        notifications = resp.json()
        chat_notifs = [n for n in notifications if n.get("type") == "chat_message" 
                      and n.get("meta", {}).get("conversation_id") == conversation_id]
        
        if len(chat_notifs) >= 1:
            log_test("E", "Customer A GET notifications", True,
                    f"HTTP 200, found {len(chat_notifs)} chat_message notification(s) for conversation")
            return True
        else:
            log_test("E", "Customer A GET notifications", False,
                    f"Expected at least 1 chat_message notification, found {len(chat_notifs)}")
            return False
    else:
        log_test("E", "Customer A GET notifications", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False


def test_f_auth_different_customer():
    """[F] Authorization - different customer cannot access."""
    print("\n" + "="*80)
    print("[F] AUTHORIZATION - DIFFERENT CUSTOMER")
    print("="*80)
    
    global customer_b_token
    
    # Try to login customer B (may not exist, will create via OTP)
    customer_b_token = otp_login(CUSTOMER_B_PHONE, "customer")
    if not customer_b_token:
        log_test("F", "Customer B login", False, "Could not login customer B")
        return False
    
    log_test("F", "Customer B login", True, "Successfully logged in as different customer")
    
    # Customer B tries to GET messages
    resp = requests.get(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {customer_b_token}"}
    )
    
    if resp.status_code == 403:
        detail = resp.json().get("detail", "")
        if "NOT_A_PARTICIPANT" in detail:
            log_test("F", "Customer B GET messages", True,
                    f"HTTP 403 NOT_A_PARTICIPANT (correct)")
        else:
            log_test("F", "Customer B GET messages", False,
                    f"HTTP 403 but wrong detail: {detail}")
            return False
    else:
        log_test("F", "Customer B GET messages", False,
                f"Expected HTTP 403, got {resp.status_code}: {resp.text}")
        return False
    
    # Customer B tries to POST message
    resp = requests.post(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {customer_b_token}"},
        json={"text": "unauthorized message"}
    )
    
    if resp.status_code == 403:
        log_test("F", "Customer B POST message", True,
                f"HTTP 403 (correct)")
    else:
        log_test("F", "Customer B POST message", False,
                f"Expected HTTP 403, got {resp.status_code}: {resp.text}")
        return False
    
    # Customer B tries to POST context with same trip_id
    resp = requests.post(f"{BASE_URL}/chat/conversations/context",
        headers={"Authorization": f"Bearer {customer_b_token}"},
        json={"trip_id": trip_id}
    )
    
    if resp.status_code == 403:
        log_test("F", "Customer B POST context", True,
                f"HTTP 403 (correct)")
    else:
        log_test("F", "Customer B POST context", False,
                f"Expected HTTP 403, got {resp.status_code}: {resp.text}")
        return False
    
    # Customer B GET conversations (should NOT contain this conversation)
    resp = requests.get(f"{BASE_URL}/chat/conversations",
        headers={"Authorization": f"Bearer {customer_b_token}"}
    )
    
    if resp.status_code == 200:
        convs = resp.json()
        found = any(c.get("id") == conversation_id for c in convs)
        if not found:
            log_test("F", "Customer B GET conversations", True,
                    f"HTTP 200, conversation NOT in list (correct)")
            return True
        else:
            log_test("F", "Customer B GET conversations", False,
                    f"Conversation should NOT be in list but was found")
            return False
    else:
        log_test("F", "Customer B GET conversations", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False


def test_g_auth_different_driver():
    """[G] Authorization - different driver cannot access."""
    print("\n" + "="*80)
    print("[G] AUTHORIZATION - DIFFERENT DRIVER")
    print("="*80)
    
    global driver_b_token
    
    # Try to login driver B
    driver_b_token = otp_login(DRIVER_B_PHONE, "driver")
    if not driver_b_token:
        log_test("G", "Driver B login", False, "Could not login driver B")
        return False
    
    log_test("G", "Driver B login", True, "Successfully logged in as different driver")
    
    # Driver B tries to GET messages
    resp = requests.get(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {driver_b_token}"}
    )
    
    if resp.status_code == 403:
        detail = resp.json().get("detail", "")
        if "NOT_A_PARTICIPANT" in detail:
            log_test("G", "Driver B GET messages", True,
                    f"HTTP 403 NOT_A_PARTICIPANT (correct)")
            return True
        else:
            log_test("G", "Driver B GET messages", False,
                    f"HTTP 403 but wrong detail: {detail}")
            return False
    else:
        log_test("G", "Driver B GET messages", False,
                f"Expected HTTP 403, got {resp.status_code}: {resp.text}")
        return False


def test_h_admin_access():
    """[H] Admin without dispute: super_admin can access."""
    print("\n" + "="*80)
    print("[H] ADMIN ACCESS (WITHOUT DISPUTE)")
    print("="*80)
    
    # Admin GET conversation
    resp = requests.get(f"{BASE_URL}/chat/conversations/{conversation_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if resp.status_code == 200:
        data = resp.json()
        log_test("H", "Admin GET conversation", True,
                f"HTTP 200, conversation.id={data.get('id')}")
    else:
        log_test("H", "Admin GET conversation", False,
                f"Expected HTTP 200, got {resp.status_code}: {resp.text}")
        return False
    
    # Admin GET conversations list
    resp = requests.get(f"{BASE_URL}/chat/conversations",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if resp.status_code == 200:
        convs = resp.json()
        found = any(c.get("id") == conversation_id for c in convs)
        if found:
            log_test("H", "Admin GET conversations", True,
                    f"HTTP 200, conversation in list (correct)")
            return True
        else:
            log_test("H", "Admin GET conversations", False,
                    f"Conversation should be in admin's list but was not found")
            return False
    else:
        log_test("H", "Admin GET conversations", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False


def test_i_validation():
    """[I] Validation: empty text, whitespace, too long."""
    print("\n" + "="*80)
    print("[I] VALIDATION")
    print("="*80)
    
    # Empty text
    resp = requests.post(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {customer_a_token}"},
        json={"text": ""}
    )
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if "MESSAGE_EMPTY" in detail:
            log_test("I", "Empty text", True, f"HTTP 400 MESSAGE_EMPTY (correct)")
        else:
            log_test("I", "Empty text", False, f"HTTP 400 but wrong detail: {detail}")
            return False
    else:
        log_test("I", "Empty text", False,
                f"Expected HTTP 400, got {resp.status_code}: {resp.text}")
        return False
    
    # Whitespace only
    resp = requests.post(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {customer_a_token}"},
        json={"text": "   "}
    )
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if "MESSAGE_EMPTY" in detail:
            log_test("I", "Whitespace only", True, f"HTTP 400 MESSAGE_EMPTY (correct)")
        else:
            log_test("I", "Whitespace only", False, f"HTTP 400 but wrong detail: {detail}")
            return False
    else:
        log_test("I", "Whitespace only", False,
                f"Expected HTTP 400, got {resp.status_code}: {resp.text}")
        return False
    
    # Too long (> 4000 chars)
    long_text = "x" * 5000
    resp = requests.post(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {customer_a_token}"},
        json={"text": long_text}
    )
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if "MESSAGE_TOO_LONG" in detail:
            log_test("I", "Text too long (5000 chars)", True,
                    f"HTTP 400 MESSAGE_TOO_LONG (correct)")
            return True
        else:
            log_test("I", "Text too long", False, f"HTTP 400 but wrong detail: {detail}")
            return False
    else:
        log_test("I", "Text too long", False,
                f"Expected HTTP 400, got {resp.status_code}: {resp.text}")
        return False


def test_j_context_before_trip():
    """[J] Context from shipment BEFORE trip: 400 error."""
    print("\n" + "="*80)
    print("[J] CONTEXT FROM SHIPMENT BEFORE TRIP")
    print("="*80)
    
    # Create a new shipment but don't accept any bid
    pickup_date = (datetime.now() + timedelta(days=1)).isoformat()
    delivery_date = (datetime.now() + timedelta(days=2)).isoformat()
    
    resp = requests.post(f"{BASE_URL}/shipments",
        headers={"Authorization": f"Bearer {customer_a_token}"},
        json={
            "title": "test shipment no trip",
            "description": "",
            "category": "general",
            "weight": "50",
            "pickup_location": {
                "address": "مسقط",
                "lat": 23.58,
                "lng": 58.40
            },
            "delivery_location": {
                "address": "صلالة",
                "lat": 17.01,
                "lng": 54.09
            },
            "pickup_date": pickup_date,
            "delivery_date": delivery_date,
            "vehicle_type": "flatbed"
        }
    )
    
    if resp.status_code != 200:
        log_test("J", "Create shipment without trip", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    new_shipment_id = data.get("id")
    log_test("J", "Create shipment without trip", True,
            f"HTTP 200, shipment.id={new_shipment_id}")
    
    # Try to create conversation with shipment_id (no trip yet)
    resp = requests.post(f"{BASE_URL}/chat/conversations/context",
        headers={"Authorization": f"Bearer {customer_a_token}"},
        json={"shipment_id": new_shipment_id}
    )
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if "CHAT_NOT_AVAILABLE_BEFORE_TRIP" in detail:
            log_test("J", "POST context with shipment_id (no trip)", True,
                    f"HTTP 400 CHAT_NOT_AVAILABLE_BEFORE_TRIP (correct)")
            return True
        else:
            log_test("J", "POST context with shipment_id (no trip)", False,
                    f"HTTP 400 but wrong detail: {detail}")
            return False
    else:
        log_test("J", "POST context with shipment_id (no trip)", False,
                f"Expected HTTP 400, got {resp.status_code}: {resp.text}")
        return False


def test_k_context_from_shipment_with_trip():
    """[K] Context from shipment WITH trip: same conversation."""
    print("\n" + "="*80)
    print("[K] CONTEXT FROM SHIPMENT WITH TRIP")
    print("="*80)
    
    # Use original shipment_id (which has a trip)
    resp = requests.post(f"{BASE_URL}/chat/conversations/context",
        headers={"Authorization": f"Bearer {customer_a_token}"},
        json={"shipment_id": shipment_id}
    )
    
    if resp.status_code == 200:
        data = resp.json()
        conv_id = data.get("id")
        
        if conv_id == conversation_id:
            log_test("K", "POST context with shipment_id (with trip)", True,
                    f"HTTP 200, SAME conversation.id={conv_id}")
            return True
        else:
            log_test("K", "POST context with shipment_id (with trip)", False,
                    f"Expected conversation.id={conversation_id}, got {conv_id}")
            return False
    else:
        log_test("K", "POST context with shipment_id (with trip)", False,
                f"Expected HTTP 200, got {resp.status_code}: {resp.text}")
        return False


def test_l_cross_trip_isolation():
    """[L] Cross-trip isolation: different trips have different conversations."""
    print("\n" + "="*80)
    print("[L] CROSS-TRIP ISOLATION")
    print("="*80)
    
    # Create another trip between customer A and driver A
    pickup_date = (datetime.now() + timedelta(days=3)).isoformat()
    delivery_date = (datetime.now() + timedelta(days=4)).isoformat()
    
    resp = requests.post(f"{BASE_URL}/shipments",
        headers={"Authorization": f"Bearer {customer_a_token}"},
        json={
            "title": "second chat trip",
            "description": "",
            "category": "general",
            "weight": "150",
            "pickup_location": {
                "address": "مسقط",
                "lat": 23.58,
                "lng": 58.40
            },
            "delivery_location": {
                "address": "صلالة",
                "lat": 17.01,
                "lng": 54.09
            },
            "pickup_date": pickup_date,
            "delivery_date": delivery_date,
            "vehicle_type": "flatbed"
        }
    )
    
    if resp.status_code != 200:
        log_test("L", "Create second shipment", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    second_shipment_id = data.get("id")
    log_test("L", "Create second shipment", True, f"HTTP 200, shipment.id={second_shipment_id}")
    
    # Publish
    resp = requests.post(f"{BASE_URL}/shipments/{second_shipment_id}/publish",
        headers={"Authorization": f"Bearer {customer_a_token}"}
    )
    
    if resp.status_code != 200:
        log_test("L", "Publish second shipment", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    log_test("L", "Publish second shipment", True, "HTTP 200")
    
    # Driver A bids
    resp = requests.post(f"{BASE_URL}/shipments/{second_shipment_id}/bids",
        headers={"Authorization": f"Bearer {driver_a_token}"},
        json={"price": 50}
    )
    
    if resp.status_code != 200:
        log_test("L", "Driver A bid on second shipment", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    second_bid_id = data.get("id")
    log_test("L", "Driver A bid on second shipment", True, f"HTTP 200, bid.id={second_bid_id}")
    
    # Customer accepts
    resp = requests.post(f"{BASE_URL}/bids/{second_bid_id}/accept",
        headers={"Authorization": f"Bearer {customer_a_token}"}
    )
    
    if resp.status_code != 200:
        log_test("L", "Accept second bid", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    second_trip_id = data.get("id")  # The response is the trip object itself
    log_test("L", "Accept second bid", True, f"HTTP 200, trip.id={second_trip_id}")
    
    # Create conversation for second trip
    resp = requests.post(f"{BASE_URL}/chat/conversations/context",
        headers={"Authorization": f"Bearer {customer_a_token}"},
        json={"trip_id": second_trip_id}
    )
    
    if resp.status_code != 200:
        log_test("L", "POST context for second trip", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    data = resp.json()
    second_conv_id = data.get("id")
    
    if second_conv_id != conversation_id:
        log_test("L", "POST context for second trip", True,
                f"HTTP 200, DIFFERENT conversation.id={second_conv_id}")
    else:
        log_test("L", "POST context for second trip", False,
                f"Expected different conversation.id, got same: {second_conv_id}")
        return False
    
    # Get messages from first conversation (should NOT contain second trip messages)
    resp = requests.get(f"{BASE_URL}/chat/conversations/{conversation_id}/messages",
        headers={"Authorization": f"Bearer {customer_a_token}"}
    )
    
    if resp.status_code != 200:
        log_test("L", "GET first conversation messages", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    first_messages = resp.json()
    
    # Get messages from second conversation (should be empty or not contain first trip messages)
    resp = requests.get(f"{BASE_URL}/chat/conversations/{second_conv_id}/messages",
        headers={"Authorization": f"Bearer {customer_a_token}"}
    )
    
    if resp.status_code != 200:
        log_test("L", "GET second conversation messages", False,
                f"HTTP {resp.status_code}: {resp.text}")
        return False
    
    second_messages = resp.json()
    
    # Verify isolation
    first_texts = [m.get("text") for m in first_messages]
    second_texts = [m.get("text") for m in second_messages]
    
    if "hello from customer" in first_texts and "hello from customer" not in second_texts:
        log_test("L", "Cross-trip isolation verified", True,
                f"First conversation has {len(first_messages)} messages, second has {len(second_messages)} messages, no overlap")
        return True
    else:
        log_test("L", "Cross-trip isolation verified", False,
                f"Messages leaked between conversations. First: {first_texts}, Second: {second_texts}")
        return False


def main():
    """Run all Chat Core tests."""
    print("\n" + "="*80)
    print("CARGO CHAT CORE BACKEND TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Test time: {datetime.now().isoformat()}")
    
    results = {}
    
    # Setup
    if not login_admin():
        print("\n❌ FATAL: Admin login failed. Cannot proceed.")
        return
    
    if not setup_trip():
        print("\n❌ FATAL: Trip setup failed. Cannot proceed.")
        return
    
    # Run tests
    results["A"] = test_a_idempotent_create()
    results["B"] = test_b_send_message()
    results["C"] = test_c_second_participant()
    results["D"] = test_d_reply_delta()
    results["E"] = test_e_notifications()
    results["F"] = test_f_auth_different_customer()
    results["G"] = test_g_auth_different_driver()
    results["H"] = test_h_admin_access()
    results["I"] = test_i_validation()
    results["J"] = test_j_context_before_trip()
    results["K"] = test_k_context_from_shipment_with_trip()
    results["L"] = test_l_cross_trip_isolation()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for section, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"[{section}] {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL CHAT CORE TESTS PASSED")
        return True
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
