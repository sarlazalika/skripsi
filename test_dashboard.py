import app
client = app.app.test_client()
response = client.get('/')
print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print("OK: Dashboard route (/) loaded without error")
else:
    print(f"Error loading dashboard: {response.data.decode('utf-8')[:500]}")
