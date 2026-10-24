# Validación de entrega 0.1.0

Fecha UTC: 20261024T223225Z

Resultado: 19 pruebas automatizadas aprobadas, sintaxis Python/JavaScript comprobada y panel local funcionando en http://127.0.0.1:8765.

## Cobertura comprobada

1. Recorrido de recepción, autorización por unidad, aprobación, manifiesto firmado y descarga íntegra.
2. Duplicados exactos y reintentos idempotentes.
3. Nuevas versiones y conflicto de versión base.
4. CSRF, Host, Origin y sesión obligatoria.
5. Rutas peligrosas, ZIP de escape, ausencia de Markdown y codificación inválida.
6. Transporte de Markdown con imagen y cifrado de archivos.
7. Desactivación de cuenta y rechazo de su sesión.
8. Auditor sin permisos de subida o lectura documental.
9. Recepción y deduplicación de eventos declarados por cliente offline.
10. Verificación de cadena HMAC, rechazo de UPDATE/DELETE ordinarios y detección de modificación.
11. Respaldo cifrado y restauración verificable a una carpeta nueva.
12. Intentos fallidos y límite de acceso.
13. Administración de cuentas y separación de roles.
14. Duplicados de otra unidad sin revelar su existencia.
15. Subida por bloques cifrados, reanudación, propiedad de la carga y finalización idempotente.
16. Cliente de actualización con firma/hashes, aplicación atómica y conservación de copia previa ante alteración.
17. Inicialización idempotente de cinco cuentas y dos documentos sintéticos.
18. Bloqueo de segunda instancia sobre la misma carpeta de datos.
19. Detección de archivos idénticos aunque cambie el nombre.

## Comprobación de interfaz

Se inició sesión en el navegador, se visualizaron el Markdown y la imagen del paquete sintético, se consultó y verificó la bitácora y se subió un ZIP desde el selector de archivos. La interfaz confirmó «Duplicado exacto detectado». Se revisó el panel en tamaño de escritorio y se inspeccionó su adaptación a 390 px. Se restauró el tamaño habitual. La consola de la página no mostró errores en la revisión realizada.

Evidencia: evidencia/panel.jpg y evidencia/duplicado.jpg. No incluyen contraseñas ni expedientes reales. Se reinició el servidor de forma controlada con el código final y se verificó nuevamente el acceso al panel.

## Límites de la verificación

Pruebas funcionales y de aislamiento básicas en un solo equipo, con datos sintéticos. No son pruebas de penetración, carga, autenticación biométrica, atestación de dispositivos, seguridad institucional o auditoría independiente. No se importaron las fichas del usuario. No se desplegó en Internet ni se conectaron apps Android/PC ya existentes.

El servidor es un prototipo HTTP local con SQLite. Los permisos actuales son por unidad/propietario/rol, no por expediente y finalidad. El cliente de referencia guarda archivos sin cifrar. La bitácora HMAC es local y no garantiza que un administrador del sistema no la reescriba o trunque. Los eventos offline son declaraciones del cliente. Véanse README.md y API.md.

## Salida de la prueba automatizada

```text
test_01_end_to_end_permissions_review_download_signature (test_server.ServerTests.test_01_end_to_end_permissions_review_download_signature) ... ok
test_02_duplicate_and_retry (test_server.ServerTests.test_02_duplicate_and_retry) ... ok
test_03_versions_conflict (test_server.ServerTests.test_03_versions_conflict) ... ok
test_04_csrf_origin_host (test_server.ServerTests.test_04_csrf_origin_host) ... ok
test_05_zip_traversal_and_limits (test_server.ServerTests.test_05_zip_traversal_and_limits) ... ok
test_06_zip_images_and_encryption (test_server.ServerTests.test_06_zip_images_and_encryption) ... ok
test_07_disabled_session (test_server.ServerTests.test_07_disabled_session) ... ok
test_08_auditor_cannot_read_or_upload (test_server.ServerTests.test_08_auditor_cannot_read_or_upload) ... ok
test_09_offline_event_deduplication (test_server.ServerTests.test_09_offline_event_deduplication) ... ok
test_10_audit_chain_append_only (test_server.ServerTests.test_10_audit_chain_append_only) ... ok
test_11_backup_restore (test_server.ServerTests.test_11_backup_restore) ... ok
test_12_login_failures_and_throttle (test_server.ServerTests.test_12_login_failures_and_throttle) ... ok
test_13_user_administration_permissions (test_server.ServerTests.test_13_user_administration_permissions) ... ok
test_14_no_cross_unit_duplicate_disclosure (test_server.ServerTests.test_14_no_cross_unit_duplicate_disclosure) ... ok
test_15_resumable_encrypted_chunks (test_server.ServerTests.test_15_resumable_encrypted_chunks) ... ok
test_16_atomic_verified_sync_and_tamper_rejection (test_server.ServerTests.test_16_atomic_verified_sync_and_tamper_rejection) ... ok
test_17_bootstrap_is_idempotent (test_server.ServerTests.test_17_bootstrap_is_idempotent) ... ok
test_18_single_process_lock (test_server.ServerTests.test_18_single_process_lock) ... ok
test_19_renamed_file_duplicate_detected (test_server.ServerTests.test_19_renamed_file_duplicate_detected) ... ok

----------------------------------------------------------------------
Ran 19 tests in 36.245s

OK

```
