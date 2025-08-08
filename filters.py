"""
Filtros para detectar ofertas interesantes de laptops en eBay
"""
import logging
from typing import List, Dict, Optional, Tuple
from config import Config

logger = logging.getLogger(__name__)

class AuctionFilter:
    def __init__(self, config: Config = None):
        self.config = config or Config()
    
    def filter_interesting_auctions(self, auctions: List[Dict]) -> List[Dict]:
        """Filtrar subastas que cumplan los criterios de ofertas interesantes"""
        interesting_auctions = []
        
        logger.info(f"Filtrando {len(auctions)} subastas...")
        
        for auction in auctions:
            try:
                if self._is_auction_interesting(auction):
                    # Agregar información adicional de filtrado
                    auction['filter_reason'] = self._get_filter_reasons(auction)
                    auction['interest_score'] = self._calculate_interest_score(auction)
                    interesting_auctions.append(auction)
                    
            except Exception as e:
                logger.warning(f"Error filtrando subasta {auction.get('ebay_id', 'unknown')}: {e}")
        
        # Ordenar por score de interés (descendente)
        interesting_auctions.sort(key=lambda x: x.get('interest_score', 0), reverse=True)
        
        logger.info(f"Subastas interesantes encontradas: {len(interesting_auctions)}")
        return interesting_auctions
    
    def _is_auction_interesting(self, auction: Dict) -> bool:
        """Determinar si una subasta es interesante según los filtros"""
        
        # Filtro 1: Precio en rango válido
        if not self._price_in_range(auction):
            return False
        
        # Filtro 2: Marca premium
        if not self._is_premium_brand(auction):
            return False
        
        # Filtro 3: Tiempo restante apropiado
        if not self._time_remaining_valid(auction):
            return False
        
        # Filtro 4: Actividad mínima de pujas
        if not self._has_minimum_activity(auction):
            return False
        
        # Filtro 5: Excluir palabras prohibidas
        if self._has_excluded_keywords(auction):
            return False
        
        # Filtro 6: Calcular descuento si es posible
        if not self._has_good_discount(auction):
            return False
        
        return True
    
    def _price_in_range(self, auction: Dict) -> bool:
        """Verificar si el precio está en el rango configurado"""
        current_price = auction.get('current_price', 0)
        return self.config.MIN_PRICE <= current_price <= self.config.MAX_PRICE
    
    def _is_premium_brand(self, auction: Dict) -> bool:
        """Verificar si es una marca premium"""
        title = auction.get('title', '').lower()
        brand = auction.get('brand')
        
        # Si ya detectamos la marca, usar esa información
        if brand:
            return brand in self.config.PREMIUM_BRANDS
        
        # Buscar marca en el título
        for premium_brand in self.config.PREMIUM_BRANDS:
            if premium_brand.lower() in title:
                auction['brand'] = premium_brand  # Actualizar marca detectada
                return True
        
        return False
    
    def _time_remaining_valid(self, auction: Dict) -> bool:
        """Verificar si el tiempo restante es apropiado"""
        time_hours = auction.get('time_remaining_hours', 999)
        return 0 < time_hours <= self.config.MAX_TIME_REMAINING_HOURS
    
    def _has_minimum_activity(self, auction: Dict) -> bool:
        """Verificar si tiene la actividad mínima de pujas"""
        bids = auction.get('bids', 0)
        return bids >= self.config.MIN_BIDS
    
    def _has_excluded_keywords(self, auction: Dict) -> bool:
        """Verificar si contiene palabras a excluir"""
        title = auction.get('title', '').lower()
        
        for keyword in self.config.EXCLUDE_KEYWORDS:
            if keyword.lower() in title:
                logger.debug(f"Subasta excluida por keyword '{keyword}': {auction.get('title', '')}")
                return True
        
        return False
    
    def _has_good_discount(self, auction: Dict) -> bool:
        """Verificar si tiene un buen descuento (si hay precio original)"""
        current_price = auction.get('current_price', 0)
        original_price = auction.get('original_price')
        
        if not original_price or original_price <= current_price:
            # Si no hay precio original o no hay descuento, aplicar lógica alternativa
            return self._alternative_value_check(auction)
        
        discount_percent = ((original_price - current_price) / original_price) * 100
        auction['discount_percent'] = discount_percent
        
        return discount_percent >= self.config.MIN_DISCOUNT_PERCENT
    
    def _alternative_value_check(self, auction: Dict) -> bool:
        """Lógica alternativa cuando no hay precio original"""
        current_price = auction.get('current_price', 0)
        bids = auction.get('bids', 0)
        brand = auction.get('brand', '')
        
        # Para marcas premium muy valoradas, ser menos estricto con precio
        premium_brands = ['MacBook', 'ThinkPad', 'XPS', 'Surface']
        if any(pb in brand for pb in premium_brands):
            if current_price <= 1500 and bids >= 5:
                return True
        
        # Para otras marcas, precio más bajo
        if current_price <= 800 and bids >= self.config.MIN_BIDS:
            return True
        
        return False
    
    def _calculate_interest_score(self, auction: Dict) -> float:
        """Calcular un score de interés para ordenar las subastas"""
        score = 0.0
        
        # Factor 1: Descuento (si existe)
        discount = auction.get('discount_percent', 0)
        if discount > 0:
            score += discount / 10  # Máximo 10 puntos por descuento de 100%
        
        # Factor 2: Actividad de pujas (más pujas = más interés)
        bids = auction.get('bids', 0)
        score += min(bids / 2, 10)  # Máximo 10 puntos por pujas
        
        # Factor 3: Tiempo restante (urgencia)
        time_hours = auction.get('time_remaining_hours', 999)
        if time_hours <= 1:
            score += 5  # Muy urgente
        elif time_hours <= 2:
            score += 3  # Urgente
        elif time_hours <= 3:
            score += 1  # Poco urgente
        
        # Factor 4: Marca premium (bonus)
        brand = auction.get('brand', '')
        premium_bonus = {
            'MacBook': 3,
            'ThinkPad': 2,
            'XPS': 2,
            'Surface': 2,
            'Alienware': 3
        }
        
        for premium, bonus in premium_bonus.items():
            if premium in brand:
                score += bonus
                break
        
        # Factor 5: Precio atractivo
        current_price = auction.get('current_price', 0)
        if current_price <= 500:
            score += 3
        elif current_price <= 800:
            score += 2
        elif current_price <= 1200:
            score += 1
        
        return round(score, 2)
    
    def _get_filter_reasons(self, auction: Dict) -> List[str]:
        """Obtener las razones por las que una subasta es interesante"""
        reasons = []
        
        brand = auction.get('brand')
        if brand:
            reasons.append(f"Marca premium: {brand}")
        
        discount = auction.get('discount_percent')
        if discount and discount > 0:
            reasons.append(f"Descuento: {discount:.1f}%")
        
        bids = auction.get('bids', 0)
        if bids >= self.config.MIN_BIDS:
            reasons.append(f"Actividad alta: {bids} pujas")
        
        time_hours = auction.get('time_remaining_hours', 999)
        if time_hours <= 1:
            reasons.append("¡Termina pronto!")
        
        current_price = auction.get('current_price', 0)
        if current_price <= 500:
            reasons.append("Precio muy atractivo")
        
        return reasons
    
    def get_filter_stats(self, all_auctions: List[Dict], filtered_auctions: List[Dict]) -> Dict:
        """Obtener estadísticas de filtrado"""
        total = len(all_auctions)
        filtered = len(filtered_auctions)
        
        stats = {
            'total_auctions': total,
            'filtered_auctions': filtered,
            'filter_rate': round((filtered / total * 100), 2) if total > 0 else 0,
            'avg_interest_score': 0,
            'top_brands': {},
            'price_distribution': {'under_500': 0, '500_1000': 0, '1000_1500': 0, 'over_1500': 0}
        }
        
        if filtered_auctions:
            # Score promedio
            scores = [a.get('interest_score', 0) for a in filtered_auctions]
            stats['avg_interest_score'] = round(sum(scores) / len(scores), 2)
            
            # Distribución de marcas
            for auction in filtered_auctions:
                brand = auction.get('brand', 'Unknown')
                stats['top_brands'][brand] = stats['top_brands'].get(brand, 0) + 1
            
            # Distribución de precios
            for auction in filtered_auctions:
                price = auction.get('current_price', 0)
                if price < 500:
                    stats['price_distribution']['under_500'] += 1
                elif price < 1000:
                    stats['price_distribution']['500_1000'] += 1
                elif price < 1500:
                    stats['price_distribution']['1000_1500'] += 1
                else:
                    stats['price_distribution']['over_1500'] += 1
        
        return stats