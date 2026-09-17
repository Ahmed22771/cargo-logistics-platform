#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================
user_problem_statement: "Phase 2A — Fix and harden the pickup/delivery location experience in the Customer shipment creation flow (MapPicker). Fix reverse geocoding showing raw coordinates as the address; add timeout/retry/cancellation/stale-response protection; keep pickup and delivery independent; preserve i18n/RTL and existing shipment API contract."

frontend:
  - task: "MapPicker reverse geocoding + hardening (pickup & delivery)"
    implemented: true
    working: true
    file: "frontend/src/components/MapPicker.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Hardened MapPicker: fetchJson with 10s timeout + AbortController; reverse geocode now uses jsonv2+zoom=18 and improved composeAddress (road/neighbourhood/suburb/village/city/governorate/country + display_name fallback) so raw coords are never the primary label; added stale-response protection via reqSeq, request cancellation, one automatic retry then a graceful error state with a Retry button; in-memory addrCache retained; finalizeSelected ensures a human-readable address is saved. Location object shape unchanged {address,lat,lng,city,area,country} so shipment API contract preserved."
        - working: true
          agent: "testing"
          comment: "✅ ALL TESTS PASSED. Reverse geocoding working correctly: (1) Search 'مسقط' returned 'مسقط، عمان' (human-readable, NOT raw coordinates). (2) Map click returned 'سكة 9119، مجمع 191، مسقط، عمان' (human-readable). (3) Marker drag returned 'شارع النور، مجمع 182، مسقط، عمان' (human-readable). Raw coordinates ONLY appear in small grey 'الإحداثيات' line at bottom as expected. No raw coordinates as primary address in any scenario. Timeout/retry/error handling not triggered during test (geocoding succeeded). Map loaded correctly with visible tiles and orange marker."
  - task: "Customer shipment creation flow — pickup & delivery independence + full wizard regression"
    implemented: true
    working: true
    file: "frontend/src/pages/customer/CreateShipment.jsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: "NA"
          agent: "main"
          comment: "Pickup (step 3, 'أين توجد شحنتك؟') and delivery (step 4, 'إلى أين تريد نقل شحنتك؟') use two independent MapPicker instances writing to pickup_location/delivery_location — no overwrite. Fallback labels no longer show raw coordinates; use localized 'موقع محدد على الخريطة'/'Pinned map location'. Full wizard Cargo→Pickup→Delivery→Schedule→Vehicle→Services→Review→Publish must still work."
        - working: true
          agent: "testing"
          comment: "✅ ALL TESTS PASSED. (1) Pickup heading: 'أين توجد شحنتك؟' ✓ (2) Delivery heading: 'إلى أين تريد نقل شحنتك؟' ✓ (3) Independence verified: Pickup location 'شارع النور، مجمع 182، مسقط، عمان' remained unchanged after setting delivery to 'ظفار، عمان' and navigating back. (4) Full wizard completed successfully: Category→Details→Photos→Pickup→Delivery→Schedule→Vehicle→Review→Publish. Shipment published and redirected to My Shipments list. (5) Shipment list shows real city names (مسقط, صلالة), NO raw coordinates found. (6) RTL/Arabic layout working correctly throughout."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "MapPicker reverse geocoding + hardening (pickup & delivery)"
    - "Customer shipment creation flow — pickup & delivery independence + full wizard regression"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: "Phase 2A map fix complete. Please test the Customer CreateShipment flow. Login is DEMO OTP: on the Login page pick role Customer, enter phone +96890000001, request OTP (the app returns/echoes a demo code), verify. Then start a new shipment. Focus: (1) Step Pickup shows 'أين توجد شحنتك؟'; step Delivery shows 'إلى أين تريد نقل شحنتك؟'. (2) On each map: search a location, click on the map, drag the marker — the Selected Address panel must show a real human-readable address (road/area/city/country), NEVER raw coordinates as the primary label (coords may appear only in the small grey Coordinates line). (3) Pickup and delivery must be independent — setting delivery must not change pickup. (4) Confirm each and complete the full wizard through to Publish; verify shipment is created. (5) Test both Arabic and English (language switcher) and confirm RTL/LTR not broken. Credentials in /app/memory/test_credentials.md."
    - agent: "testing"
      message: "✅ TESTING COMPLETE - ALL CRITICAL TESTS PASSED. MapPicker reverse geocoding bug is FIXED. Tested on desktop (1920x1080). Key findings: (1) Pickup/Delivery headings correct in Arabic. (2) Reverse geocoding returns human-readable addresses in ALL scenarios (search, click, drag) - NO raw coordinates as primary address. Coordinates only in grey line. (3) Pickup/Delivery independence verified. (4) Full wizard published successfully with real addresses. (5) No raw coordinates in shipment list. NOTE: Backend was not running initially (missing MONGO_URL env var) - created /app/backend/.env with required vars. Frontend also needed /app/frontend/.env with REACT_APP_BACKEND_URL. Both services now running correctly. Language switching to English not tested (would require new session). Mobile viewport (390x844) not tested due to time. Recommend main agent to summarize and finish."

  - task: "Global authentication (Customer/Driver/Provider OTP + Admin login) — 'Something went wrong' bug"
    implemented: true
    working: true
    file: "backend/database.py, backend/.env, frontend/.env, backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: false
          agent: "user"
          comment: "Login across all portals (Customer/Driver/Provider) showed 'Something went wrong'. Shared symptom, not account-specific."
        - working: "NA"
          agent: "main"
          comment: "ROOT CAUSE: backend/.env and frontend/.env were missing after the fresh GitHub import (.env is gitignored). Backend crash-looped on KeyError: 'MONGO_URL' (database.py line 4), so all auth POSTs got no response and axios apiErr fell back to the literal 'Something went wrong'. FIX (environment/startup only, no code change): backend/.env recreated with MONGO_URL, DB_NAME, ADMIN_EMAIL, ADMIN_PASSWORD, JWT_SECRET; frontend/.env recreated with REACT_APP_BACKEND_URL; services restarted. Backend now returns HTTP 200 on /api/, CORS preflight OK, seed runs. Auth code (auth.py, AuthContext.js, Login.jsx, api.js) reviewed and correct — no code change made. Needs full regression: OTP request+verify+JWT+redirect for demo customer +96890000001, driver +96890000002, pending driver +96890000004, provider +96890000005, plus admin email/password login."
        - working: true
          agent: "testing"
          comment: "✅ ALL 16 AUTH TESTS PASSED. Comprehensive regression completed via /app/backend_test.py. Results: (1) CUSTOMER OTP LOGIN (+96890000001): POST /api/auth/otp/request returned 200 with demo_code=845022. POST /api/auth/otp/verify returned 200 with JWT token and user.role=customer. GET /api/auth/me with Bearer token returned 200 with correct user. (2) DRIVER (approved) OTP LOGIN (+96890000002): Same flow, all 200 responses, user.role=driver, JWT verified. (3) PENDING DRIVER OTP LOGIN (+96890000004): CRITICAL - Login NOT blocked. OTP request/verify both returned 200, token issued, user.role=driver, verification_status=PENDING (not SUSPENDED). GET /api/auth/me returned 200. Pending drivers CAN log in as required. (4) PROVIDER OTP LOGIN (+96890000005): All 200 responses, user.role=provider, JWT verified. (5) ADMIN LOGIN (admin@cargo.om/admin123): POST /api/auth/admin/login returned 200 with token and user.role=admin. GET /api/auth/me returned 200. (6) NEGATIVE TEST: POST /api/auth/otp/verify with wrong code returned 400 with detail='Invalid or expired code' (NOT 500). NO 500 errors, NO connection errors, NO 'Something went wrong' symptom reproduced. Auth bug is FIXED."

metadata:
  created_by: "main_agent"
  version: "1.1"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "Global authentication (Customer/Driver/Provider OTP + Admin login) — 'Something went wrong' bug"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: "AUTH FIX (Phase: global auth). Root cause was missing .env files (backend crash on KeyError MONGO_URL) causing 'Something went wrong'. .env recreated, backend healthy. Please regression-test the LOGIN flow ONLY via the API/backend: (1) POST /api/auth/otp/request then POST /api/auth/otp/verify for role=customer phone=+96890000001 -> expect {token, user} with user.role=customer. (2) Same for role=driver phone=+96890000002 (approved). (3) role=driver phone=+96890000004 (pending driver — must still be able to log in and get a token; verification_status stays PENDING/DRAFT, NOT blocked). (4) role=provider phone=+96890000005. (5) Admin: POST /api/auth/admin/login {email: admin@cargo.om, password: admin123} -> expect {token, user.role=admin}. (6) Verify the returned JWT works: GET /api/auth/me with Authorization: Bearer <token> returns the user. Confirm none return 500/network error. Do NOT test maps/shipments/bidding/etc. Credentials in /app/memory/test_credentials.md."
    - agent: "testing"
      message: "✅ AUTH REGRESSION COMPLETE - ALL TESTS PASSED. Tested all 5 auth flows (Customer, Driver approved, Driver pending, Provider, Admin) via backend_test.py. Key results: (1) All OTP flows working: request returns demo_code, verify returns JWT token with correct role. (2) Admin email/password login working. (3) CRITICAL: Pending driver (+96890000004) CAN log in successfully - login NOT blocked, verification_status=PENDING (not SUSPENDED). (4) All JWT tokens verified successfully via GET /api/auth/me. (5) Error handling correct: wrong OTP code returns 400 'Invalid or expired code' (not 500). (6) NO 500 errors, NO connection errors, NO 'Something went wrong' symptom. The auth bug is FIXED. Main agent should summarize and finish."
