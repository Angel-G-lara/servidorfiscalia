# Contrato HTTP del prototipo 0.1

Base local: `http://127.0.0.1:8765`. Sin CORS abierto. Todas las respuestas de datos usan `Cache-Control: no-store`.

## Sesión

`POST /api/login` recibe JSON con `username`, `password`, `device` (8–80 caracteres alfanuméricos, guion o guion bajo). Responde `user`, `csrf` y cookie HttpOnly `session`. La sesión caduca por 30 minutos de inactividad y se comprueba el estado de la cuenta en cada solicitud.

Conservar la cookie y enviar `X-CSRF-Token` en los POST autenticados. No poner secretos en URL. Las apps definitivas deben proteger su sesión mediante almacenamiento seguro del sistema.

- `GET /api/me`: identidad y CSRF de la sesión actual.
- `POST /api/logout`: cierra la sesión.
- `GET /api/health`: salud local, sin datos documentales.

## Documentos y versiones

- `GET /api/documents`: versiones visibles. Agentes ven publicaciones de su unidad y sus propios borradores; revisores/admin ven su unidad; auditores no ven contenido.
- `POST /api/uploads`: carga directa, JSON de hasta 36 MB. Requiere `Idempotency-Key`. Cuerpo: `title`, `files: [{path, base64}]`. Opcional: `document_id`, `base_version` para crear una versión de un documento existente. Responde identificadores, estado, digest y `duplicate`.
- `POST /api/uploads/start`: alternativa reanudable usada por la interfaz. Requiere `Idempotency-Key`. Cuerpo: `total_bytes` y `sha256` de los bytes UTF-8 del JSON de carga completo. Responde `upload_id`, `chunk_bytes: 524288`, `received` y `result` si ya terminó.
- `POST /api/uploads/{upload_id}/chunk`: JSON `index` (desde cero), `base64` del bloque. Solo el propietario de la sesión de carga puede enviarlo. Los bloques repetidos deben ser idénticos.
- `POST /api/uploads/{upload_id}/complete`: JSON `{}`. Comprueba todos los bloques y la carga completa y ejecuta la recepción idempotente. Una repetición devuelve el resultado previo.
- `POST /api/versions/{version_id}/review`: `status: approved|rejected`, `note`. Revisor/admin de la unidad. Rechazo requiere motivo. Una versión revisada no se vuelve a revisar.
- `GET /api/versions/{version_id}/file?path=...`: contenido autorizado por ruta exacta del manifiesto. Markdown como texto; imágenes con MIME y `nosniff`.
- `GET /api/versions/{version_id}/download`: ZIP del paquete. Registra autorización, escritura o interrupción de transferencia.
- `GET /api/sync/manifest`: últimas versiones aprobadas para la cuenta/unidad. Responde `manifest`, `canonical_base64`, `signature_base64` y `public_key_base64`. Verificar con una clave pública previamente fijada, no confiar simplemente en la clave incluida en la respuesta.

Un duplicado exacto devuelve la versión existente solo si el usuario ya tiene acceso a ella. Una coincidencia en otra unidad no se revela. Cambiar foto, anexo o ruta cambia el manifiesto del paquete. `matching_files` informa archivos con bytes idénticos en versiones accesibles, aunque sus nombres difieran, sin fusionar entregas. No hay normalización de nombres ni fusión de identidades.

## Auditoría y eventos offline

- `GET /api/audit`: hasta 300 eventos recientes visibles. Admin ve metadatos globales; revisor/auditor solo su unidad. No muestra contraseñas ni contenido de expedientes.
- `GET /api/audit/verify`: comprueba la cadena HMAC de eventos presentes. No es certificación independiente ni prueba de que no se truncó el historial.
- `POST /api/device-events`: `events`, hasta 100. Cada evento requiere `event_id` y `action` de `local_open`, `local_search`, `local_export`, `local_report_created`. Se recomienda `local_time`, identificador del documento y secuencia local sin incluir contenido sensible. Un mismo ID con contenido diferente produce 409. La respuesta `accepted` confirma los IDs recibidos. Son eventos declarados por el cliente, sin atestación de hardware ni detección completa de huecos en esta versión.

## Administración

- `GET /api/users`: catálogo de cuentas; solo admin.
- `POST /api/users`: `username`, `password` (12–256 caracteres), `role: admin|revisor|agente|auditor`, `unit`.
- `POST /api/users/{id}/active`: `active: true|false`. No permite desactivar la propia cuenta.
- `POST /api/admin/shutdown`: solicita detener este proceso local; solo admin.

## Errores

401 sesión ausente o inválida; 403 rol/CSRF/origen no autorizado; 404 recurso no disponible (incluye recursos ajenos); 409 conflicto de versión u operación; 413 tamaño excesivo; 429 límite de intentos; 507 capacidad temporal reservada agotada. Los errores contienen `error`, sin trazas o secretos.

La interfaz presenta un identificador de dispositivo, pero no es inscripción criptográfica. El protocolo HTTPS institucional y los factores de autenticación definitivos siguen pendientes. No reutilizar este contrato como declaración de seguridad validada.
