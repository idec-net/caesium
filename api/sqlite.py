import sqlite3, time

con = sqlite3.connect("idec.db")
c = con.cursor()

def get_echo_length(echo):
    row = c.execute("SELECT COUNT(1) FROM msg WHERE echoarea = ?;", (echo,)).fetchone()
    return row[0]

def get_echocount(echo):
    return get_echo_length(echo)

def save_to_favorites(msgid, msg):
    favoritep = c.execute("SELECT COUNT(1) FROM msg WHERE msgid = ? AND favorites = 1", (msgid,)).fetchone()[0]
    if favoritep == 0:
        c.execute("UPDATE msg SET favorites = 1 WHERE msgid = ?;", (msgid,))
        con.commit()
        return True
    else:
        return False

def get_echo_msgids(echo):
    msgids = []
    for row in c.execute("SELECT msgid FROM msg WHERE echoarea = ? ORDER BY id;", (echo,)):
        if len(row[0]) > 0:
            msgids.append(row[0])
    return msgids

def get_carbonarea():
    msgids = []
    for row in c.execute("SELECT msgid FROM msg WHERE carbonarea = 1 ORDER BY id"):
        msgids.append(row[0])
    return msgids

def add_to_carbonarea(msgid, msgbody):
    c.execute("UPDATE msg SET carbonarea = 1 WHERE msgid = ?;", (msgid,))
    con.commit()

def save_message(raw, counts, remote_counts, node, to):
    co = counts
    for msg in raw:
        msgid = msg[0]
        msgbody = msg[1]
        if msgbody[1] in co[node]:
            co[node][msgbody[1]] += 1
        else:
            co[node][msgbody[1]] = remote_counts[msgbody[1]]
        c.execute("INSERT INTO msg (msgid, tags, echoarea, time, fr, addr, t, subject, body) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", (msgid, msgbody[0], msgbody[1], msgbody[2], msgbody[3], msgbody[4], msgbody[5], msgbody[6], "\n".join(msgbody[7:])))
    con.commit()
    for msg in raw:
        msgid = msg[0]
        msgbody = msg[1]
        if to:
            try:
                carbonarea = get_carbonarea()
            except:
                carbonarea = []
            for name in to:
                if name in msgbody[5] and not msgid in carbonarea:
                    add_to_carbonarea(msgid, msgbody)
    return co

def get_favorites_list():
    msgids = []
    for row in c.execute("SELECT msgid FROM msg WHERE favorites = 1;"):
        msgids.append(row[0])
    return msgids

def remove_from_favorites(msgid):
    c.execute("UPDATE msg SET favorites = 0 WHERE msgid = ?;", (msgid))
    con.commit()

def remove_echoarea(echoarea):
    c.execute("DELETE FROM msg WHERE echoarea = ?;", (echoarea,))
    con.commit()

def get_msg_list_data(echoarea):
    lst = []
    for row in c.execute("SELECT msgid, fr, subject, time FROM msg WHERE echoarea = ? ORDER BY id;", (echoarea,)):
        lst.append([row[0], row[1], row[2], time.strftime("%Y.%m.%d", time.gmtime(int(row[3])))])
    return lst

def read_msg(msgid, echoarea):
    size = "0b"
    row = c.execute("SELECT tags, echoarea, time, fr, addr, t, subject, body FROM msg WHERE msgid = ?;", (msgid,)).fetchone()
    msg = row[0] + "\n" + row[1] + "\n" + row[2] + "\n" + row[3] + "\n" + row[4] + "\n" + row[5] + "\n" + row[6] + "\n" + row[7]
    if msg:
        size = len(msg.encode("utf-8"))
    else:
        size = 0
    if size < 1024:
        size = str(size) + " B"
    else:
        size = str(format(size / 1024, ".2f")) + " KB"
    return msg.split("\n"), size

# Create databse
c.execute("""CREATE TABLE IF NOT EXISTS msg(
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    msgid TEXT,
    favorites INTEGER DEFAULT 0,
    carbonarea INTEGER DEFAULT 0,
    tags TEXT,
    echoarea TEXT,
    time TEXT,
    fr TEXT,
    addr TEXT,
    t TEXT,
    subject TEXT,
    body TEXT,
    UNIQUE (id));""")
c.execute("CREATE INDEX IF NOT EXISTS msgid ON 'msg' ('msgid');")
c.execute("CREATE INDEX IF NOT EXISTS echoarea ON 'msg' ('echoarea');")
c.execute("CREATE INDEX IF NOT EXISTS time ON 'msg' ('time');")
c.execute("CREATE INDEX IF NOT EXISTS subject ON 'msg' ('subject');")
c.execute("CREATE INDEX IF NOT EXISTS body ON 'msg' ('body');")
con.commit()
