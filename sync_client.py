"""Cliente de referencia para probar descarga verificada y aplicación atómica.
Usar solo datos sintéticos: este cliente de prueba guarda la copia descargada sin cifrar.
"""
import argparse, base64, hashlib, io, json, os, secrets, shutil, urllib.request, urllib.parse, uuid, zipfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from server import canonical, sha, safe_path, Problem, MAX_BYTES, MAX_FILES

def synchronize(fetch, destination, public_key):
    """fetch(path) returns authenticated response bytes; key is provisioned separately."""
    envelope=json.loads(fetch('/api/sync/manifest'))
    raw=base64.b64decode(envelope['canonical_base64'],validate=True)
    Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key,validate=True)).verify(base64.b64decode(envelope['signature_base64'],validate=True),raw)
    manifest=json.loads(raw)
    if manifest!=envelope['manifest']:raise ValueError('El contenido del manifiesto no coincide con la firma.')
    dest=Path(destination);dest.mkdir(parents=True,exist_ok=True)
    pointer=dest/'current.json';previous=json.loads(pointer.read_text()) if pointer.exists() else None
    if previous:
        if previous['unit']!=manifest['unit'] or previous['account']!=manifest['account']:raise ValueError('La carpeta de sincronización pertenece a otra cuenta o unidad.')
        versions=previous.get('maximum_versions',{})
        for d in manifest['documents']:
            if d['version']<versions.get(d['document_id'],0):raise ValueError('Se rechazó una versión anterior a la ya instalada.')
    else:versions={}
    snapshots=dest/'snapshots';snapshots.mkdir(exist_ok=True)
    stage=snapshots/('tmp-'+uuid.uuid4().hex);stage.mkdir()
    try:
        for doc in manifest['documents']:
            if not isinstance(doc['document_id'],str) or len(doc['document_id'])!=32 or any(c not in '0123456789abcdef' for c in doc['document_id']):raise ValueError('ID de documento inválido.')
            if sha(canonical(doc['files']))!=doc['digest']:raise ValueError('El manifiesto de archivos no coincide con el paquete.')
            path='/api/versions/'+doc['version_id']+'/download'
            if doc['download']!=path:raise ValueError('Ruta de descarga inválida.')
            expected={f['path']:f for f in doc['files']}
            if len(expected)!=len(doc['files']) or len(expected)>MAX_FILES or sum(f['bytes'] for f in expected.values())>MAX_BYTES:raise ValueError('Paquete excesivo o repetido.')
            for name in expected:safe_path(name)
            archive=fetch(path)
            with zipfile.ZipFile(io.BytesIO(archive)) as z:
                if len(z.infolist())!=len(expected) or set(z.namelist())!=set(expected):raise ValueError('Los archivos recibidos difieren del manifiesto.')
                for info in z.infolist():
                    f=expected[info.filename]
                    if info.file_size!=f['bytes']:raise ValueError('Tamaño de archivo incorrecto.')
                    data=z.read(info)
                    if sha(data)!=f['sha256']:raise ValueError('Hash de archivo incorrecto.')
                    target=stage/doc['document_id']/info.filename;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            versions[doc['document_id']]=max(versions.get(doc['document_id'],0),doc['version'])
        (stage/'manifest.json').write_bytes(canonical(envelope))
        name='snapshot-'+uuid.uuid4().hex;os.replace(stage,snapshots/name)
        state={'snapshot':'snapshots/'+name,'unit':manifest['unit'],'account':manifest['account'],'manifest_hash':sha(raw),'maximum_versions':versions}
        temp=dest/('pointer-'+uuid.uuid4().hex+'.tmp');temp.write_bytes(canonical(state));os.replace(temp,pointer)
        return state
    finally:
        # Only this freshly generated staging directory may be removed on failure.
        if stage.exists() and stage.resolve().parent==snapshots.resolve() and stage.name.startswith('tmp-'):shutil.rmtree(stage)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8765');parser.add_argument('--username',required=True);parser.add_argument('--public-key',required=True,help='Archivo de clave pública previamente confiable');parser.add_argument('--destination',required=True);args=parser.parse_args()
    parsed=urllib.parse.urlsplit(args.url)
    if parsed.query or parsed.fragment or parsed.username or parsed.path not in {'','/'} or (parsed.scheme!='https' and not(parsed.scheme=='http' and parsed.hostname in {'localhost','127.0.0.1'})):raise ValueError('Use HTTPS o el servidor local, sin credenciales ni rutas en la URL.')
    import getpass,http.cookiejar
    jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar));base=args.url.rstrip('/')
    payload={'username':args.username,'password':getpass.getpass('Contraseña: '),'device':'client-'+uuid.uuid4().hex}
    req=urllib.request.Request(base+'/api/login',data=canonical(payload),headers={'Content-Type':'application/json'},method='POST')
    with opener.open(req,timeout=30) as response:json.load(response)
    def fetch(path):
        with opener.open(base+path,timeout=60) as response:
            raw=response.read(MAX_BYTES*2+1)
            if len(raw)>MAX_BYTES*2:raise ValueError('Respuesta excesiva.')
            return raw
    state=synchronize(fetch,args.destination,Path(args.public_key).read_text().strip())
    print('Actualización verificada. Nueva copia: '+str(Path(args.destination)/state['snapshot']))

if __name__=='__main__':main()
