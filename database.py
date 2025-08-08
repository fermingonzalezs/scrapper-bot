"""
Manejo de base de datos SQLite para el bot de eBay
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import Config

logger = logging.getLogger(__name__)

class AuctionDatabase:
    def __init__(self, db_file: str = None):
        self.db_file = db_file or Config().DATABASE_FILE
        self.init_database()
    
    def init_database(self):
        """Inicializar la base de datos y crear tablas si no existen"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                # Tabla de subastas notificadas
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notified_auctions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ebay_item_id TEXT UNIQUE NOT NULL,
                        title TEXT NOT NULL,
                        current_price REAL NOT NULL,
                        original_price REAL,
                        discount_percent REAL,
                        bids INTEGER NOT NULL,
                        time_remaining TEXT NOT NULL,
                        url TEXT NOT NULL,
                        brand TEXT,
                        notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        auction_end_time TIMESTAMP
                    )
                ''')
                
                # Tabla de configuración
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bot_config (
                        id INTEGER PRIMARY KEY,
                        last_check TIMESTAMP,
                        total_notifications INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Insertar configuración inicial si no existe
                cursor.execute('''
                    INSERT OR IGNORE INTO bot_config (id, total_notifications) 
                    VALUES (1, 0)
                ''')
                
                conn.commit()
                logger.info(f"Base de datos inicializada: {self.db_file}")
                
        except sqlite3.Error as e:
            logger.error(f"Error inicializando base de datos: {e}")
            raise
    
    def is_auction_notified(self, ebay_item_id: str) -> bool:
        """Verificar si una subasta ya fue notificada"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT 1 FROM notified_auctions WHERE ebay_item_id = ?',
                    (ebay_item_id,)
                )
                return cursor.fetchone() is not None
        except sqlite3.Error as e:
            logger.error(f"Error verificando subasta notificada: {e}")
            return True  # Asumir que ya fue notificada para evitar spam
    
    def add_notified_auction(self, auction_data: Dict) -> bool:
        """Agregar una subasta a la lista de notificadas"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR IGNORE INTO notified_auctions 
                    (ebay_item_id, title, current_price, original_price, 
                     discount_percent, bids, time_remaining, url, brand, auction_end_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    auction_data['ebay_id'],
                    auction_data['title'],
                    auction_data['current_price'],
                    auction_data.get('original_price'),
                    auction_data.get('discount_percent'),
                    auction_data['bids'],
                    auction_data['time_remaining'],
                    auction_data['url'],
                    auction_data.get('brand'),
                    auction_data.get('auction_end_time')
                ))
                
                # Actualizar contador de notificaciones
                cursor.execute('''
                    UPDATE bot_config 
                    SET total_notifications = total_notifications + 1,
                        last_check = CURRENT_TIMESTAMP
                    WHERE id = 1
                ''')
                
                conn.commit()
                logger.info(f"Subasta agregada a BD: {auction_data['ebay_id']}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error agregando subasta a BD: {e}")
            return False
    
    def cleanup_old_auctions(self, days_old: int = 7):
        """Limpiar subastas antigas de la base de datos"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'DELETE FROM notified_auctions WHERE notified_at < ?',
                    (cutoff_date,)
                )
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Limpieza BD: {deleted_count} registros eliminados")
                    
        except sqlite3.Error as e:
            logger.error(f"Error en limpieza de BD: {e}")
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas del bot"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                
                # Estadísticas generales
                cursor.execute('SELECT total_notifications, last_check FROM bot_config WHERE id = 1')
                config_row = cursor.fetchone()
                
                # Conteo por día
                cursor.execute('''
                    SELECT DATE(notified_at) as date, COUNT(*) as count
                    FROM notified_auctions 
                    WHERE notified_at >= datetime('now', '-7 days')
                    GROUP BY DATE(notified_at)
                    ORDER BY date DESC
                ''')
                daily_stats = cursor.fetchall()
                
                # Marcas más notificadas
                cursor.execute('''
                    SELECT brand, COUNT(*) as count
                    FROM notified_auctions 
                    WHERE brand IS NOT NULL AND notified_at >= datetime('now', '-30 days')
                    GROUP BY brand
                    ORDER BY count DESC
                    LIMIT 5
                ''')
                top_brands = cursor.fetchall()
                
                return {
                    'total_notifications': config_row[0] if config_row else 0,
                    'last_check': config_row[1] if config_row else None,
                    'daily_stats': daily_stats,
                    'top_brands': top_brands
                }
                
        except sqlite3.Error as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    def update_last_check(self):
        """Actualizar timestamp del último chequeo"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE bot_config SET last_check = CURRENT_TIMESTAMP WHERE id = 1'
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Error actualizando último chequeo: {e}")