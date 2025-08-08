"""
Bot de Telegram simple para buscar subastas en eBay
"""
import logging
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from scraper import EbayScraper
from config import Config

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ebay_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Solo debug para nuestro scraper
logging.getLogger('scraper').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

# Estados de conversación
WAITING_SEARCH = 1

class EbayBot:
    def __init__(self):
        self.config = Config.load()
        self.scraper = EbayScraper(self.config)
        
        if not self.config.validate():
            raise ValueError("Configuración inválida")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        welcome_message = (
            "🤖 *¡Hola! Soy tu bot de subastas de eBay*\n\n"
            "Comandos disponibles:\n"
            "• /buscar - Buscar subastas por término\n"
            "• /help - Ver esta ayuda\n\n"
            "¡Empezá con /buscar para encontrar ofertas!"
        )
        
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        help_message = (
            "🔍 *Cómo usar el bot:*\n\n"
            "1. Usa /buscar\n"
            "2. Escribe lo que querés buscar (ej: 'macbook pro')\n"
            "3. Te muestro las 10 subastas que terminan más pronto\n\n"
            "*Ejemplos de búsqueda:*\n"
            "• macbook\n"
            "• thinkpad t480\n"
            "• gaming laptop\n"
            "• dell xps\n\n"
            "💡 *Tip:* Sé específico para mejores resultados"
        )
        
        await update.message.reply_text(
            help_message,
            parse_mode='Markdown'
        )

    async def buscar_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /buscar - inicia búsqueda"""
        await update.message.reply_text(
            "🔍 *¿Qué querés buscar en eBay?*\n\n"
            "Escribí el término de búsqueda (ej: 'macbook pro', 'thinkpad', etc.)\n"
            "o /cancel para cancelar",
            parse_mode='Markdown'
        )
        return WAITING_SEARCH

    async def handle_search_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar el término de búsqueda del usuario"""
        query = update.message.text.strip()
        
        if not query:
            await update.message.reply_text("❌ Por favor escribe algo para buscar")
            return WAITING_SEARCH
        
        # Mostrar mensaje de búsqueda
        search_msg = await update.message.reply_text(
            f"🔍 Buscando '{query}' en eBay...\n"
            "⏳ Esto puede tomar unos segundos..."
        )
        
        try:
            # Buscar subastas
            auctions = self.scraper.search_auctions(query)
            
            if not auctions:
                await search_msg.edit_text(
                    f"😔 No encontré subastas activas para '{query}'\n\n"
                    "💡 *Intentá con:*\n"
                    "• Términos más generales\n"
                    "• Menos palabras\n"
                    "• Diferentes marcas\n\n"
                    "Usá /buscar para intentar de nuevo"
                )
                return ConversationHandler.END
            
            # Ordenar por tiempo restante (las que terminan primero)
            auctions_sorted = sorted(auctions, key=lambda x: x.get('time_remaining_hours', 999))
            top_10 = auctions_sorted[:10]
            
            # Formatear resultados
            await search_msg.edit_text(f"✅ Encontré {len(auctions)} subastas para '{query}'")
            
            # Enviar cada subasta
            for i, auction in enumerate(top_10, 1):
                message = self.format_auction_message(auction, i)
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                
            # Mensaje final
            await update.message.reply_text(
                f"🎯 *Mostrando las {len(top_10)} subastas que terminan más pronto*\n\n"
                "Usá /buscar para hacer otra búsqueda"
            )
                
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            await search_msg.edit_text(
                f"❌ Error buscando '{query}'\n\n"
                "Puede ser que eBay esté bloqueando las consultas.\n"
                "Intentá de nuevo en unos minutos.\n\n"
                "Usá /buscar para reintentar"
            )
        
        return ConversationHandler.END

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancelar operación actual"""
        await update.message.reply_text(
            "❌ Búsqueda cancelada\n\n"
            "Usá /buscar cuando quieras buscar algo"
        )
        return ConversationHandler.END

    def format_auction_message(self, auction: dict, position: int) -> str:
        """Formatear mensaje de subasta"""
        title = auction.get('title', 'Sin título')
        if len(title) > 60:
            title = title[:60] + "..."
        
        current_price = auction.get('current_price', 0)
        bids = auction.get('bids', 0)
        time_remaining = auction.get('time_remaining', 'N/A')
        url = auction.get('url', '')
        
        message = (
            f"*{position}. {title}*\n\n"
            f"💰 *Precio actual:* ${current_price:,.2f}\n"
            f"🔨 *Pujas:* {bids}\n"
            f"⏰ *Termina en:* {time_remaining}\n"
        )
        
        # Agregar marca si está disponible
        brand = auction.get('brand')
        if brand:
            message += f"🏢 *Marca:* {brand}\n"
        
        # Agregar enlace
        if url:
            message += f"\n🔗 [Ver en eBay]({url})"
        
        return message

    def run(self):
        """Ejecutar el bot"""
        # Crear aplicación
        application = Application.builder().token(self.config.TELEGRAM_BOT_TOKEN).build()
        
        # Configurar conversation handler para búsqueda
        search_handler = ConversationHandler(
            entry_points=[CommandHandler('buscar', self.buscar_command)],
            states={
                WAITING_SEARCH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_search_query),
                    CommandHandler('cancel', self.cancel_command)
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel_command)]
        )
        
        # Agregar handlers
        application.add_handler(CommandHandler('start', self.start_command))
        application.add_handler(CommandHandler('help', self.help_command))
        application.add_handler(search_handler)
        
        # Iniciar bot
        logger.info("🚀 Bot iniciado. Presiona Ctrl+C para parar.")
        application.run_polling()

def main():
    """Función principal"""
    try:
        bot = EbayBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot detenido por usuario")
    except Exception as e:
        logger.error(f"Error ejecutando bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()