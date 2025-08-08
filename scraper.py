"""
Scraper de eBay para subastas de laptops
"""
import requests
from bs4 import BeautifulSoup
import logging
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urlencode, urljoin
from config import Config

logger = logging.getLogger(__name__)

class EbayScraper:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.session = requests.Session()
        self.session.headers.update(self.config.HEADERS)
    
    def search_auctions(self, search_query: str = None) -> List[Dict]:
        """Buscar subastas activas en eBay"""
        auctions = []
        
        try:
            # Usar query personalizado o el de config
            query = search_query or self.config.SEARCH_QUERY
            logger.info(f"Query de búsqueda: '{query}'")
            
            # Parámetros de búsqueda simples (todos los productos)
            params = {
                '_nkw': query,
                '_sacat': self.config.CATEGORY_ID,
                '_pgn': '1',  # Primera página
            }
            
            url = f"{self.config.EBAY_SEARCH_URL}?{urlencode(params)}"
            logger.info(f"URL completa: {url}")
            
            logger.info("Haciendo request a eBay...")
            response = self.session.get(url, timeout=self.config.REQUEST_TIMEOUT)
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            response.raise_for_status()
            
            logger.info(f"HTML recibido - longitud: {len(response.content)} bytes")
            logger.debug(f"Primeros 500 chars del HTML: {response.text[:500]}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Debug: guardar HTML para inspección
            try:
                with open('debug_ebay.html', 'w', encoding='utf-8') as f:
                    f.write(str(soup))
                logger.info("Archivo debug_ebay.html guardado exitosamente")
            except Exception as e:
                logger.error(f"Error guardando debug HTML: {e}")
            
            # Encontrar elementos de productos - probar múltiples selectores
            auction_items = soup.find_all('div', class_='s-item__wrapper clearfix')
            logger.info(f"Selector 1 - s-item__wrapper clearfix: {len(auction_items)} elementos")
            
            if len(auction_items) < 5:  # Si hay pocos resultados, probar otros selectores
                auction_items2 = soup.find_all('div', class_='s-item')
                logger.info(f"Selector 2 - s-item: {len(auction_items2)} elementos")
                if len(auction_items2) > len(auction_items):
                    auction_items = auction_items2
            
            if len(auction_items) < 5:
                # Selector más amplio
                auction_items3 = soup.find_all('div', {'class': lambda x: x and 's-item' in str(x)})
                logger.info(f"Selector 3 - cualquier s-item: {len(auction_items3)} elementos")
                if len(auction_items3) > len(auction_items):
                    auction_items = auction_items3
                
            logger.info(f"Total elementos encontrados: {len(auction_items)}")
            
            for item in auction_items:
                auction_data = self._parse_auction_item(item)
                if auction_data:
                    auctions.append(auction_data)
            
            time.sleep(self.config.REQUEST_DELAY)
            
        except requests.RequestException as e:
            logger.error(f"Error en request a eBay: {e}")
            logger.error(f"URL que falló: {url}")
        except Exception as e:
            logger.error(f"Error parseando página de eBay: {e}")
            import traceback
            logger.error(f"Traceback completo: {traceback.format_exc()}")
        
        logger.info(f"Subastas parseadas exitosamente: {len(auctions)}")
        return auctions
    
    def _parse_auction_item(self, item_soup) -> Optional[Dict]:
        """Parsear un elemento individual de subasta"""
        try:
            # Debug: log del item
            logger.debug(f"Parseando item: {str(item_soup)[:100]}...")
            
            # Buscar título con múltiples selectores
            title_elem = (item_soup.find('h3', class_='s-item__title') or 
                         item_soup.find('h3', {'class': lambda x: x and 'title' in x}) or
                         item_soup.find('a', {'class': lambda x: x and 'link' in x}))
            
            if not title_elem:
                logger.debug("No se encontró título")
                return None
            
            title = title_elem.get_text(strip=True)
            
            # Filtrar títulos que no son subastas reales
            invalid_titles = [
                'shop on ebay', 'shop on ebayopens in a new window or tab',
                'save this search', 'get an alert with the newest ads',
                'sponsored', 'advertisement', ''
            ]
            
            if not title or any(invalid in title.lower() for invalid in invalid_titles):
                logger.debug(f"Título inválido filtrado: {title}")
                return None
            
            # Buscar enlace
            link_elem = (title_elem.find('a') or 
                        item_soup.find('a', class_='s-item__link') or
                        item_soup.find('a', href=True))
            
            if not link_elem:
                logger.debug("No se encontró enlace")
                return None
            
            url = link_elem.get('href', '')
            
            # Extraer ID de eBay de la URL
            ebay_id = self._extract_ebay_id(url)
            if not ebay_id:
                logger.debug(f"No se pudo extraer ID de: {url}")
                return None
            
            # Buscar precio con múltiples selectores
            price_elem = (item_soup.find('span', class_='s-item__price') or
                         item_soup.find('span', {'class': lambda x: x and 'price' in x}) or
                         item_soup.find('span', string=lambda x: x and '$' in str(x)))
            
            if not price_elem:
                logger.debug("No se encontró precio")
                return None
            
            current_price = self._parse_price(price_elem.get_text(strip=True))
            if current_price is None:
                logger.debug(f"No se pudo parsear precio: {price_elem.get_text(strip=True)}")
                return None
            
            # Información de pujas
            bid_info = self._parse_bid_info(item_soup)
            
            # Tiempo restante - buscar múltiples selectores
            time_elem = (item_soup.find('span', class_='s-item__time-left') or
                        item_soup.find('span', {'class': lambda x: x and 'time' in x}) or
                        item_soup.find('span', string=lambda x: x and ('d' in str(x) or 'h' in str(x) or 'm' in str(x))))
            
            time_remaining = time_elem.get_text(strip=True) if time_elem else "Unknown"
            
            # Para Buy It Now, el tiempo puede ser "Unknown" o diferente
            # Solo filtrar si claramente no es un producto real
            if time_remaining == "Unknown":
                time_remaining = "Buy It Now"
                # No retornar None, continuar con el parsing
            
            # Shipping info (para calcular precio total si es posible)
            shipping_elem = item_soup.find('span', class_='s-item__shipping')
            shipping_text = shipping_elem.get_text(strip=True) if shipping_elem else ""
            
            auction_data = {
                'ebay_id': ebay_id,
                'title': title,
                'url': url,
                'current_price': current_price,
                'bids': bid_info['bids'],
                'time_remaining': time_remaining,
                'time_remaining_hours': self._parse_time_remaining(time_remaining),
                'shipping_text': shipping_text,
                'brand': self._extract_brand(title),
                'scraped_at': datetime.now()
            }
            
            return auction_data
            
        except Exception as e:
            logger.warning(f"Error parseando item de subasta: {e}")
            return None
    
    def _extract_ebay_id(self, url: str) -> Optional[str]:
        """Extraer ID de eBay de la URL"""
        try:
            # Validar que sea una URL de eBay real
            if not url or 'ebay.com' not in url.lower():
                return None
            
            # Buscar patrón de ID en la URL - múltiples patrones
            patterns = [
                r'/itm/([^/?&]+)',
                r'item=(\d+)',
                r'/(\d{12,})',
                r'hash=item(\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    item_id = match.group(1)
                    # Verificar que el ID sea numérico y de longitud razonable
                    if item_id.isdigit() and len(item_id) >= 8:
                        return item_id
                        
            return None
        except:
            return None
    
    def _parse_price(self, price_text: str) -> Optional[float]:
        """Parsear texto de precio a float"""
        try:
            # Remover símbolos y espacios
            price_clean = re.sub(r'[^\d.,]', '', price_text)
            price_clean = price_clean.replace(',', '')
            
            if not price_clean:
                return None
                
            return float(price_clean)
        except:
            return None
    
    def _parse_bid_info(self, item_soup) -> Dict:
        """Parsear información de pujas"""
        bid_info = {'bids': 0, 'bid_text': ''}
        
        try:
            # Buscar información de pujas con múltiples selectores
            bid_elem = (item_soup.find('span', class_='s-item__bidCount') or
                       item_soup.find('span', {'class': lambda x: x and 'bid' in str(x)}) or
                       item_soup.find('span', string=lambda x: x and 'bid' in str(x).lower()))
            
            if bid_elem:
                bid_text = bid_elem.get_text(strip=True)
                bid_info['bid_text'] = bid_text
                
                # Extraer número de pujas
                match = re.search(r'(\d+)', bid_text)
                if match:
                    bid_info['bids'] = int(match.group(1))
            else:
                # Para Buy It Now, puede no tener pujas
                bid_info['bid_text'] = 'Buy It Now'
                bid_info['bids'] = 0
            
        except:
            pass
        
        return bid_info
    
    def _parse_time_remaining(self, time_text: str) -> float:
        """Convertir tiempo restante a horas"""
        try:
            time_text = time_text.lower()
            hours = 0.0
            
            # Buscar días
            days_match = re.search(r'(\d+)d', time_text)
            if days_match:
                hours += int(days_match.group(1)) * 24
            
            # Buscar horas
            hours_match = re.search(r'(\d+)h', time_text)
            if hours_match:
                hours += int(hours_match.group(1))
            
            # Buscar minutos
            minutes_match = re.search(r'(\d+)m', time_text)
            if minutes_match:
                hours += int(minutes_match.group(1)) / 60
            
            return hours
            
        except:
            return 999.0  # Valor alto para casos donde no se puede parsear
    
    def _extract_brand(self, title: str) -> Optional[str]:
        """Extraer marca del título"""
        title_lower = title.lower()
        
        # Lista simple de marcas para detectar
        brands = [
            'MacBook', 'ThinkPad', 'XPS', 'Surface', 'Alienware',
            'Dell', 'Lenovo', 'HP', 'ASUS', 'Acer', 'MSI',
            'Apple', 'Microsoft', 'Razer', 'Sony', 'Toshiba'
        ]
        
        for brand in brands:
            if brand.lower() in title_lower:
                return brand
        
        return None
    
    def get_auction_details(self, url: str) -> Optional[Dict]:
        """Obtener detalles adicionales de una subasta específica"""
        try:
            response = self.session.get(url, timeout=self.config.REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar precio original (Buy It Now o precio de lista)
            original_price = self._find_original_price(soup)
            
            details = {
                'original_price': original_price,
                'condition': self._find_condition(soup),
                'location': self._find_location(soup)
            }
            
            time.sleep(self.config.REQUEST_DELAY)
            return details
            
        except Exception as e:
            logger.warning(f"Error obteniendo detalles de subasta {url}: {e}")
            return {}
    
    def _find_original_price(self, soup) -> Optional[float]:
        """Buscar precio original en página de detalle"""
        try:
            # Buscar varios selectores posibles para precio original
            selectors = [
                '.u-flL.condText span',
                '.notranslate',
                '.vi-price .notranslate',
                '.u-flL span'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                for elem in elements:
                    text = elem.get_text(strip=True)
                    if '$' in text and 'was' in text.lower():
                        price = self._parse_price(text)
                        if price and price > 0:
                            return price
            
            return None
        except:
            return None
    
    def _find_condition(self, soup) -> str:
        """Buscar condición del item"""
        try:
            condition_elem = soup.find('div', {'id': 'u_vi_condition'})
            if condition_elem:
                return condition_elem.get_text(strip=True)
        except:
            pass
        return "Unknown"
    
    def _find_location(self, soup) -> str:
        """Buscar ubicación del vendedor"""
        try:
            location_elem = soup.find('span', class_='vi-acc-del-range')
            if location_elem:
                return location_elem.get_text(strip=True)
        except:
            pass
        return "Unknown"