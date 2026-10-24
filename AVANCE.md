# Avance del servidor local

Fecha UTC: 20261024T223225Z
Base del cerebro conocida: 0.6.0. No releído ni modificado remotamente en esta tarea.

El usuario pidió programar de inmediato y señaló que disponía de menos de una hora. Se construyó y dejó encendido un prototipo local funcional, con código, UI y cliente de referencia. Se utilizó Python estándar y SQLite por disponibilidad del entorno, en lugar del FastAPI/PostgreSQL antes propuesto. No se instalaron dependencias ni se contrató alojamiento; se usó cryptography 50.0.2 del runtime ya disponible.

Implementado: cuentas, permisos por unidad/rol/propietario, carga de Markdown/ZIP/carpetas, bloques reanudables cifrados, idempotencia, duplicados de paquetes y archivos renombrados, versiones/conflictos, revisión, descarga, manifiesto Ed25519, cliente de aplicación atómica, auditoría HMAC y eventos declarados offline, respaldo/restauración y mantenimiento offline.

Verificación: 19 pruebas aprobadas y recorrido UI con datos sintéticos. Evidencia y límites en VALIDACION.md. Los originales y las conversiones anteriores no se modificaron ni importaron. No hay implementación de huella ni autorización por expediente; no es una liberación institucional.

Archivos de trabajo: server.py, sync_client.py, manage.py, requirements.txt, web/index.html, web/app.js, web/style.css, tests/test_server.py, INICIAR.cmd, ABRIR_PANEL.cmd, ejemplos/paquete_demo.zip, README.md, API.md, VALIDACION.md, evidencia/, este avance y su relevo. Las claves, cuentas y base de la instancia local viven en .data/ y se excluyen del ZIP y del aporte documental.

Subida a Drive: pendiente de subir o verificar. No se dispone de escritura de Drive verificada en esta sesión. Hay una copia nueva propia en APORTES/codex-local, sin sobrescribir trabajo ajeno.
