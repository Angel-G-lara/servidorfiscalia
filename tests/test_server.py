import base64, io, json, shutil, sqlite3, sys, tempfile, threading, unittest, urllib.request, urllib.error, zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Store, Handler, ThreadingHTTPServer, Problem, unpack_files, restore_backup, canonical, sha, CHUNK_BYTES, bootstrap, process_lock
from sync_client import synchronize
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PASSWORD='Prueba-sintetica-2026!'
def payload(text='# Informe sintético\nSin datos personales.',name='contenido.md',title='Entrega sintética'):
    return {'title':title,'files':[{'path':name,'base64':base64.b64encode(text.encode()).decode()}]}

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.store=Store(Path(cls.temp.name)/'data')
        cls.actors={}
        for username,role,unit in [('admin','admin','A'),('reviewer','revisor','A'),('agent_a','agente','A'),('agent_b','agente','B'),('auditor','auditor','A')]:
            uid=cls.store.create_user(username,PASSWORD,role,unit)
            cls.actors[username]=cls.store.clean_user(cls.store.db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone())
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),Handler);cls.http.store=cls.store
        cls.port=cls.http.server_port;cls.url=f'http://127.0.0.1:{cls.port}'
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.store.db.close();cls.temp.cleanup()
    def request(self,path,method='GET',data=None,session=None,extra=None):
        headers={**(extra or {})}
        if data is not None:headers['Content-Type']='application/json'
        if session:headers.update({'Cookie':'session='+session['token'],'X-CSRF-Token':session['csrf']})
        req=urllib.request.Request(self.url+path,data=canonical(data) if data is not None else None,headers=headers,method=method)
        try:
            with urllib.request.urlopen(req,timeout=15) as response:return response.status,response.read(),response.headers
        except urllib.error.HTTPError as e:return e.code,e.read(),e.headers
    def session(self,name):
        status,body,headers=self.request('/api/login','POST',{'username':name,'password':PASSWORD,'device':'test-device-0001'})
        self.assertEqual(status,200);data=json.loads(body);data['token']=headers['Set-Cookie'].split(';')[0].split('=',1)[1];return data
    def upload(self,name='agent_a',suffix='workflow'):
        session=self.session(name);data=payload('# Sintético '+suffix)
        status,body,_=self.request('/api/uploads','POST',data,session,{'Idempotency-Key':'operation-'+suffix})
        self.assertEqual(status,200,body);return session,data,json.loads(body)

    def test_01_end_to_end_permissions_review_download_signature(self):
        agent,data,result=self.upload(suffix='end-to-end');vid=result['version_id']
        reviewer=self.session('reviewer');other=self.session('agent_b')
        status,_,_=self.request(f'/api/versions/{vid}/download',session=other);self.assertEqual(status,404)
        status,body,_=self.request('/api/sync/manifest',session=agent);self.assertNotIn(vid,body.decode())
        status,_,_=self.request(f'/api/versions/{vid}/review','POST',{'status':'approved'},agent);self.assertEqual(status,403)
        status,body,_=self.request(f'/api/versions/{vid}/review','POST',{'status':'approved'},reviewer);self.assertEqual(status,200,body)
        status,body,_=self.request('/api/sync/manifest',session=agent);self.assertEqual(status,200);signed=json.loads(body)
        raw=base64.b64decode(signed['canonical_base64']);self.assertEqual(json.loads(raw),signed['manifest'])
        Ed25519PublicKey.from_public_bytes(base64.b64decode(signed['public_key_base64'])).verify(base64.b64decode(signed['signature_base64']),raw)
        self.assertIn(vid,body.decode())
        status,body,_=self.request(f'/api/versions/{vid}/download',session=agent);self.assertEqual(status,200)
        with zipfile.ZipFile(io.BytesIO(body)) as z:self.assertEqual(z.read('contenido.md').decode(),'# Sintético end-to-end')
        status,body,_=self.request(f'/api/versions/{vid}/file?path=contenido.md',session=agent);self.assertEqual(status,200)
        self.assertEqual(body.decode(),'# Sintético end-to-end')

    def test_02_duplicate_and_retry(self):
        session,data,r=self.upload(suffix='duplicate-check')
        status,body,_=self.request('/api/uploads','POST',data,session,{'Idempotency-Key':'operation-duplicate-check'})
        self.assertEqual(status,200);self.assertTrue(json.loads(body)['retry']);self.assertEqual(json.loads(body)['version_id'],r['version_id'])
        status,body,_=self.request('/api/uploads','POST',data,session,{'Idempotency-Key':'another-operation-duplicate'})
        self.assertEqual(status,200);self.assertTrue(json.loads(body)['duplicate'])
        changed=payload('# Cambió')
        status,_,_=self.request('/api/uploads','POST',changed,session,{'Idempotency-Key':'operation-duplicate-check'});self.assertEqual(status,409)

    def test_03_versions_conflict(self):
        session,data,r=self.upload(suffix='versions-check');d=payload('# Nueva versión');d.update(document_id=r['document_id'],base_version=1)
        status,body,_=self.request('/api/uploads','POST',d,session,{'Idempotency-Key':'new-version-0001'});self.assertEqual(status,200,body);self.assertEqual(json.loads(body)['version'],2)
        status,_,_=self.request('/api/uploads','POST',d,session,{'Idempotency-Key':'new-version-0002'});self.assertEqual(status,409)

    def test_04_csrf_origin_host(self):
        session=self.session('agent_a');session['csrf']='incorrecto'
        self.assertEqual(self.request('/api/uploads','POST',payload(),session,{'Idempotency-Key':'csrf-operation'})[0],403)
        self.assertEqual(self.request('/api/health',extra={'Origin':'https://otro.example'})[0],403)
        self.assertEqual(self.request('/api/health',extra={'Host':'attacker.example'})[0],403)
        self.assertEqual(self.request('/api/documents')[0],401)

    def test_05_zip_traversal_and_limits(self):
        for name in ['../escape.md','/absolute.md','C:/file.md','x\\file.md','x/../file.md','a//b.md','malware.exe']:
            with self.assertRaises(Problem):unpack_files(payload(name=name)['files'])
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:z.writestr('../escape.md','bad')
        with self.assertRaises(Problem):unpack_files([{'path':'test.zip','base64':base64.b64encode(buf.getvalue()).decode()}])
        with self.assertRaises(Problem):unpack_files([{'path':'x.png','base64':'AAAA'}])
        with self.assertRaises(Problem):unpack_files([{'path':'x.md','base64':'/w=='}])
        with self.assertRaises(Problem):unpack_files([{'path':'x.md','base64':'not base64!'}])

    def test_06_zip_images_and_encryption(self):
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w') as z:
            z.writestr('contenido.md','# Sintético\n![Foto](imagenes/foto.png)');z.writestr('imagenes/foto.png',b'fake-image-for-transport')
        files=unpack_files([{'path':'paquete.zip','base64':base64.b64encode(buf.getvalue()).decode()}]);self.assertEqual(len(files),2)
        digest=self.store.blob(b'secreto-sintetico-en-prueba')
        raw=(self.store.blobs/digest).read_bytes();self.assertNotIn(b'secreto-sintetico-en-prueba',raw)
        self.assertEqual(self.store.read_blob(digest),b'secreto-sintetico-en-prueba')

    def test_07_disabled_session(self):
        uid=self.store.create_user('temporary',PASSWORD,'agente','A');token,csrf,_=self.store.login('temporary',PASSWORD,'test-device-0001','127.0.0.1')
        admin=self.session('admin');self.assertEqual(self.request(f'/api/users/{uid}/active','POST',{'active':False},admin)[0],200)
        self.assertEqual(self.request('/api/documents',session={'token':token,'csrf':csrf})[0],401)

    def test_08_auditor_cannot_read_or_upload(self):
        auditor=self.session('auditor');self.assertEqual(self.request('/api/uploads','POST',payload(),auditor,{'Idempotency-Key':'auditor-upload-0001'})[0],403)
        self.assertEqual(self.request('/api/sync/manifest',session=auditor)[0],403)
        self.assertEqual(self.request('/api/audit',session=auditor)[0],200)
        self.assertEqual(self.request('/api/audit',session=self.session('agent_a'))[0],403)

    def test_09_offline_event_deduplication(self):
        agent=self.session('agent_a');data={'events':[{'event_id':'offline-0001','action':'local_open','local_time':'2026-10-24T00:00:00Z','document_id':'synthetic'}]}
        for _ in range(2):self.assertEqual(self.request('/api/device-events','POST',data,agent)[0],200)
        count=self.store.db.execute('SELECT count(*) FROM device_events WHERE event_id=?',('offline-0001',)).fetchone()[0];self.assertEqual(count,1)
        data['events'][0]['action']='local_export';self.assertEqual(self.request('/api/device-events','POST',data,agent)[0],409)

    def test_10_audit_chain_append_only(self):
        self.assertTrue(self.store.verify_audit()['valid'])
        with self.assertRaises(sqlite3.IntegrityError):self.store.db.execute("UPDATE audit SET event='{}' WHERE seq=1")
        with self.assertRaises(sqlite3.IntegrityError):self.store.db.execute('DELETE FROM audit WHERE seq=1')
        with tempfile.TemporaryDirectory() as folder:
            s=Store(folder);s.audit('test');s.db.execute('DROP TRIGGER audit_no_update');s.db.execute("UPDATE audit SET event='{}' WHERE seq=1")
            self.assertFalse(s.verify_audit()['valid']);s.db.close()

    def test_11_backup_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            backup=Path(folder)/'backup.enc';destination=Path(folder)/'restored';password='respaldo-seguro-sintetico-2026'
            self.store.backup(password,backup);self.assertNotIn(b'SQLite format',backup.read_bytes())
            restore_backup(backup,password,destination);restored=Store(destination)
            self.assertTrue(restored.verify_audit()['valid']);self.assertEqual(restored.db.execute('SELECT count(*) FROM documents').fetchone()[0],self.store.db.execute('SELECT count(*) FROM documents').fetchone()[0]);restored.db.close()
            with self.assertRaises(Problem):restore_backup(backup,password,destination)

    def test_12_login_failures_and_throttle(self):
        for i in range(8):self.assertEqual(self.request('/api/login','POST',{'username':'doesnotexist','password':'bad','device':'test-device-0001'})[0],401)
        self.assertEqual(self.request('/api/login','POST',{'username':'doesnotexist','password':'bad','device':'test-device-0001'})[0],429)

    def test_13_user_administration_permissions(self):
        self.assertEqual(self.request('/api/users',session=self.session('agent_a'))[0],403)
        admin=self.session('admin');self.assertEqual(self.request('/api/users','POST',{'username':'created_user','password':PASSWORD,'role':'agente','unit':'B'},admin)[0],201)
        self.assertEqual(self.request('/api/users','POST',{'username':'created_user','password':PASSWORD,'role':'agente','unit':'B'},admin)[0],409)

    def test_14_no_cross_unit_duplicate_disclosure(self):
        _,data,a=self.upload(suffix='cross-unit-duplicate')
        session=self.session('agent_b');status,body,_=self.request('/api/uploads','POST',data,session,{'Idempotency-Key':'unit-b-duplicate-001'})
        self.assertEqual(status,200);b=json.loads(body);self.assertFalse(b['duplicate']);self.assertNotEqual(a['document_id'],b['document_id'])

    def test_15_resumable_encrypted_chunks(self):
        agent=self.session('agent_a');other=self.session('agent_b');data=payload('# Paquete grande\n'+'contenido sintético\n'*45000);raw=canonical(data)
        begin={'total_bytes':len(raw),'sha256':sha(raw)};headers={'Idempotency-Key':'resumable-operation-01'}
        status,body,_=self.request('/api/uploads/start','POST',begin,agent,headers);self.assertEqual(status,200);sid=json.loads(body)['upload_id']
        chunk=lambda index:{'index':index,'base64':base64.b64encode(raw[index*CHUNK_BYTES:(index+1)*CHUNK_BYTES]).decode()}
        self.assertEqual(self.request(f'/api/uploads/{sid}/chunk','POST',chunk(0),agent)[0],200)
        self.assertEqual(self.request(f'/api/uploads/{sid}/complete','POST',{},agent)[0],409)
        self.assertEqual(self.request(f'/api/uploads/{sid}/chunk','POST',chunk(0),other)[0],404)
        status,body,_=self.request('/api/uploads/start','POST',begin,agent,headers);self.assertEqual(status,200);self.assertIn('0',json.loads(body)['received'])
        stage=(self.store.staging/sid/'0').read_bytes();self.assertNotIn(b'Paquete grande',stage)
        for index in range(1,(len(raw)+CHUNK_BYTES-1)//CHUNK_BYTES):self.assertEqual(self.request(f'/api/uploads/{sid}/chunk','POST',chunk(index),agent)[0],200)
        status,body,_=self.request(f'/api/uploads/{sid}/complete','POST',{},agent);self.assertEqual(status,200,body)
        status,body,_=self.request(f'/api/uploads/{sid}/complete','POST',{},agent);self.assertEqual(status,200);self.assertTrue(json.loads(body)['retry'])
        self.assertFalse((self.store.staging/sid).exists())

    def test_16_atomic_verified_sync_and_tamper_rejection(self):
        agent,_,r=self.upload(suffix='sync-client-check');reviewer=self.session('reviewer')
        self.assertEqual(self.request(f'/api/versions/{r["version_id"]}/review','POST',{'status':'approved'},reviewer)[0],200)
        def fetch(path):
            status,body,_=self.request(path,session=agent)
            if status!=200:raise ValueError('HTTP '+str(status))
            return body
        with tempfile.TemporaryDirectory() as folder:
            state=synchronize(fetch,folder,self.store.public_key)
            self.assertTrue((Path(folder)/state['snapshot']/r['document_id']/'contenido.md').exists())
            pointer=(Path(folder)/'current.json').read_bytes()
            def bad_fetch(path):
                data=fetch(path)
                if path.endswith('/download'):
                    buffer=io.BytesIO()
                    with zipfile.ZipFile(io.BytesIO(data)) as source,zipfile.ZipFile(buffer,'w') as target:
                        for name in source.namelist():target.writestr(name,b'alterado')
                    return buffer.getvalue()
                return data
            with self.assertRaises(ValueError):synchronize(bad_fetch,folder,self.store.public_key)
            self.assertEqual(pointer,(Path(folder)/'current.json').read_bytes())
            self.assertFalse(any(p.name.startswith('tmp-') for p in (Path(folder)/'snapshots').iterdir()))

    def test_17_bootstrap_is_idempotent(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Store(folder);bootstrap(store);bootstrap(store)
            self.assertEqual(store.db.execute('SELECT count(*) FROM users').fetchone()[0],5)
            self.assertEqual(store.db.execute('SELECT count(*) FROM documents').fetchone()[0],2)
            self.assertTrue((Path(folder)/'CREDENCIALES_LOCALES.txt').exists());self.assertTrue(store.verify_audit()['valid']);store.db.close()

    def test_18_single_process_lock(self):
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            lock=process_lock(folder)
            try:
                result=subprocess.run([sys.executable,'-c','from server import process_lock; import sys; process_lock(sys.argv[1])',folder],cwd=str(Path(__file__).resolve().parents[1]),capture_output=True,timeout=15)
                self.assertNotEqual(result.returncode,0)
            finally:lock.close()
            second=process_lock(folder);second.close()

    def test_19_renamed_file_duplicate_detected(self):
        session,data,r=self.upload(suffix='renamed-file-check')
        renamed=payload('# Sintético renamed-file-check',name='otro_nombre.md')
        status,body,_=self.request('/api/uploads','POST',renamed,session,{'Idempotency-Key':'renamed-file-operation'})
        self.assertEqual(status,200);result=json.loads(body);self.assertFalse(result['duplicate'])
        self.assertEqual(result['matching_files'][0]['path'],'otro_nombre.md')
        self.assertTrue(any(m['version_id']==r['version_id'] for m in result['matching_files'][0]['matches']))

if __name__=='__main__':unittest.main(verbosity=2)
