import psycopg2
import sys

sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(
    host="localhost",
    port=55011,
    user="switch_app",
    password="J0-Efw91U4XjcYhS8CfA0qdHaUzi8oSx",
    dbname="switch"
)
cur = conn.cursor()
cur.execute("SET app.tenant_id = '00000000-0000-0000-0000-000000000000';")

print("=== ROOM_ROLES ===")
cur.execute("SELECT * FROM room_roles WHERE room_id = 'b58680a3-370e-468b-abf7-1e66a813599f';")
print(cur.fetchall())

print("=== ROOM_AGENTS ===")
cur.execute("SELECT * FROM room_agents WHERE room_id = 'b58680a3-370e-468b-abf7-1e66a813599f';")
print(cur.fetchall())

print("=== EXTERNAL_USERS ===")
cur.execute("SELECT * FROM external_users;")
print(cur.fetchall())

print("=== CLIENT_ROOMS ===")
cur.execute("SELECT * FROM client_rooms WHERE room_id = 'b58680a3-370e-468b-abf7-1e66a813599f';")
print(cur.fetchall())

