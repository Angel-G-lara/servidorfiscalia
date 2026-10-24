# Configuración de Flutter para conectar con el Backend

## Pasos para conectar tu app Flutter

### 1. Configurar el backend

1. Copia `.env.example` a `.env`:
```bash
cp .env.example .env
```

2. Edita `.env` con tus credenciales reales de Supabase y Google OAuth

3. Inicia el servidor:
```bash
npm run dev
```

El servidor estará en `http://localhost:3000`

### 2. Configurar Flutter

Agrega las dependencias necesarias en tu `pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.1.0
  google_sign_in: ^6.1.0
  flutter_secure_storage: ^8.0.0
  shared_preferences: ^2.2.0
```

### 3. Crear servicio de API en Flutter

Crea un archivo `lib/services/api_service.dart`:

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiService {
  static const String baseUrl = 'http://10.0.2.2:3000'; // Para emulador Android
  // Para dispositivo físico o web, usa: 'http://localhost:3000' o tu IP real
  
  final _storage = const FlutterSecureStorage();

  Future<http.Response> loginWithGoogle(String idToken, String deviceId) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/auth/google'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'idToken': idToken,
        'device': deviceId,
      }),
    );
    return response;
  }

  Future<http.Response> getDocuments(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/api/documents'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );
    return response;
  }

  Future<http.Response> uploadDocument(
    String token,
    Map<String, dynamic> data,
  ) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/documents'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: jsonEncode(data),
    );
    return response;
  }

  Future<void> saveToken(String token) async {
    await _storage.write(key: 'auth_token', value: token);
  }

  Future<String?> getToken() async {
    return await _storage.read(key: 'auth_token');
  }

  Future<void> deleteToken() async {
    await _storage.delete(key: 'auth_token');
  }
}
```

### 4. Configurar Google Sign-In en Flutter

Crea `lib/services/auth_service.dart`:

```dart
import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'api_service.dart';

class AuthService {
  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: ['email'],
  );
  final _storage = const FlutterSecureStorage();
  final _apiService = ApiService();

  Future<bool> signIn() async {
    try {
      final GoogleSignInAccount? account = await _googleSignIn.signIn();
      if (account == null) return false;

      final GoogleSignInAuthentication auth = await account.authentication;
      
      final response = await _apiService.loginWithGoogle(
        auth.idToken!,
        'flutter_device',
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        await _storage.write(key: 'auth_token', value: data['token']);
        return true;
      }
      return false;
    } catch (e) {
      print('Error signing in: $e');
      return false;
    }
  }

  Future<void> signOut() async {
    await _googleSignIn.signOut();
    await _storage.delete(key: 'auth_token');
  }

  Future<String?> getToken() async {
    return await _storage.read(key: 'auth_token');
  }
}
```

### 5. URLs según entorno

#### Emulador Android
```dart
static const String baseUrl = 'http://10.0.2.2:3000';
```

#### Dispositivo físico Android (mismo WiFi)
```dart
static const String baseUrl = 'http://TU_IP_LOCAL:3000';
// Ejemplo: 'http://192.168.1.100:3000'
```

#### iOS Simulator
```dart
static const String baseUrl = 'http://localhost:3000';
```

#### Web
```dart
static const String baseUrl = 'http://localhost:3000';
```

### 6. Ejemplo de uso en un widget

```dart
import 'package:flutter/material.dart';
import 'services/auth_service.dart';
import 'services/api_service.dart';

class LoginPage extends StatefulWidget {
  @override
  _LoginPageState createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _authService = AuthService();
  final _apiService = ApiService();

  Future<void> _handleSignIn() async {
    final success = await _authService.signIn();
    if (success) {
      Navigator.pushReplacementNamed(context, '/home');
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al iniciar sesión')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: ElevatedButton(
          onPressed: _handleSignIn,
          child: Text('Iniciar sesión con Google'),
        ),
      ),
    );
  }
}
```

### 7. Configuración de Google Sign-In para Android

En `android/app/build.gradle`, agrega:

```gradle
dependencies {
    implementation 'com.google.android.gms:play-services-auth:20.7.0'
}
```

En `android/app/src/main/AndroidManifest.xml`, agrega dentro de `<application>`:

```xml
<meta-data
    android:name="com.google.android.gms.common.api.GoogleApiAvailabilityChecker"
    android:value="com.google.android.gms.common.api.GoogleApiAvailabilityCheckerInternal" />
```

### 8. Permitir HTTP en Android (solo desarrollo)

En `android/app/src/main/AndroidManifest.xml`, agrega dentro de `<application>`:

```xml
<application
    android:usesCleartextTraffic="true"
    ...>
```

### 9. Configuración de Google Sign-In para iOS

En `ios/Runner/Info.plist`, agrega:

```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleTypeRole</key>
        <string>Editor</string>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>YOUR_REVERSED_CLIENT_ID</string>
        </array>
    </dict>
</array>
```

## Notas Importantes

1. **Para producción**, usa HTTPS en lugar de HTTP
2. **En emulador Android**, `10.0.2.2` equivale a `localhost` del host
3. **En dispositivo físico**, ambos deben estar en la misma red WiFi
4. **Asegúrate de que el firewall permita conexiones al puerto 3000**
5. **Las credenciales de Google OAuth deben coincidir con las configuradas en el backend**

## Troubleshooting

### Error: "Connection refused"
- Verifica que el backend esté corriendo
- Verifica la URL base en tu app Flutter
- En emulador Android, usa `10.0.2.2:3000`

### Error: "CORS policy"
- Verifica que el origen esté configurado en `backend/src/index.js`
- En desarrollo, CORS debería permitir todos los orígenes

### Error: "No permitido por CORS"
- Agrega tu IP o dominio a la lista de orígenes permitidos en el backend
