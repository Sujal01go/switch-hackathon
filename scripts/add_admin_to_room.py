import psycopg2
import datetime

conn = psycopg2.connect(
    host="localhost",
    port=55011,
    user="switch_app",
    password="J0-Efw91U4XjcYhS8CfA0qdHaUzi8oSx",
    dbname="switch"
)
cur = conn.cursor()
cur.execute("SET app.tenant_id = '00000000-0000-0000-0000-000000000000';")

cur.execute("SELECT * FROM tenant_members WHERE user_id = 'f4df2d4f-dc9c-4621-99f4-97fc6b1af001';")
print("Tenant members:", cur.fetchall())

# Check if already in client_rooms
cur.execute("SELECT * FROM client_rooms WHERE client_id = 'a5300d5b-8584-4268-ad15-29ba84679fd8' AND room_id = 'b58680a3-370e-468b-abf7-1e66a813599f';")
res = cur.fetchall()
print("In client_rooms:", res)

if not res:
    cur.execute("""
        INSERT INTO client_rooms (client_id, room_id, joined_at, tenant_id)
        VALUES ('a5300d5b-8584-4268-ad15-29ba84679fd8', 'b58680a3-370e-468b-abf7-1e66a813599f', NOW(), '00000000-0000-0000-0000-000000000000');
    """)
    conn.commit()
    print("Inserted admin client into client_rooms!")

