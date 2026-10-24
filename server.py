"""Prototipo local de gestión documental. Python 3.11+ y cryptography."""
from __future__ import annotations
import argparse, base64, hashlib, hmac, io, json, mimetypes, os, re
import secrets, sqlite3, stat, threading, time, unicodedata, uuid, zipfile
from datetime import datetime, timezone
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, parse_qs
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

ROOT = Path(__file__).resolve().parent
MAX_FILES, MAX_BYTES, MAX_BODY = 100, 25*1024*1024, 36*1024*1024
CHUNK_BYTES = 512*1024
ALLOWED = {'.md', '.png', '.jpg', '.jpeg', '.webp', '.pdf', '.txt', '.json'}
ROLES = {'admin', 'revisor', 'agente', 'auditor'}

def now(): return datetime.now(timezone.utc).isoformat(timespec='milliseconds')
def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def sha(data): return hashlib.sha256(data).hexdigest()
def password_hash(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    return salt.hex()+':'+hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600_000).hex()
def password_ok(password, value):
    salt, _ = value.split(':')
    return hmac.compare_digest(password_hash(password, bytes.fromhex(salt)), value)

class Problem(Exception):
    def __init__(self, status, message): self.status, self.message = status, message

def safe_path(name):
    if not isinstance(name, str) or not name or len(name)>220 or '\\' in name or ':' in name:
        raise Problem(400, 'Ruta de archivo no permitida.')
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in {'', '.', '..'} for p in name.split('/')) or any(ord(c)<32 for c in name):
        raise Problem(400, 'Ruta de archivo no permitida.')
    if path.suffix.lower() not in ALLOWED: raise Problem(400, 'Extensión no permitida: '+path.suffix)
    return path.as_posix()

def unpack_files(items):
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_FILES: raise Problem(400, 'Seleccione entre 1 y 100 archivos.')
    files = {}
    def add(name, data):
        name=safe_path(name)
        if name.casefold() in {p.casefold() for p in files}: raise Problem(400, 'Rutas repetidas en el paquete.')
        if len(files)>=MAX_FILES or len(data)+sum(map(len,files.values()))>MAX_BYTES: raise Problem(413, 'Paquete mayor a 25 MB o 100 archivos.')
        if name.lower().endswith('.md'):
            try: data.decode('utf-8-sig')
            except UnicodeDecodeError: raise Problem(400, 'El Markdown debe estar codificado en UTF-8.')
        files[name]=data
    for item in items:
        try: data=base64.b64decode(item['base64'], validate=True); name=item['path']
        except (KeyError, ValueError, TypeError): raise Problem(400, 'Archivo codificado incorrectamente.')
        if not isinstance(name,str): raise Problem(400, 'Nombre inválido.')
        if name.lower().endswith('.zip'):
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    if len(archive.infolist())>MAX_FILES*2: raise Problem(413, 'Demasiadas entradas ZIP.')
                    for info in archive.infolist():
                        if info.is_dir(): continue
                        if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1: raise Problem(400, 'ZIP cifrado o con enlaces no permitido.')
                        if info.file_size>MAX_BYTES or info.file_size+sum(map(len,files.values()))>MAX_BYTES: raise Problem(413, 'ZIP descomprimido demasiado grande.')
                        add(info.filename, archive.read(info))
            except (zipfile.BadZipFile, RuntimeError, NotImplementedError): raise Problem(400, 'ZIP inválido o no compatible.')
        else: add(name,data)
    if not any(p.lower().endswith('.md') for p in files): raise Problem(400,'El paquete necesita al menos un archivo Markdown.')
    return files

class Store:
    def __init__(self, folder):
        self.folder=Path(folder); self.folder.mkdir(parents=True,exist_ok=True)
        self.blobs=self.folder/'blobs'; self.blobs.mkdir(exist_ok=True)
        self.staging=self.folder/'staging';self.staging.mkdir(exist_ok=True)
        self.lock=threading.RLock(); self.sessions={}; self.failures={}
        keys=self.folder/'keys.json'
        if not keys.exists():
            # Never silently generate replacement keys for an existing database.
            if (self.folder/'catalog.sqlite3').exists(): raise RuntimeError('Faltan claves; recupere un respaldo completo.')
            keys.write_text(json.dumps({k:secrets.token_bytes(32).hex() for k in ['files','audit','signing']}))
            try: os.chmod(keys,0o600)
            except OSError: pass
        self.keys=json.loads(keys.read_text()); self.aes=AESGCM(bytes.fromhex(self.keys['files']))
        self.signer=Ed25519PrivateKey.from_private_bytes(bytes.fromhex(self.keys['signing']))
        self.public_key=base64.b64encode(self.signer.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
        self.db=sqlite3.connect(self.folder/'catalog.sqlite3',check_same_thread=False,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL'); self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL, unit TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS documents(id TEXT PRIMARY KEY, unit TEXT NOT NULL, title TEXT NOT NULL, owner TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS versions(id TEXT PRIMARY KEY, doc_id TEXT NOT NULL REFERENCES documents(id), number INTEGER NOT NULL, digest TEXT NOT NULL, status TEXT NOT NULL, files TEXT NOT NULL, author TEXT NOT NULL, created TEXT NOT NULL, reviewer TEXT, reviewed TEXT, note TEXT, UNIQUE(doc_id,number));
        CREATE TABLE IF NOT EXISTS receipts(user_id TEXT NOT NULL, operation TEXT NOT NULL, request_hash TEXT NOT NULL, response TEXT NOT NULL, created TEXT NOT NULL, PRIMARY KEY(user_id,operation));
        CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY, event TEXT NOT NULL, prev TEXT NOT NULL, mac TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'audit append only'); END;
        CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'audit append only'); END;
        CREATE TABLE IF NOT EXISTS device_events(user_id TEXT NOT NULL, device TEXT NOT NULL, event_id TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(user_id,device,event_id));
        CREATE TABLE IF NOT EXISTS upload_sessions(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, operation TEXT NOT NULL, total_bytes INTEGER NOT NULL, payload_hash TEXT NOT NULL, chunks TEXT NOT NULL, created TEXT NOT NULL, result TEXT, UNIQUE(user_id,operation));
        ''')
        if not self.verify_audit()['valid']: raise RuntimeError('La cadena de auditoría no es válida. Conserve los archivos y revise el incidente.')

    def audit(self, action, actor=None, **details):
        with self.lock:
            last=self.db.execute('SELECT seq,mac FROM audit ORDER BY seq DESC LIMIT 1').fetchone()
            seq=(last['seq']+1) if last else 1; prev=last['mac'] if last else '0'*64
            event={'event_id':uuid.uuid4().hex,'server_time':now(),'action':action,'actor':actor['id'] if actor else None,'username':actor['username'] if actor else None,'unit':actor['unit'] if actor else None,**details}
            raw=canonical(event).decode(); mac=hmac.new(bytes.fromhex(self.keys['audit']),f'{seq}\n{prev}\n{raw}'.encode(),hashlib.sha256).hexdigest()
            self.db.execute('INSERT INTO audit VALUES(?,?,?,?)',(seq,raw,prev,mac))
            return seq

    def verify_audit(self):
        with self.lock:
            prev='0'*64; count=0
            for row in self.db.execute('SELECT * FROM audit ORDER BY seq'):
                count+=1; expected=hmac.new(bytes.fromhex(self.keys['audit']),f'{count}\n{prev}\n{row["event"]}'.encode(),hashlib.sha256).hexdigest()
                if row['seq']!=count or row['prev']!=prev or not hmac.compare_digest(expected,row['mac']):return {'valid':False,'checked':count,'invalid_seq':row['seq']}
                prev=row['mac']
            return {'valid':True,'checked':count,'head':prev}

    def create_user(self,username,password,role,unit,actor=None):
        if not all(isinstance(v,str) for v in [username,password,role,unit]) or not re.fullmatch(r'[a-zA-Z0-9_.-]{3,40}',username) or len(password)<12 or len(password)>256 or role not in ROLES or not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}',unit):raise Problem(400,'Usuario, unidad o rol inválido; contraseña mínima de 12 caracteres.')
        with self.lock:
            uid=uuid.uuid4().hex
            try:self.db.execute('INSERT INTO users VALUES(?,?,?,?,?,1)',(uid,username,password_hash(password),role,unit))
            except sqlite3.IntegrityError:raise Problem(409,'El usuario ya existe.')
            self.audit('user_created',actor,target_user=uid,role=role,target_unit=unit)
            return uid

    def login(self,username,password,device,ip):
        if not isinstance(username,str) or not isinstance(password,str) or len(password)>256 or not re.fullmatch(r'[a-zA-Z0-9_-]{8,80}',device or ''):raise Problem(400,'Credenciales o identificador de dispositivo inválidos.')
        with self.lock:
            key=(ip,username); attempts=[t for t in self.failures.get(key,[]) if t>time.time()-900]
            if len(attempts)>=8:raise Problem(429,'Demasiados intentos. Espere 15 minutos.')
            user=self.db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
            valid=password_ok(password,user['password']) if user else password_ok(password,password_hash('dummy-password'))
            if not user or not user['active'] or not valid:
                self.failures[key]=attempts+[time.time()];self.audit('login_denied',None,ip=ip);raise Problem(401,'Credenciales inválidas.')
            self.failures.pop(key,None);token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
            self.sessions[sha(token.encode())]={'uid':user['id'],'csrf':csrf,'device':device,'expires':time.time()+1800}
            self.audit('login_success',user,device=device,ip=ip)
            return token,csrf,self.clean_user(user)

    @staticmethod
    def clean_user(user):return {k:user[k] for k in ['id','username','role','unit','active']}

    def authenticate(self,token):
        with self.lock:
            session=self.sessions.get(sha(token.encode()))
            if not session or session['expires']<time.time():raise Problem(401,'Inicie sesión nuevamente.')
            user=self.db.execute('SELECT * FROM users WHERE id=?',(session['uid'],)).fetchone()
            if not user or not user['active']:raise Problem(401,'Cuenta desactivada.')
            session['expires']=time.time()+1800
            return self.clean_user(user),session

    def can_read(self,user,row):
        return row['unit']==user['unit'] and (user['role'] in {'admin','revisor'} or (user['role']=='agente' and (row['status']=='approved' or row['owner']==user['id'])))

    def version(self,user,vid):
        row=self.db.execute('SELECT v.*,d.unit,d.title,d.owner FROM versions v JOIN documents d ON v.doc_id=d.id WHERE v.id=?',(vid,)).fetchone()
        if not row or not self.can_read(user,row):
            self.audit('access_denied',user,resource=vid);raise Problem(404,'Documento no disponible.')
        return row

    def blob(self,data):
        digest=sha(data); path=self.blobs/digest
        if not path.exists():
            nonce=secrets.token_bytes(12); encrypted=nonce+self.aes.encrypt(nonce,data,digest.encode())
            temp=self.blobs/(digest+'.'+uuid.uuid4().hex+'.tmp');temp.write_bytes(encrypted);os.replace(temp,path)
        return digest

    def read_blob(self,digest):
        raw=(self.blobs/digest).read_bytes(); data=self.aes.decrypt(raw[:12],raw[12:],digest.encode())
        if sha(data)!=digest:raise RuntimeError('Integridad de archivo inválida.')
        return data

    def upload(self,user,payload,operation):
        if user['role'] not in {'admin','revisor','agente'}:raise Problem(403,'Este rol no puede subir archivos.')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{8,100}',operation or ''):raise Problem(400,'Falta identificador de operación.')
        title=payload.get('title','')
        if not isinstance(title,str):raise Problem(400,'Título inválido.')
        title=title.strip()
        if not 1<=len(title)<=180:raise Problem(400,'Indique un título de hasta 180 caracteres.')
        request_hash=sha(canonical(payload))
        with self.lock:
            receipt=self.db.execute('SELECT * FROM receipts WHERE user_id=? AND operation=?',(user['id'],operation)).fetchone()
            if receipt:
                if receipt['request_hash']!=request_hash:raise Problem(409,'Este identificador de operación ya se usó con otro contenido.')
                self.audit('upload_retry_confirmed',user,operation=operation)
                return {**json.loads(receipt['response']),'retry':True}
            files=unpack_files(payload.get('files'))
            manifest=[{'path':p,'sha256':sha(data),'bytes':len(data)} for p,data in sorted(files.items())]
            digest=sha(canonical(manifest));docid=payload.get('document_id');base=payload.get('base_version')
            # Detect equal bytes even when the uploaded filename changed. Never disclose other units.
            matching_files=[];matches_by_hash={}
            visible=self.db.execute('SELECT v.*,d.unit,d.title,d.owner FROM versions v JOIN documents d ON v.doc_id=d.id WHERE d.unit=?',(user['unit'],)).fetchall()
            for candidate in visible:
                if not self.can_read(user,candidate):continue
                for f in json.loads(candidate['files']):
                    group=matches_by_hash.setdefault(f['sha256'],[])
                    if len(group)<5:group.append({'version_id':candidate['id'],'document_id':candidate['doc_id'],'path':f['path']})
            for f in manifest:
                if f['sha256'] in matches_by_hash:matching_files.append({'path':f['path'],'sha256':f['sha256'],'matches':matches_by_hash[f['sha256']]})
            existing=None
            if docid:
                doc=self.db.execute('SELECT * FROM documents WHERE id=?',(docid,)).fetchone()
                if not doc or doc['unit']!=user['unit'] or not(user['role'] in {'admin','revisor'} or doc['owner']==user['id']):raise Problem(404,'Documento no disponible.')
                latest=self.db.execute('SELECT * FROM versions WHERE doc_id=? ORDER BY number DESC LIMIT 1',(docid,)).fetchone()
                if base!=latest['number']:raise Problem(409,'Conflicto: ya existe una versión más reciente. Descárguela y revise las diferencias.')
                number=latest['number']+1
                if latest['digest']==digest:existing=self.version(user,latest['id'])
            else:
                candidates=self.db.execute('SELECT v.*,d.unit,d.owner,d.title FROM versions v JOIN documents d ON v.doc_id=d.id WHERE v.digest=? AND d.unit=? ORDER BY v.created DESC',(digest,user['unit'])).fetchall()
                existing=next((r for r in candidates if self.can_read(user,r)),None)
                docid=uuid.uuid4().hex;number=1
            if existing:
                result={'duplicate':True,'version_id':existing['id'],'document_id':existing['doc_id'],'version':existing['number'],'status':existing['status'],'digest':digest,'matching_files':matching_files}
                self.db.execute('INSERT INTO receipts VALUES(?,?,?,?,?)',(user['id'],operation,request_hash,json.dumps(result),now()))
                self.audit('upload_duplicate',user,operation=operation,version_id=existing['id'],digest=digest)
                return result
            for data in files.values():self.blob(data)
            vid=uuid.uuid4().hex
            self.db.execute('BEGIN IMMEDIATE')
            try:
                if not payload.get('document_id'):self.db.execute('INSERT INTO documents VALUES(?,?,?,?,?)',(docid,user['unit'],title,user['id'],now()))
                self.db.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?,?,?,?)',(vid,docid,number,digest,'pending',canonical(manifest).decode(),user['id'],now(),None,None,None))
                result={'duplicate':False,'version_id':vid,'document_id':docid,'version':number,'status':'pending','digest':digest,'matching_files':matching_files}
                self.db.execute('INSERT INTO receipts VALUES(?,?,?,?,?)',(user['id'],operation,request_hash,json.dumps(result),now()))
                self.audit('upload_received',user,operation=operation,version_id=vid,digest=digest,files=len(files),bytes=sum(map(len,files.values())),matching_file_count=len(matching_files))
                self.db.execute('COMMIT')
            except Exception:self.db.execute('ROLLBACK');raise
            return result

    def upload_session(self,user,sid):
        row=self.db.execute('SELECT * FROM upload_sessions WHERE id=? AND user_id=?',(sid,user['id'])).fetchone()
        if not row:raise Problem(404,'Carga no disponible.')
        return row

    def start_upload(self,user,operation,total,digest):
        if user['role'] not in {'admin','revisor','agente'}:raise Problem(403,'Este rol no puede subir archivos.')
        if not re.fullmatch(r'[a-zA-Z0-9_-]{8,100}',operation or '') or type(total) is not int or not 0<total<=MAX_BODY or not re.fullmatch(r'[0-9a-f]{64}',digest or ''):raise Problem(400,'Datos de carga inválidos.')
        with self.lock:
            existing=self.db.execute('SELECT * FROM upload_sessions WHERE user_id=? AND operation=?',(user['id'],operation)).fetchone()
            if existing:
                if existing['total_bytes']!=total or existing['payload_hash']!=digest:raise Problem(409,'La operación corresponde a otro contenido.')
                return {'upload_id':existing['id'],'received':list(json.loads(existing['chunks'])),'chunk_bytes':CHUNK_BYTES,'result':json.loads(existing['result']) if existing['result'] else None}
            # Bounded local staging; expired/incomplete sessions can be explicitly purged by the administrator offline.
            reserved=self.db.execute('SELECT COALESCE(sum(total_bytes),0) FROM upload_sessions WHERE result IS NULL').fetchone()[0]
            if reserved+total>256*1024*1024:raise Problem(507,'Área temporal llena. Revise cargas incompletas.')
            sid=uuid.uuid4().hex;self.db.execute('INSERT INTO upload_sessions VALUES(?,?,?,?,?,?,?,NULL)',(sid,user['id'],operation,total,digest,'{}',now()))
            self.audit('upload_started',user,upload_id=sid,operation=operation,total_bytes=total)
            return {'upload_id':sid,'received':[],'chunk_bytes':CHUNK_BYTES,'result':None}

    def upload_chunk(self,user,sid,index,encoded):
        with self.lock:
            row=self.upload_session(user,sid)
            if row['result']:raise Problem(409,'La carga ya terminó.')
            count=(row['total_bytes']+CHUNK_BYTES-1)//CHUNK_BYTES
            if type(index) is not int or not 0<=index<count:raise Problem(400,'Índice de bloque inválido.')
            try:data=base64.b64decode(encoded,validate=True)
            except (TypeError,ValueError):raise Problem(400,'Bloque inválido.')
            size=min(CHUNK_BYTES,row['total_bytes']-index*CHUNK_BYTES)
            if len(data)!=size:raise Problem(400,'Tamaño de bloque inválido.')
            chunks=json.loads(row['chunks']);digest=sha(data)
            if str(index) in chunks:
                if chunks[str(index)]!=digest:raise Problem(409,'El bloque recibido tiene otro contenido.')
                return {'received':index,'retry':True}
            nonce=secrets.token_bytes(12);raw=nonce+self.aes.encrypt(nonce,data,f'{sid}:{index}'.encode())
            folder=self.staging/sid;folder.mkdir(exist_ok=True);temp=folder/(str(index)+'.tmp');temp.write_bytes(raw);os.replace(temp,folder/str(index))
            chunks[str(index)]=digest;self.db.execute('UPDATE upload_sessions SET chunks=? WHERE id=?',(json.dumps(chunks),sid))
            self.audit('upload_chunk_received',user,upload_id=sid,index=index,bytes=len(data))
            return {'received':index,'retry':False}

    def finish_upload(self,user,sid):
        with self.lock:
            row=self.upload_session(user,sid)
            if row['result']:return {**json.loads(row['result']),'retry':True}
            chunks=json.loads(row['chunks']);count=(row['total_bytes']+CHUNK_BYTES-1)//CHUNK_BYTES
            if len(chunks)!=count:raise Problem(409,'Faltan bloques; reanude la carga.')
            pieces=[]
            for i in range(count):
                raw=(self.staging/sid/str(i)).read_bytes();data=self.aes.decrypt(raw[:12],raw[12:],f'{sid}:{i}'.encode())
                if sha(data)!=chunks[str(i)]:raise Problem(409,'Un bloque no supera la verificación.')
                pieces.append(data)
            data=b''.join(pieces)
            if len(data)!=row['total_bytes'] or sha(data)!=row['payload_hash']:raise Problem(409,'La carga completa no supera la verificación.')
            try:payload=json.loads(data)
            except (ValueError,UnicodeDecodeError):raise Problem(400,'Contenido JSON inválido.')
            if not isinstance(payload,dict):raise Problem(400,'Contenido inválido.')
            result=self.upload(user,payload,row['operation'])
            self.db.execute('UPDATE upload_sessions SET result=? WHERE id=?',(json.dumps(result),sid));self.audit('upload_completed',user,upload_id=sid,version_id=result['version_id'])
            for i in range(count):(self.staging/sid/str(i)).unlink(missing_ok=True)
            (self.staging/sid).rmdir()
            return result

    def review(self,user,vid,status,note):
        with self.lock:
            row=self.version(user,vid)
            if user['role'] not in {'admin','revisor'}:raise Problem(403,'Se requiere rol revisor.')
            if status not in {'approved','rejected'} or not isinstance(note,str) or len(note)>1000:raise Problem(400,'Revisión inválida.')
            if row['status']!='pending':raise Problem(409,'La versión ya fue revisada; cree una nueva para corregirla.')
            if status=='rejected' and not note.strip():raise Problem(400,'Indique el motivo del rechazo.')
            self.db.execute('BEGIN IMMEDIATE')
            try:
                self.db.execute('UPDATE versions SET status=?,reviewer=?,reviewed=?,note=? WHERE id=?',(status,user['id'],now(),note,vid))
                self.audit('version_'+status,user,version_id=vid,note=note)
                self.db.execute('COMMIT')
            except Exception:self.db.execute('ROLLBACK');raise

    def listing(self,user):
        with self.lock:
            rows=self.db.execute('SELECT v.*,d.unit,d.title,d.owner FROM versions v JOIN documents d ON d.id=v.doc_id WHERE d.unit=? ORDER BY v.created DESC',(user['unit'],)).fetchall()
            result=[]
            for row in rows:
                if self.can_read(user,row):
                    item=dict(row);item['files']=json.loads(item['files']);result.append(item)
            self.audit('catalog_view',user,count=len(result))
            return result

    def sync(self,user):
        if user['role']=='auditor':raise Problem(403,'El auditor no descarga contenido.')
        with self.lock:
            docs=self.listing(user);latest={}
            for row in docs:
                if row['status']=='approved' and (row['doc_id'] not in latest or row['number']>latest[row['doc_id']]['number']):latest[row['doc_id']]=row
            manifest={'schema':1,'generated_at':now(),'unit':user['unit'],'account':user['id'],'documents':[{'document_id':r['doc_id'],'title':r['title'],'version':r['number'],'version_id':r['id'],'digest':r['digest'],'files':r['files'],'download':'/api/versions/'+r['id']+'/download'} for r in latest.values()]}
            raw=canonical(manifest)
            self.audit('update_manifest_requested',user,documents=len(latest),manifest_hash=sha(raw))
            return {'manifest':manifest,'canonical_base64':base64.b64encode(raw).decode(),'signature_base64':base64.b64encode(self.signer.sign(raw)).decode(),'public_key_base64':self.public_key}

    def backup(self,password,destination):
        if len(password)<16:raise Problem(400,'Contraseña de respaldo mínima: 16 caracteres.')
        with self.lock:
            self.audit('backup_created',None)
            temp=self.folder/('backup-'+uuid.uuid4().hex+'.sqlite3')
            target=sqlite3.connect(temp);self.db.backup(target);target.close()
            stream=io.BytesIO()
            try:
                with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
                    z.write(temp,'catalog.sqlite3');z.writestr('keys.json',json.dumps(self.keys))
                    for p in self.blobs.iterdir():
                        if re.fullmatch('[0-9a-f]{64}',p.name):z.write(p,'blobs/'+p.name)
                salt=secrets.token_bytes(16);nonce=secrets.token_bytes(12);key=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,600_000)
                Path(destination).write_bytes(b'FISCALIA1'+salt+nonce+AESGCM(key).encrypt(nonce,stream.getvalue(),b'FISCALIA1'))
            finally:temp.unlink(missing_ok=True)

def restore_backup(source,password,destination):
    dest=Path(destination)
    if dest.exists() and any(dest.iterdir()):raise Problem(409,'Restaurar requiere una carpeta nueva o vacía.')
    raw=Path(source).read_bytes()
    if raw[:9]!=b'FISCALIA1':raise Problem(400,'Formato de respaldo inválido.')
    key=hashlib.pbkdf2_hmac('sha256',password.encode(),raw[9:25],600_000)
    content=AESGCM(key).decrypt(raw[25:37],raw[37:],b'FISCALIA1')
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        names=z.namelist()
        if not {'catalog.sqlite3','keys.json'}.issubset(names) or any(not (n in {'catalog.sqlite3','keys.json'} or re.fullmatch(r'blobs/[0-9a-f]{64}',n)) for n in names):raise Problem(400,'Respaldo inválido.')
        dest.mkdir(parents=True,exist_ok=True)
        for n in names:
            p=dest/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
    store=Store(dest);store.audit('backup_restored');store.db.close()

class Handler(BaseHTTPRequestHandler):
    server_version='FiscaliaLocal/0.1'
    def setup(self):
        super().setup();self.connection.settimeout(30)
    def log_message(self,*args):pass
    @property
    def store(self):return self.server.store
    def headers_safe(self,ctype):
        self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
    def send(self,status,body,ctype='application/json; charset=utf-8',extra=None,transfer=None):
        if not isinstance(body,bytes):body=canonical(body)
        self.send_response(status);self.headers_safe(ctype);self.send_header('Content-Length',str(len(body)))
        for k,v in (extra or {}).items():self.send_header(k,v)
        self.end_headers()
        try:
            self.wfile.write(body);self.wfile.flush()
            if transfer:self.store.audit('transfer_written',transfer[0],**transfer[1],bytes=len(body))
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
            if transfer:self.store.audit('transfer_interrupted',transfer[0],**transfer[1])
    def body(self):
        if self.headers.get('Transfer-Encoding'):raise Problem(400,'Transferencia no compatible.')
        try:size=int(self.headers.get('Content-Length','0'))
        except ValueError:raise Problem(400,'Longitud inválida.')
        if not 0<size<=MAX_BODY:raise Problem(413,'Solicitud vacía o demasiado grande.')
        if self.headers.get_content_type()!='application/json':raise Problem(415,'Se requiere JSON.')
        try:
            value=json.loads(self.rfile.read(size))
            if not isinstance(value,dict):raise ValueError()
            return value
        except (ValueError,UnicodeDecodeError):raise Problem(400,'JSON inválido.')
    def token(self):
        try: jar=cookies.SimpleCookie(self.headers.get('Cookie',''));return jar['session'].value if 'session' in jar else ''
        except cookies.CookieError:return ''
    def check_host(self):
        expected={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        if self.headers.get('Host') not in expected:raise Problem(403,'Host no permitido.')
        origin=self.headers.get('Origin')
        if origin and origin not in {'http://'+v for v in expected}:raise Problem(403,'Origen no permitido.')
    def dispatch(self,method):
        actor=None
        try:
            self.check_host();url=urlsplit(self.path);path=url.path
            if method=='GET' and path in {'/','/app.js','/style.css'}:
                filename={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}[path]
                return self.send(200,(ROOT/'web'/filename).read_bytes(),{'/':'text/html; charset=utf-8','/app.js':'text/javascript; charset=utf-8','/style.css':'text/css; charset=utf-8'}[path])
            if method=='GET' and path=='/api/health':return self.send(200,{'status':'ok','mode':'local-prototype','version':'0.1.0'})
            if method=='POST' and path=='/api/login':
                data=self.body();token,csrf,user=self.store.login(data.get('username'),data.get('password'),data.get('device'),self.client_address[0])
                return self.send(200,{'user':user,'csrf':csrf},extra={'Set-Cookie':'session='+token+'; HttpOnly; SameSite=Strict; Path=/'})
            actor,session=self.store.authenticate(self.token())
            if method=='POST' and not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),session['csrf']):raise Problem(403,'Token de operación inválido; recargue la página.')
            if method=='GET' and path=='/api/me':return self.send(200,{'user':actor,'csrf':session['csrf']})
            if method=='POST' and path=='/api/logout':
                self.store.audit('logout',actor,device=session['device']);self.store.sessions.pop(sha(self.token().encode()),None)
                return self.send(200,{'ok':True},extra={'Set-Cookie':'session=; HttpOnly; SameSite=Strict; Max-Age=0; Path=/'})
            if method=='POST' and path=='/api/admin/shutdown':
                if actor['role']!='admin':raise Problem(403,'Se requiere administrador.')
                self.store.audit('server_shutdown_requested',actor)
                self.send(200,{'ok':True});threading.Thread(target=self.server.shutdown,daemon=True).start();return
            if method=='GET' and path=='/api/documents':return self.send(200,{'documents':self.store.listing(actor)})
            if method=='POST' and path=='/api/uploads':
                self.store.audit('upload_requested',actor,device=session['device'])
                return self.send(200,self.store.upload(actor,self.body(),self.headers.get('Idempotency-Key')))
            if method=='POST' and path=='/api/uploads/start':
                d=self.body();return self.send(200,self.store.start_upload(actor,self.headers.get('Idempotency-Key'),d.get('total_bytes'),d.get('sha256')))
            chunks_route=re.fullmatch(r'/api/uploads/([a-f0-9]{32})/(chunk|complete)',path)
            if method=='POST' and chunks_route:
                sid,action=chunks_route.groups();d=self.body()
                if action=='chunk':return self.send(200,self.store.upload_chunk(actor,sid,d.get('index'),d.get('base64')))
                return self.send(200,self.store.finish_upload(actor,sid))
            if method=='GET' and path=='/api/sync/manifest':return self.send(200,self.store.sync(actor))
            match=re.fullmatch(r'/api/versions/([a-f0-9]{32})/(review|download|file)',path)
            if match:
                vid,action=match.groups()
                with self.store.lock:
                    row=self.store.version(actor,vid)
                    if method=='POST' and action=='review':
                        data=self.body();self.store.review(actor,vid,data.get('status'),data.get('note',''));return self.send(200,{'ok':True})
                    if method=='GET' and action=='download':
                        self.store.audit('download_authorized',actor,version_id=vid,device=session['device'])
                        stream=io.BytesIO()
                        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
                            for f in json.loads(row['files']):z.writestr(f['path'],self.store.read_blob(f['sha256']))
                        return self.send(200,stream.getvalue(),'application/zip',{'Content-Disposition':f'attachment; filename="documento-{vid}.zip"'},(actor,{'version_id':vid,'purpose':'download','device':session['device']}))
                    if method=='GET' and action=='file':
                        name=parse_qs(url.query).get('path',[''])[0];f=next((f for f in json.loads(row['files']) if f['path']==name),None)
                        if not f:raise Problem(404,'Archivo no disponible.')
                        data=self.store.read_blob(f['sha256']);is_image=Path(name).suffix.lower() in {'.jpg','.jpeg','.png','.webp'}
                        ctype=mimetypes.guess_type(name)[0] if is_image else 'text/plain; charset=utf-8'
                        self.store.audit('file_opened',actor,version_id=vid,file_hash=f['sha256'],device=session['device'])
                        return self.send(200,data,ctype,transfer=(actor,{'version_id':vid,'purpose':'preview','file_hash':f['sha256']}))
            if path in {'/api/audit','/api/audit/verify'} and method=='GET':
                if actor['role'] not in {'admin','revisor','auditor'}:raise Problem(403,'Rol no autorizado para auditoría.')
                if path.endswith('/verify'):return self.send(200,self.store.verify_audit())
                with self.store.lock:
                    rows=self.store.db.execute('SELECT * FROM audit ORDER BY seq DESC LIMIT 2000').fetchall()
                    events=[{'seq':r['seq'],**json.loads(r['event']),'mac':r['mac']} for r in rows]
                    if actor['role']!='admin':events=[e for e in events if e.get('unit')==actor['unit']]
                    self.store.audit('audit_viewed',actor)
                return self.send(200,{'events':events[:300]})
            if path=='/api/users':
                if actor['role']!='admin':raise Problem(403,'Se requiere administrador.')
                if method=='GET':
                    with self.store.lock:users=[self.store.clean_user(r) for r in self.store.db.execute('SELECT * FROM users ORDER BY username')]
                    self.store.audit('users_viewed',actor);return self.send(200,{'users':users})
                if method=='POST':
                    d=self.body();uid=self.store.create_user(d.get('username',''),d.get('password',''),d.get('role',''),d.get('unit',''),actor);return self.send(201,{'id':uid})
            match=re.fullmatch(r'/api/users/([a-f0-9]{32})/active',path)
            if method=='POST' and match:
                if actor['role']!='admin':raise Problem(403,'Se requiere administrador.')
                uid=match.group(1);d=self.body()
                if uid==actor['id']:raise Problem(400,'No puede desactivar su propia cuenta.')
                if type(d.get('active')) is not bool:raise Problem(400,'Estado inválido.')
                with self.store.lock:
                    if not self.store.db.execute('SELECT 1 FROM users WHERE id=?',(uid,)).fetchone():raise Problem(404,'Usuario no disponible.')
                    self.store.db.execute('UPDATE users SET active=? WHERE id=?',(int(d['active']),uid));self.store.audit('user_status_changed',actor,target_user=uid,active=d['active'])
                return self.send(200,{'ok':True})
            if method=='POST' and path=='/api/device-events':
                data=self.body();events=data.get('events')
                if not isinstance(events,list) or len(events)>100:raise Problem(400,'Máximo 100 eventos por envío.')
                accepted=[]
                with self.store.lock:
                    for e in events:
                        if not isinstance(e,dict) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',e.get('event_id','')) or e.get('action') not in {'local_open','local_search','local_export','local_report_created'} or len(canonical(e))>2048:raise Problem(400,'Evento inválido.')
                    for e in events:
                        existing=self.store.db.execute('SELECT payload FROM device_events WHERE user_id=? AND device=? AND event_id=?',(actor['id'],session['device'],e['event_id'])).fetchone()
                        if existing and existing['payload']!=canonical(e).decode():raise Problem(409,'Identificador de evento reutilizado con otro contenido.')
                    for e in events:
                        exists=self.store.db.execute('SELECT 1 FROM device_events WHERE user_id=? AND device=? AND event_id=?',(actor['id'],session['device'],e['event_id'])).fetchone()
                        if not exists:
                            self.store.db.execute('INSERT INTO device_events VALUES(?,?,?,?)',(actor['id'],session['device'],e['event_id'],canonical(e).decode()))
                            self.store.audit('device_event_received',actor,device=session['device'],reported_event=e,trust='client_reported_not_hardware_attested')
                        accepted.append(e['event_id'])
                return self.send(200,{'accepted':accepted,'server_time':now()})
            raise Problem(404,'Ruta no disponible.')
        except Problem as e:
            self.store.audit('request_rejected',actor,method=method,status=e.status)
            self.send(e.status,{'error':e.message})
        except Exception as e:
            # Keep sensitive content and exception details out of HTTP responses.
            try:self.store.audit('server_error',actor,error_type=type(e).__name__)
            except Exception:pass
            self.send(500,{'error':'Error interno; revise integridad, espacio disponible y bitácora.'})
    def do_GET(self):self.dispatch('GET')
    def do_POST(self):self.dispatch('POST')

def bootstrap(store):
    with store.lock:
        if store.db.execute('SELECT count(*) FROM users').fetchone()[0]:return
        credentials=[]
        for username,role,unit in [('admin','admin','DEMO_A'),('revisor_a','revisor','DEMO_A'),('agente_a','agente','DEMO_A'),('agente_b','agente','DEMO_B'),('auditor_a','auditor','DEMO_A')]:
            password=secrets.token_urlsafe(18);store.create_user(username,password,role,unit)
            credentials.append(f'{username} | {role} | {unit} | {password}')
        (store.folder/'CREDENCIALES_LOCALES.txt').write_text('CUENTAS DEL PROTOTIPO LOCAL\nNo compartir ni incluir en el ZIP de código.\nUsuario | Rol | Unidad | Contraseña\n\n'+'\n'.join(credentials)+'\n',encoding='utf-8')
        agent=store.clean_user(store.db.execute("SELECT * FROM users WHERE username='agente_a'").fetchone())
        reviewer=store.clean_user(store.db.execute("SELECT * FROM users WHERE username='revisor_a'").fetchone())
        sample=ROOT/'ejemplos'/'paquete_demo.zip'
        if sample.exists():
            result=store.upload(agent,{'title':'Informe sintético · Recepción de documentos','files':[{'path':'paquete_demo.zip','base64':base64.b64encode(sample.read_bytes()).decode()}]},'bootstrap-demo-0001')
            store.review(reviewer,result['version_id'],'approved','Ejemplo inicial sintético; aprobación de demostración.')
        store.upload(agent,{'title':'Entrega sintética · Pendiente de revisión','files':[{'path':'contenido.md','base64':base64.b64encode(b'# Entrega sintetica pendiente\n\nDocumento de prueba. Sin datos personales ni expedientes reales.\n\n## Revision solicitada\n\n- Verificar archivos.\n- Revisar fuentes sinteticas.\n- Aprobar o rechazar con un motivo.\n').decode()}]},'bootstrap-pending-0001')

def process_lock(folder):
    """One writer process per data directory, including offline maintenance."""
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    handle=open(folder/'.process.lock','a+b')
    handle.seek(0,2)
    if handle.tell()==0:handle.write(b'0');handle.flush()
    handle.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        handle.close();raise RuntimeError('La carpeta ya está abierta por otro proceso. Detenga el servidor antes del mantenimiento.')
    return handle

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);parser.add_argument('--data-dir',default=str(ROOT/'.data'));parser.add_argument('--backup');parser.add_argument('--restore');args=parser.parse_args()
    if args.restore:
        import getpass
        restore_backup(args.restore,getpass.getpass('Contraseña del respaldo: '),args.data_dir);print('Restauración verificada.');return
    lock_handle=process_lock(args.data_dir)
    store=Store(args.data_dir)
    (store.folder/'PUBLIC_KEY.txt').write_text(store.public_key+'\n',encoding='ascii')
    if args.backup:
        import getpass
        store.backup(getpass.getpass('Contraseña nueva del respaldo (16 caracteres mínimo): '),args.backup);print('Respaldo cifrado creado.');return
    bootstrap(store);server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.store=store
    print(f'Prototipo local: http://127.0.0.1:{args.port}\nCredenciales: {store.folder / "CREDENCIALES_LOCALES.txt"}\nNo publicar este servidor en Internet.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();store.db.close()

if __name__=='__main__':main()
