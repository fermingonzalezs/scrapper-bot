# 🤖 Bot de Monitoreo de Subastas de Laptops en eBay

Bot de Telegram que monitorea automáticamente subastas de laptops en eBay y notifica sobre ofertas interesantes que estén por terminar.

## 🚀 Características

- **Monitoreo automático**: Chequea eBay cada 15 minutos
- **Filtros inteligentes**: Detecta ofertas con buen descuento y actividad
- **Marcas premium**: Enfoque en MacBook, ThinkPad, XPS, Surface, Alienware
- **Notificaciones Telegram**: Mensajes con toda la información relevante
- **Base de datos SQLite**: Evita notificaciones duplicadas
- **Sistema de puntuación**: Ordena ofertas por interés
- **Logs detallados**: Seguimiento completo de la actividad

## 📋 Requisitos

- Python 3.8 o superior
- Token de bot de Telegram
- ID de chat de Telegram
- Conexión a internet estable

## 🛠️ Instalación

### 1. Clonar el repositorio
```bash
git clone <url-del-repositorio>
cd ebay-scrapper
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar el bot de Telegram

#### Crear un bot de Telegram:
1. Habla con [@BotFather](https://t.me/botfather) en Telegram
2. Usa el comando `/newbot`
3. Elige un nombre para tu bot
4. Guarda el token que te proporciona

#### Obtener tu Chat ID:
1. Habla con [@userinfobot](https://t.me/userinfobot) 
2. Envía cualquier mensaje
3. Guarda el ID que te muestra

### 4. Configurar variables de entorno

Crea un archivo `.env` en el directorio del proyecto:

```bash
# Crear archivo .env
touch .env
```

Agrega las siguientes variables:

```env
# Token del bot de Telegram
TELEGRAM_BOT_TOKEN=tu_token_aqui

# ID del chat donde enviar notificaciones
TELEGRAM_CHAT_ID=tu_chat_id_aqui
```

### 5. Configuración alternativa (sin .env)

Si prefieres exportar variables de entorno directamente:

```bash
export TELEGRAM_BOT_TOKEN="tu_token_aqui"
export TELEGRAM_CHAT_ID="tu_chat_id_aqui"
```

## ▶️ Uso

### Ejecutar el bot:
```bash
python main.py
```

### Ejecutar en segundo plano (Linux/macOS):
```bash
nohup python main.py &
```

### Usando screen (recomendado para servidores):
```bash
screen -S ebay-bot
python main.py
# Presiona Ctrl+A, luego D para desconectar
# Para reconectar: screen -r ebay-bot
```

## ⚙️ Configuración

El bot se puede configurar editando `config.py`:

### Filtros principales:
```python
MIN_PRICE = 200.0              # Precio mínimo en USD
MAX_PRICE = 2000.0             # Precio máximo en USD
MIN_DISCOUNT_PERCENT = 30.0    # Descuento mínimo requerido
MAX_TIME_REMAINING_HOURS = 3.0 # Máximo tiempo restante
MIN_BIDS = 3                   # Mínimo número de pujas
```

### Marcas a monitorear:
```python
PREMIUM_BRANDS = [
    "MacBook", "ThinkPad", "XPS", "Surface", "Alienware",
    "Dell XPS", "Lenovo ThinkPad", "Microsoft Surface"
]
```

### Palabras a excluir:
```python
EXCLUDE_KEYWORDS = [
    "parts", "repair", "broken", "damaged", "cracked"
]
```

### Intervalo de chequeo:
```python
CHECK_INTERVAL_MINUTES = 15    # Chequear cada 15 minutos
```

## 📊 Funcionamiento del Sistema de Filtros

### 1. Filtros básicos:
- ✅ Precio en rango configurado ($200-2000)
- ✅ Marca premium detectada
- ✅ Tiempo restante ≤ 3 horas
- ✅ Mínimo 3 pujas (indica interés)
- ❌ Excluye palabras como "parts", "repair", "broken"

### 2. Sistema de puntuación:
- **Descuento**: Hasta 10 puntos por descuento alto
- **Actividad**: Puntos por número de pujas
- **Urgencia**: Bonus por tiempo restante corto
- **Marca**: Bonus adicional para marcas premium
- **Precio**: Bonus para precios muy atractivos

### 3. Detección de valor:
- Si hay precio original → Calcula descuento real
- Si no hay precio original → Usa lógica alternativa basada en marca y precio actual

## 📱 Ejemplo de Notificación

```
💻 MacBook Pro 13" 2020 M1 Chip 8GB RAM 256GB SSD

💰 Precio actual: $899.00
🏷️ Precio original: $1,299.00
💥 Descuento: 30.8%
🔨 Pujas: 7
⏰ Tiempo restante: 2h 15m
🏢 Marca: MacBook
⭐ Score de interés: 8.5/10

¿Por qué es interesante?
• Marca premium: MacBook
• Descuento: 30.8%
• Actividad alta: 7 pujas
• ¡Termina pronto!

🔗 Ver en eBay
```

## 📁 Estructura del Proyecto

```
ebay-scrapper/
├── main.py           # Bot principal de Telegram
├── config.py         # Configuración del sistema
├── scraper.py        # Lógica de scraping de eBay
├── database.py       # Manejo de base de datos SQLite
├── filters.py        # Sistema de filtros y puntuación
├── requirements.txt  # Dependencias de Python
├── README.md         # Este archivo
├── auctions.db       # Base de datos (se crea automáticamente)
└── ebay_bot.log      # Archivo de logs (se crea automáticamente)
```

## 🗃️ Base de Datos

El bot usa SQLite para almacenar:
- **Subastas notificadas**: Evita duplicados
- **Estadísticas**: Contadores y timestamps
- **Limpieza automática**: Elimina registros antiguos (7 días)

### Ver la base de datos:
```bash
sqlite3 auctions.db
.tables
.schema notified_auctions
SELECT * FROM notified_auctions LIMIT 5;
.quit
```

## 📊 Logs y Monitoreo

### Ver logs en tiempo real:
```bash
tail -f ebay_bot.log
```

### Logs incluyen:
- ✅ Conexiones exitosas a eBay y Telegram
- 📊 Estadísticas de cada chequeo
- ⚠️ Errores y warnings
- 📧 Notificaciones enviadas

## 🔧 Solución de Problemas

### Error: "TELEGRAM_BOT_TOKEN no configurado"
- Verifica que el archivo `.env` existe y tiene el token correcto
- O exporta la variable de entorno manualmente

### Error: "Error conectando a Telegram"
- Verifica que el token del bot es válido
- Verifica que el bot no fue bloqueado por Telegram
- Revisa tu conexión a internet

### Error: "No se encontraron subastas"
- eBay puede estar bloqueando requests
- Intenta cambiar el User-Agent en `config.py`
- Verifica que eBay esté disponible

### El bot no envía notificaciones:
- Verifica que el CHAT_ID es correcto
- Asegúrate de que iniciaste una conversación con el bot
- Revisa que los filtros no sean muy restrictivos

### Performance lento:
- Reduce la frecuencia de chequeo en `config.py`
- Aumenta `REQUEST_DELAY` para ser más conservador

## 🛡️ Consideraciones de Seguridad

### Tokens y credenciales:
- ✅ Usa variables de entorno para tokens
- ❌ No hardcodees credenciales en el código
- ✅ Añade `.env` a `.gitignore`

### Rate limiting:
- ✅ El bot incluye delays entre requests
- ✅ Maneja errores de Telegram por rate limiting
- ⚠️ No reduzcas demasiado los delays

### Uso responsable:
- ✅ Respeta robots.txt de eBay
- ✅ No hagas requests excesivos
- ✅ Usa el bot solo para uso personal

## 🚀 Mejoras Futuras

### Posibles extensiones:
- [ ] Soporte para múltiples categorías
- [ ] Filtros más avanzados con ML
- [ ] Interfaz web para configuración
- [ ] Soporte para múltiples usuarios
- [ ] Integración con otras plataformas
- [ ] Alertas por precio objetivo
- [ ] Historial de precios

### Optimizaciones:
- [ ] Cache de requests HTTP
- [ ] Base de datos más robusta (PostgreSQL)
- [ ] Containerización con Docker
- [ ] Monitoreo con métricas
- [ ] Tests automatizados

## 📄 Licencia

Este proyecto es solo para uso educativo y personal. Respeta los términos de servicio de eBay y Telegram.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## ⚠️ Disclaimer

Este bot es para uso educativo. El autor no se hace responsable por:
- Uso indebido del bot
- Violación de términos de servicio de terceros
- Decisiones de compra basadas en las notificaciones
- Pérdidas o problemas derivados del uso del bot

Usa bajo tu propia responsabilidad y siempre verifica la información antes de realizar compras.