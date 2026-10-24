"""Mantenimiento offline. Detener primero el servidor."""
import argparse, getpass, json, re, shutil, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from server import Store, process_lock, password_hash, ROOT

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',default=str(ROOT/'.data'))
    group=parser.add_mutually_exclusive_group(required=True);group.add_argument('--password',metavar='USUARIO',help='Cambiar contraseña con acceso local al equipo');group.add_argument('--purge-incomplete',action='store_true',help='Retirar bloques de cargas incompletas de más de 24 horas');args=parser.parse_args()
    if not (Path(args.data_dir)/'catalog.sqlite3').exists():raise ValueError('No existe catálogo en esa carpeta.')
    lock=process_lock(args.data_dir);store=Store(args.data_dir)
    try:
        if args.password:
            user=store.db.execute('SELECT * FROM users WHERE username=?',(args.password,)).fetchone()
            if not user:raise ValueError('Usuario inexistente.')
            password=getpass.getpass('Nueva contraseña (12 caracteres mínimo): ')
            if not 12<=len(password)<=256 or password!=getpass.getpass('Repetir contraseña: '):raise ValueError('Longitud inválida o contraseñas diferentes.')
            store.db.execute('UPDATE users SET password=? WHERE id=?',(password_hash(password),user['id']));store.audit('password_changed_offline',None,target_user=user['id'])
            credentials=store.folder/'CREDENCIALES_LOCALES.txt'
            if credentials.exists():
                lines=credentials.read_text(encoding='utf8').splitlines()
                credentials.write_text('\n'.join(' | '.join(line.split(' | ')[:3]+['[modificada en mantenimiento]']) if line.startswith(args.password+' | ') else line for line in lines)+'\n',encoding='utf8')
            print('Contraseña cambiada. Inicie el servidor y use la contraseña elegida.')
        else:
            cutoff=(datetime.now(timezone.utc)-timedelta(hours=24)).isoformat(timespec='milliseconds')
            rows=store.db.execute('SELECT * FROM upload_sessions WHERE result IS NULL AND created<?',(cutoff,)).fetchall();count=0
            for row in rows:
                if not re.fullmatch('[a-f0-9]{32}',row['id']):raise ValueError('ID de carga inesperado; no se retira contenido.')
                target=(store.staging/row['id']).resolve()
                if target.parent!=store.staging.resolve():raise ValueError('Ruta temporal fuera de la carpeta esperada.')
                if target.exists():shutil.rmtree(target)
                store.db.execute('DELETE FROM upload_sessions WHERE id=?',(row['id'],));store.audit('incomplete_upload_purged',None,upload_id=row['id']);count+=1
            print(f'Cargas incompletas retiradas: {count}. Los documentos recibidos no se modificaron.')
    finally:store.db.close();lock.close()

if __name__=='__main__':main()
