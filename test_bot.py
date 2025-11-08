"""
Script de prueba para verificar que el bot funciona correctamente
"""
import requests
import json

def test_health_endpoint():
    """Prueba el endpoint de salud"""
    print("🔍 Probando endpoint /health...")
    try:
        response = requests.get("http://localhost:5000/health")
        if response.status_code == 200:
            data = response.json()
            print("✅ Endpoint /health funciona correctamente")
            print(f"   Estado: {data.get('status')}")
            print(f"   Google Sheets: {data.get('google_sheets')}")
            return True
        else:
            print(f"❌ Error: Código de estado {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Error: No se puede conectar al servidor")
        print("   Asegúrate de que el bot esté corriendo (python app.py)")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_webhook_verification():
    """Prueba la verificación del webhook"""
    print("\n🔍 Probando verificación del webhook...")
    try:
        url = "http://localhost:5000/webhook"
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": "mi_token_secreto_123",
            "hub.challenge": "test_challenge_123"
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            if response.text == "test_challenge_123":
                print("✅ Verificación del webhook funciona correctamente")
                print(f"   Challenge recibido: {response.text}")
                return True
            else:
                print(f"❌ Error: Challenge no coincide. Recibido: {response.text}")
                return False
        else:
            print(f"❌ Error: Código de estado {response.status_code}")
            print(f"   Respuesta: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_webhook_verification_wrong_token():
    """Prueba con token incorrecto (debe fallar)"""
    print("\n🔍 Probando verificación con token incorrecto...")
    try:
        url = "http://localhost:5000/webhook"
        params = {
            "hub.mode": "subscribe",
            "hub.verify_token": "token_incorrecto",
            "hub.challenge": "test_challenge_123"
        }
        response = requests.get(url, params=params)
        if response.status_code == 403:
            print("✅ Verificación rechaza correctamente tokens incorrectos")
            return True
        else:
            print(f"❌ Error: Debería rechazar el token. Código: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("=" * 50)
    print("🧪 PRUEBAS DEL WHATSAPP BOT")
    print("=" * 50)
    
    tests = [
        ("Endpoint de salud", test_health_endpoint),
        ("Verificación del webhook", test_webhook_verification),
        ("Rechazo de token incorrecto", test_webhook_verification_wrong_token),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error ejecutando prueba '{name}': {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE PRUEBAS")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASÓ" if result else "❌ FALLÓ"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} pruebas pasaron")
    
    if passed == total:
        print("\n🎉 ¡Todas las pruebas pasaron! El bot está funcionando correctamente.")
        print("\n💡 Próximos pasos:")
        print("   1. Asegúrate de que ngrok esté corriendo (ngrok http 5000)")
        print("   2. Configura el webhook en Meta for Developers")
        print("   3. Envía un mensaje de prueba desde WhatsApp")
    else:
        print("\n⚠️  Algunas pruebas fallaron. Revisa los errores arriba.")
        print("\n💡 Asegúrate de que:")
        print("   1. El bot esté corriendo (python app.py)")
        print("   2. El puerto 5000 esté disponible")
        print("   3. No haya errores en la terminal del bot")

if __name__ == "__main__":
    main()

