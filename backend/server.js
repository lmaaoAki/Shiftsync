const express = require('express');
const cors = require('cors');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const sqlite3 = require('sqlite3');
const { open } = require('sqlite');

const app = express();
const PORT = process.env.PORT || 3000;
const DB_FILE = process.env.DB_FILE || path.join(__dirname, 'data', 'shiftsync.sqlite');
const ML_SERVICE_URL = process.env.ML_SERVICE_URL || 'http://shiftsync-ml-service:5000';
const SECRET_KEY = process.env.APP_SECRET_KEY || 'default_insecure_secret';

app.use(cors());
app.use(express.json({ limit: '10mb' }));

let db;

const dbDir = path.dirname(DB_FILE);
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

const DEFPW = 'shiftsync123';
const DEFAULT_ORG_ROLES = [
  'Desk', 'Registration', 'Usher', 'Logistics', 'Documentation',
  'Stage Manager', 'Assistant Stage Manager', 'Stage Crew', 'Lights', 'Sounds', 'AVP'
];

const seedMembersData = [
  // Org 1 (handle: usg): University Student Government
  ['Arden', 0, 'org_1', 'usg', 'officer', 1],
  ['Bea', 2, 'org_1', 'usg', 'member', null],
  ['Carlo', 1, 'org_1', 'usg', 'member', null],
  // Org 2 (handle: css): Computer Science Society
  ['Gio', 2, 'org_2', 'css', 'officer', 4],
  ['Hana', 1, 'org_2', 'css', 'member', null],
  ['Ivan', 0, 'org_2', 'css', 'member', null]
];

function ds(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function mondayOf(x) {
  const d = new Date(x + 'T00:00:00');
  const dow = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - dow);
  return ds(d);
}

async function initDb() {
  db = await open({
    filename: DB_FILE,
    driver: sqlite3.Database
  });

  await db.exec(`
    CREATE TABLE IF NOT EXISTS state (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      data TEXT NOT NULL
    );
  `);

  const row = await db.get('SELECT data FROM state WHERE id = 1');
  if (!row) {
    const today = ds(new Date());
    const week = mondayOf(today);
    let seed = 7;
    const rnd = () => (seed = (seed * 9301 + 49297) % 233280) / 233280;

    const mkCls = () => {
      const c = [];
      for (let d = 0; d < 6; d++) {
        for (let k = 0, t = 0; k < (d === 5 ? 1 : 2); k++) {
          const a = t + Math.floor(rnd() * 5);
          const l = 2 + Math.floor(rnd() * 2);
          if (a + l <= 17) {
            c.push({ id: c.length + 1, name: 'Class ' + (c.length + 1), day: d, s: a + 5, e: a + l + 5 });
            t = a + l;
          }
        }
      }
      return c;
    };

    const members = seedMembersData.map((n, i) => {
      const classes = mkCls();
      const grid = Array(6).fill(0).map(() => Array(34).fill(0));
      classes.forEach(c => {
        for (let h = c.s; h < c.e; h += 0.5) grid[c.day][(h - 5) * 2] = c.id;
      });
      return {
        id: i + 1,
        orgId: n[2],
        name: n[0],
        def: n[1],
        status: 'active',
        sysRole: n[4],
        posId: n[5],
        nick: `${n[3]}_${n[0].toLowerCase()}`,
        pw: DEFPW,
        classes,
        grid,
        prefGrid: Array(6).fill(0).map(() => Array(34).fill(0)),
        prefs: [...DEFAULT_ORG_ROLES]
      };
    });

    const satDate = ds(new Date(new Date(week + 'T00:00:00').setDate(new Date(week + 'T00:00:00').getDate() + 5)));
    const thuDate = ds(new Date(new Date(week + 'T00:00:00').setDate(new Date(week + 'T00:00:00').getDate() + 3)));

    const initialState = {
      role: null,
      uid: 1,
      orgId: null,
      superSelectedOrg: 'org_1',
      page: 'home',
      week,
      uid2: 100,
      cd: null,
      orgs: [
        { id: 'org_1', handle: 'usg', name: 'University Student Government (USG)', deskCap: 2, target: 6, eventWeek: false, eventDays: [], customRoles: [...DEFAULT_ORG_ROLES] },
        { id: 'org_2', handle: 'css', name: 'Computer Science Society (CSS)', deskCap: 2, target: 6, eventWeek: false, eventDays: [], customRoles: ['Desk', 'Registration', 'Usher', 'Logistics', 'Documentation', 'Technical Support'] }
      ],
      officerPositions: [
        { id: 1, orgId: 'org_1', title: 'President', targetHrs: 12 },
        { id: 2, orgId: 'org_1', title: 'Vice President', targetHrs: 10 },
        { id: 3, orgId: 'org_1', title: 'Committee Head', targetHrs: 8 },
        { id: 4, orgId: 'org_2', title: 'President', targetHrs: 12 },
        { id: 5, orgId: 'org_2', title: 'VP Internal', targetHrs: 10 }
      ],
      staff: [
        { user: 'superadmin', pw: DEFPW, role: 'superadmin', name: 'University Super Admin', orgId: null },
        { user: 'usg_admin', pw: DEFPW, role: 'admin', name: 'USG Admin', orgId: 'org_1' },
        { user: 'css_admin', pw: DEFPW, role: 'admin', name: 'CSS Admin', orgId: 'org_2' }
      ],
      sid: null, err: '', lu: '', abs: [], as: [], un: [], log: [], timeLogs: [], conflicts: [], history: [], msg: '', bench: null, sus: null,
      members,
      events: [
        { id: 1, orgId: 'org_1', name: 'General Assembly', date: satDate, s: 9, e: 17, roles: { Registration: 1, Usher: 2, Logistics: 1 } },
        { id: 2, orgId: 'org_2', name: 'Annual Hackathon', date: thuDate, s: 9, e: 17, roles: { Registration: 2, Logistics: 1, 'Technical Support': 2 } }
      ]
    };

    await db.run('INSERT INTO state (id, data) VALUES (1, ?)', JSON.stringify(initialState));
  }
}

app.get('/api/state', async (req, res) => {
  try {
    const row = await db.get('SELECT data FROM state WHERE id = 1');
    res.json(JSON.parse(row.data));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/state', async (req, res) => {
  try {
    const newData = JSON.stringify(req.body);
    await db.run('UPDATE state SET data = ? WHERE id = 1', newData);
    res.json({ status: 'ok' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.post('/api/generate-roster', async (req, res) => {
  try {
    const payload = req.body;
    const response = await axios.post(`${ML_SERVICE_URL}/solve-roster`, payload, {
      headers: { 'X-Secret-Key': SECRET_KEY }
    });

    const updatedState = response.data;
    await db.run('UPDATE state SET data = ? WHERE id = 1', JSON.stringify(updatedState));
    res.json(updatedState);
  } catch (err) {
    res.status(500).json({ error: 'ML Solver Error: ' + (err.response?.data?.detail || err.message) });
  }
});

initDb().then(() => {
  app.listen(PORT, () => {
    console.log(`ShiftSync Backend running on port ${PORT}`);
  });
});