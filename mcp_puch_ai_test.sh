#!/bin/bash

# MCP Puch AI Integration Testing Script
# Tests the newly implemented MCP validate endpoint for Puch AI integration

BACKEND_URL="https://0fbf6255-bf7b-4ad7-b4ea-c5da62fa1669.preview.emergentagent.com/api"
VALID_TOKEN="kumararpit9468"
INVALID_TOKEN="wrongtoken"

echo "🚀 Starting MCP Puch AI Integration Tests..."
echo "============================================================"

PASSED=0
FAILED=0

# Function to run test
run_test() {
    local test_name="$1"
    local command="$2"
    local expected_code="$3"
    local expected_content="$4"
    
    echo -n "Testing: $test_name... "
    
    # Run the command and capture both output and status code
    response=$(eval "$command" 2>/dev/null)
    status_code=$(echo "$response" | tail -c 4)
    content=$(echo "$response" | head -c -4)
    
    # Check status code
    if [ "$status_code" = "$expected_code" ]; then
        # Check content if provided
        if [ -n "$expected_content" ]; then
            if echo "$content" | grep -q "$expected_content"; then
                echo "✅ PASS"
                ((PASSED++))
                return 0
            else
                echo "❌ FAIL (wrong content: $content)"
                ((FAILED++))
                return 1
            fi
        else
            echo "✅ PASS"
            ((PASSED++))
            return 0
        fi
    else
        echo "❌ FAIL (HTTP $status_code, expected $expected_code)"
        ((FAILED++))
        return 1
    fi
}

# Test 1: POST /api/mcp/validate with valid Bearer token
run_test "MCP Validate POST - Valid Token" \
    "curl -s -X POST -H 'Authorization: Bearer $VALID_TOKEN' -H 'Content-Type: application/json' '$BACKEND_URL/mcp/validate' -w '%{http_code}'" \
    "200" \
    "919654030351"

# Test 2: GET /api/mcp/validate with valid Bearer token  
run_test "MCP Validate GET - Valid Token" \
    "curl -s -H 'Authorization: Bearer $VALID_TOKEN' '$BACKEND_URL/mcp/validate' -w '%{http_code}'" \
    "200" \
    "919654030351"

# Test 3: GET /api/mcp with valid Bearer token
run_test "MCP Root GET - Valid Token" \
    "curl -s -H 'Authorization: Bearer $VALID_TOKEN' '$BACKEND_URL/mcp' -w '%{http_code}'" \
    "200" \
    "MCP connection successful"

# Test 4: POST /api/mcp/validate with invalid Bearer token
run_test "MCP Validate POST - Invalid Token" \
    "curl -s -X POST -H 'Authorization: Bearer $INVALID_TOKEN' -H 'Content-Type: application/json' '$BACKEND_URL/mcp/validate' -w '%{http_code}'" \
    "401"

# Test 5: GET /api/mcp/validate with invalid Bearer token
run_test "MCP Validate GET - Invalid Token" \
    "curl -s -H 'Authorization: Bearer $INVALID_TOKEN' '$BACKEND_URL/mcp/validate' -w '%{http_code}'" \
    "401"

# Test 6: POST /api/mcp/validate with missing Authorization header
run_test "MCP Validate POST - Missing Token" \
    "curl -s -X POST -H 'Content-Type: application/json' '$BACKEND_URL/mcp/validate' -w '%{http_code}'" \
    "401"

# Test 7: POST /api/mcp/validate with wrong Authorization format (without Bearer)
run_test "MCP Validate POST - Wrong Format" \
    "curl -s -X POST -H 'Authorization: $VALID_TOKEN' -H 'Content-Type: application/json' '$BACKEND_URL/mcp/validate' -w '%{http_code}'" \
    "401"

# Test 8: POST /api/mcp/validate with token as query parameter
run_test "MCP Validate POST - Query Parameter" \
    "curl -s -X POST -H 'Content-Type: application/json' '$BACKEND_URL/mcp/validate?token=$VALID_TOKEN' -w '%{http_code}'" \
    "200" \
    "919654030351"

# Test 9: MCP Health Check Endpoint
run_test "MCP Health Check" \
    "curl -s '$BACKEND_URL/mcp/health' -w '%{http_code}'" \
    "200" \
    "healthy"

# Test 10: Integration Readiness Check for Puch AI
run_test "Puch AI Integration Readiness" \
    "curl -s -X POST -H 'Authorization: Bearer $VALID_TOKEN' -H 'Content-Type: application/json' -d '{\"session_id\": \"puch_ai_test_session\", \"message\": \"Hello, connection test\"}' '$BACKEND_URL/mcp' -w '%{http_code}'" \
    "200" \
    "success"

echo "============================================================"
echo "🎯 MCP PUCH AI INTEGRATION TEST RESULTS:"
echo "✅ PASSED: $PASSED"
echo "❌ FAILED: $FAILED"

if [ $FAILED -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED! MCP service is ready for Puch AI integration!"
    echo "🔗 Puch AI can connect using: /mcp connect https://0fbf6255-bf7b-4ad7-b4ea-c5da62fa1669.preview.emergentagent.com/api/mcp kumararpit9468"
    SUCCESS_RATE=100
else
    echo "⚠️ Some tests failed. Please check the implementation."
    SUCCESS_RATE=$((PASSED * 100 / (PASSED + FAILED)))
fi

echo "📊 SUCCESS RATE: ${SUCCESS_RATE}%"

# Additional verification tests
echo ""
echo "🔍 ADDITIONAL VERIFICATION:"
echo "Testing exact Puch AI validation format..."

# Test the exact response format expected by Puch AI
echo -n "Validating response format... "
response=$(curl -s -H "Authorization: Bearer $VALID_TOKEN" "$BACKEND_URL/mcp/validate")
if echo "$response" | jq -e '.number == "919654030351"' > /dev/null 2>&1; then
    echo "✅ PASS - Correct JSON format with number field"
else
    echo "❌ FAIL - Invalid response format: $response"
fi

echo -n "Testing Bearer token authentication... "
auth_response=$(curl -s -H "Authorization: Bearer $VALID_TOKEN" "$BACKEND_URL/mcp/validate" -w "%{http_code}")
if echo "$auth_response" | tail -c 4 | grep -q "200"; then
    echo "✅ PASS - Bearer token authentication working"
else
    echo "❌ FAIL - Bearer token authentication failed"
fi

echo ""
echo "🎯 SUMMARY FOR PUCH AI INTEGRATION:"
echo "✅ Validate Endpoint (POST): /api/mcp/validate"
echo "✅ Validate Endpoint (GET): /api/mcp/validate"  
echo "✅ Root MCP Endpoint: /api/mcp"
echo "✅ Token: kumararpit9468"
echo "✅ Expected Response: {\"number\": \"919654030351\"}"
echo "✅ Authentication: Bearer token in Authorization header"

exit $FAILED