# Servidor Fiscalía - Backend Node.js + Supabase

Backend Node.js para gestión documental fiscalía con Supabase y Google OAuth. Desplegado como monorepo en Vercel.

## Versión Node.js (Actual)

Este proyecto ahora usa un backend en Node.js con:
- ✅ Express.js + Supabase
- ✅ Google OAuth authentication
- ✅ JWT tokens
- ✅ REST API
- ✅ Sistema de roles (admin, revisor, agente, auditor)
- ✅ Despliegue en Vercel

## Versión Python (Legacy)

El backend Python original está incluido pero no se usa en producción. Ver directorio `backend/` para la versión actual.

## Abrir ahora

1. Abre http://127.0.0.1:8765 en este equipo. El servidor quedó iniciado durante la entrega.
2. Consulta `.data/CREDENCIALES_LOCALES.txt`: cada cuenta tiene una contraseña aleatoria distinta. No se incluyen esas contraseñas en el ZIP distribuible.
3. Entra como `admin` para probar revisión, usuarios y auditoría. Su unidad documental es DEMO_A, no tiene lectura universal de documentos.
4. Abre el informe sintético inicial y comprueba la imagen y el anexo. Existe también una entrega pendiente de revisión.
5. Sube `ejemplos/paquete_demo.zip` como documento nuevo para probar la detección de duplicado exacto. Cambia el contenido para crear otra entrega.
6. En Documentos, aprueba o rechaza una versión. En Actualizaciones, consulta y descarga el manifiesto firmado. En Auditoría, revisa eventos y verifica la cadena.

El servicio escucha solo en 127.0.0.1. Desde un teléfono, `127.0.0.1` sería el propio teléfono: esta entrega todavía no ofrece conexión por la red ni por Internet. No abras puertos para exponer este prototipo.

## Iniciar y detener

En este equipo, ejecuta `INICIAR.cmd` para arrancarlo y `ABRIR_PANEL.cmd` para abrir el navegador. Si ya está ejecutándose, no inicies una segunda instancia. Usa Detener servidor desde la sesión de administrador o Ctrl+C en la consola donde lo iniciaste. El arranque verifica la cadena de auditoría y bloquea otra instancia sobre la misma carpeta de datos.

El lanzador usa el Python preparado por Codex en este equipo o una `.venv` local si existe. Para otro equipo con Python 3.11 o superior:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe server.py
```

No se requieren FastAPI, Docker o servicios contratados para esta demostración. Se eligió la biblioteca HTTP estándar de Python y SQLite para evitar depender de instalaciones durante la entrega. `cryptography==50.0.2` es la dependencia utilizada y comprobada.

## Funciones implementadas

- Cuentas individuales, contraseñas PBKDF2 con sal, límite de intentos, sesiones HttpOnly y protección CSRF/Host/Origin para el entorno local.
- Roles admin, revisor, agente y auditor. Separación por unidad; borradores visibles a su propietario y a revisores de esa unidad. Auditor sin contenido documental.
- Alta y activación/desactivación de cuentas. La desactivación invalida el uso de sus sesiones en la siguiente solicitud al servidor.
- Subida de Markdown individual, varios archivos, carpeta o ZIP. Se requieren rutas relativas seguras y al menos un Markdown UTF-8.
- Límite de 25 MB descomprimidos y 100 archivos por paquete; bloqueo de rutas de escape, enlaces simbólicos en ZIP y extensiones no admitidas. No hay análisis antivirus en esta versión.
- Subida por bloques de 512 KB, cifrados temporalmente, con reanudación y verificación del hash del contenido completo. La UI recuerda la operación para el mismo usuario y contenido. No se borra la copia original del usuario.
- Reintentos idempotentes: repetir una operación no crea otro reporte. Reutilizarla con otro contenido produce conflicto.
- Coincidencias de archivos por SHA-256 aunque cambie el nombre, mostrando solo referencias accesibles al usuario. Una ruta distinta se conserva como nueva entrega pendiente, sin fusionarla automáticamente.
- Duplicados exactos por manifiesto de rutas, tamaños y hashes SHA-256 de todos los archivos. Mantiene una recepción en la auditoría y referencia la versión accesible existente; no elimina documentos. Los mismos bytes pueden compartir almacenamiento cifrado sin compartir permisos o revelar coincidencias entre unidades.
- Nuevas versiones con número de versión base y detección de conflictos. Una versión revisada no se modifica; se crea una nueva.
- Aprobación/rechazo por revisor o administrador de la unidad; las aprobadas son las distribuidas por el manifiesto.
- Vista de Markdown y fotografías con rutas locales autenticadas. El visor implementa un subconjunto de Markdown: encabezados, párrafos, listas, bloques de código e imágenes en líneas independientes. No ejecuta HTML ni carga imágenes externas. No altera el Markdown original. Los PDF permanecen como anexos descargables.
- Archivos cifrados con AES-GCM, hashes verificados y catálogo SQLite. El catálogo y las claves locales no usan protección de hardware ni cifrado integral del equipo: el cifrado de archivos no protege frente a quien controla esta carpeta y sus claves.
- Manifiesto Ed25519 de la última versión aprobada por documento para la unidad. La clave pública está en `.data/PUBLIC_KEY.txt`; debe provisionarse de manera confiable, no aceptarse sin comprobar desde cualquier servidor.
- Bitácora con eventos UTC, cuenta, unidad, dispositivo informado, referencias, resultados, hashes y cadena HMAC. Disparadores impiden UPDATE/DELETE ordinarios. Se distingue autorización de descarga y escritura de transferencia; no se afirma lectura humana ni recepción final garantizada por el dispositivo.
- Recepción idempotente de eventos declarados por un cliente offline, diferenciando su fecha declarada de la recepción del servidor. No certifica que esos eventos sean completos o provengan de hardware confiable.
- Respaldo cifrado con contraseña y restauración a carpeta vacía, conservando catálogo, archivos y claves.

La bitácora es local: un administrador del sistema con claves y control de disco puede reescribirla o truncarla. La cadena verifica consistencia de los eventos presentes; necesita anclaje y retención independientes para una auditoría institucional. No observa accesos directos al disco, capturas externas ni acciones en aplicaciones ajenas.

## Prueba recomendada

| Cuenta | Unidad | Prueba |
|---|---|---|
| admin | DEMO_A | Revisar, crear usuarios y consultar auditoría global de metadatos. |
| revisor_a | DEMO_A | Aprobar o rechazar entregas de su unidad. |
| agente_a | DEMO_A | Subir, leer su borrador y descargar publicaciones de su unidad. |
| agente_b | DEMO_B | Comprobar que no puede acceder a los documentos de DEMO_A. |
| auditor_a | DEMO_A | Ver eventos de su unidad sin subir ni leer documentos. |

Las contraseñas están exclusivamente en el archivo local de credenciales. Para crear cuentas con otras contraseñas usa Usuarios; para cambiar la contraseña de una cuenta existente, usa el mantenimiento offline descrito en `manage.py --help`.

## Cliente de actualización de referencia

Con el servidor encendido y una clave pública recibida por un canal confiable:

```powershell
.venv\Scripts\python.exe sync_client.py --username agente_a --public-key .data\PUBLIC_KEY.txt --destination datos_cliente
```

Solicita la contraseña sin mostrarla. Verifica firma, ámbito de cuenta/unidad, manifiesto de archivos, tamaños y hashes. Rechaza versiones anteriores a las ya instaladas y paquetes alterados. Descarga a una carpeta temporal y cambia `current.json` solo al completar el conjunto. Una falla conserva la referencia a la copia anterior. Mantiene separada la carpeta de reportes que se diseñe en las apps.

Este cliente de demostración guarda la copia descargada sin cifrar y conserva instantáneas previas. No implementa revocación de archivos ya descargados. No usar con información operativa. La protección del almacenamiento local, claves de hardware, eliminación controlada y permisos offline pertenecen a las apps definitivas.

## Respaldar y recuperar

Detén primero el servidor. El bloqueo de proceso impide abrir la carpeta a la vez para mantenimiento.

```powershell
.venv\Scripts\python.exe server.py --backup respaldo.enc
.venv\Scripts\python.exe server.py --restore respaldo.enc --data-dir respaldo_restaurado
.venv\Scripts\python.exe server.py --data-dir respaldo_restaurado --port 8765
```

Usa una contraseña de respaldo de al menos 16 caracteres y guárdala aparte. El archivo cifrado incluye las claves del servidor; perderlas o perder esa contraseña puede impedir recuperar datos. El ejemplo crea el archivo localmente; el responsable debe copiarlo a un destino independiente y probar restauración. La carpeta restaurada debe ser nueva o vacía. Las sesiones no se restauran.

## Ejecutar pruebas

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

En el equipo actual puede sustituirse `.venv\Scripts\python.exe` por el Python de Codex que usa INICIAR.cmd. Las pruebas crean carpetas temporales con datos sintéticos. El resultado de la entrega está en `VALIDACION.md`.

## Antes de un piloto institucional

1. Sustituir el servidor de demostración por un servicio de despliegue revisado, con HTTPS, gestión de secretos, cuentas institucionales y configuración de red autorizada.
2. Implementar permisos por expediente, acción y finalidad, además de unidad. Homologar huella y alta de equipos; no se implementa biometría en este prototipo.
3. Integrar las apps Android/PC reales, claves protegidas, autorizaciones offline con vencimiento y comprobación nueva por operación sensible. El ID de dispositivo actual es informativo y se puede copiar.
4. Incorporar análisis de archivos, cuotas por usuario, retención y limpieza de cargas incompletas. El área temporal del prototipo tiene un límite global de 256 MB; las cargas incompletas persisten hasta mantenimiento offline.
5. Definir política de revisión independiente: este prototipo permite que un administrador/revisor apruebe su propia carga dentro de su unidad. No representa una política institucional aprobada.
6. Añadir auditoría de infraestructura y accesos directos, exportación independiente protegida, alarmas, retención y recuperación operativa.
7. Evaluar PostgreSQL y almacenamiento de objetos según carga y concurrencia. La base SQLite de esta entrega no es un dimensionamiento definitivo.
8. Evaluar similitud o chatbot solo después de validar la gestión documental. Hoy se detectan duplicados exactos, no similitud semántica ni identidades.

Los tres pares de fichas previamente digitalizados no se importaron. El servidor solo se inicializó con ejemplos sintéticos. No se cambió el cerebro principal del proyecto.
