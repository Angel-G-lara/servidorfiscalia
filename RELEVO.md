# Relevo del servidor 0.1.0

## Encargo y decisiones del usuario

El mensaje actual autoriza programar de inmediato el servidor y señala menos de una hora disponible. Los mensajes previos solicitan actualizaciones y subida de reportes/archivos, detección de duplicados y registro de accesos, descargas y subidas. El alcance previo conserva apps locales y Markdown. No eligió proveedor, tecnologías, políticas de retención o hardware biométrico ni autorizó gastos.

## Qué se hizo

Se programó un prototipo local en outputs/servidor_fiscalia y se inició en http://127.0.0.1:8765. Python estándar, SQLite, archivos AES-GCM, hashes SHA-256, firma Ed25519 y bitácora HMAC. Interfaz con documentos, entregas, actualizaciones, auditoría y cuentas. La carpeta .data contiene la instancia local y credenciales aleatorias; no compartir ni incluir en el ZIP de código.

Se incluyen subidas reanudables e idempotentes, aprobación/rechazo, versiones, conflictos, duplicados de paquetes y de archivos con distinto nombre, separación por unidad, manifestación firmada, cliente de referencia que verifica y aplica por cambio atómico de puntero, eventos offline declarados, respaldo/restauración y mantenimiento offline. Solo se cargaron ejemplos sintéticos. No se importaron las fichas personales digitalizadas.

## Qué se verificó

19 pruebas automatizadas aprobaron; la salida está en VALIDACION.md. Se comprobó login, visualización de Markdown/imagen, bitácora, cadena y carga desde la UI con detección de duplicado. Se reinició controladamente el proceso con el código final y se verificó acceso nuevamente. La sintaxis Python y JavaScript pasó. Evidencia en evidencia/panel.jpg y evidencia/duplicado.jpg.

## Cómo continuar sin esta conversación

Leer README.md, API.md y VALIDACION.md. El servidor está escuchando solo en loopback. Usar las cuentas en .data/CREDENCIALES_LOCALES.txt, o arrancar con INICIAR.cmd si se detuvo. Admin está en DEMO_A; no tiene lectura documental global. La cuenta agente_b permite probar aislamiento de DEMO_B. Detener desde admin antes de respaldar o mantener; las sesiones se pierden al reiniciar.

Antes de integrar al cerebro, releer su versión vigente y sus aportes. La base conocida de esta sesión es 0.6.0. No se modificaron CEREBRO.md, contexto.json ni el tablero.

## Qué falta

Validación del usuario sobre el prototipo. Integración con las apps reales Android/PC; identidad institucional y huella nueva por operación; inscripción criptográfica de equipos; permisos por expediente/acción/finalidad; políticas offline y exportación; almacenamiento local protegido del cliente; antivirus; auditoría y retención independientes; infraestructura con HTTPS y despliegue autorizado. El chatbot y la detección semántica no están implementados. La auditoría local no puede garantizar actividad fuera del sistema, ni revocación inmediata sin conexión, ni resistir a un administrador con control de claves y disco.

El cliente sync_client.py es de referencia y escribe instantáneas sin cifrar; usar solo datos sintéticos. No publicar el servidor HTTP estándar en Internet. La futura migración a un servicio de producción y PostgreSQL es trabajo separado, no una función completada.

## Siguiente paso

Hacer con el usuario el recorrido de entrega, duplicado, revisión, publicación, descarga y auditoría con ejemplos sintéticos. Luego acordar el siguiente alcance de implementación y el alojamiento; no trasladar datos operativos por inferencia.

## Estado de entrega

Archivos y documentación guardados localmente. El ZIP del código excluye .data, claves, contraseñas, base y snapshots de clientes. El aporte propio conserva código y documentación de manera nueva. Drive: pendiente de subir o verificar; no hay un enlace remoto de subida verificada.
