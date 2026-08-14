param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$health = Invoke-RestMethod -Method Get -Uri "$BaseUrl/health"
Write-Host "Health:" ($health | ConvertTo-Json -Depth 5)

$meta = Invoke-RestMethod -Method Get -Uri "$BaseUrl/meta"
Write-Host "Meta:" ($meta | ConvertTo-Json -Depth 5)

$call = Invoke-RestMethod -Method Post -Uri "$BaseUrl/calls" -ContentType "application/json" -Body '{"customer_id":"CUST-1001"}'
$callId = $call.call_id
Write-Host "Call ID:" $callId

$verify = Invoke-RestMethod -Method Post -Uri "$BaseUrl/verify" -ContentType "application/json" -Body (@{
    customer_id = "CUST-1001"
    verification_value = "Rahul Sharma"
    call_id = $callId
} | ConvertTo-Json)
Write-Host "Verify:" ($verify | ConvertTo-Json -Depth 5)

$turn = Invoke-RestMethod -Method Post -Uri "$BaseUrl/webhooks/conversation" -ContentType "application/json" -Body (@{
    customer_id = "CUST-1001"
    call_id = $callId
    verification_value = "Rahul Sharma"
    message = "I'll pay tomorrow"
} | ConvertTo-Json)
Write-Host "Conversation:" ($turn | ConvertTo-Json -Depth 5)

